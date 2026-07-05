"""
Epic 3.3 — Return Chart Integration tests.

Verifies:
  1. Core overlay: natal planets placed in return chart houses (1-12)
  2. Core overlay: cross-aspects found between return and natal planets
  3. Cross-aspects are within combined orb
  4. Applying flag is computed from return planet speed
  5. Solar return API: include_natal_overlay=True populates natal_overlay
  6. Lunar return API: include_natal_overlay=True populates overlay on each entry
  7. Default (include_natal_overlay=False) → natal_overlay is null
  8. Placements: 7 natal planets each placed in a valid house (1-12)
  9. No self-to-self aspects (return Sun vs natal Sun, etc.)
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.return_overlay import (
    calc_return_natal_overlay, _planet_in_house, _is_applying_cross,
)
from models.chart import PlanetPosition

# ── ephemeris path ─────────────────────────────────────────────────────────────

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

# ── Shared test data ──────────────────────────────────────────────────────────

BIRTH = {"year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 30, "ut_offset": 0.0}
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

SR_REQUEST = {**BIRTH, "return_year": 2025, "return_lat": 41.9, "return_lon": 12.5, "hsys": "B"}
LR_REQUEST = {**BIRTH, "return_year": 2025, "return_lat": 41.9, "return_lon": 12.5, "hsys": "B"}

client = TestClient(app)

_TRAD = [
    (swe.SUN, "Sun"), (swe.MOON, "Moon"), (swe.MERCURY, "Mercury"),
    (swe.VENUS, "Venus"), (swe.MARS, "Mars"), (swe.JUPITER, "Jupiter"),
    (swe.SATURN, "Saturn"),
]
_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


def _make_planet(pid, name, lon, speed=1.0) -> PlanetPosition:
    sign = _SIGNS[int(lon / 30) % 12]
    return PlanetPosition(
        id=pid, name=name, lon=lon, lat=0.0, speed=speed,
        retrograde=speed < 0, sign=sign, sign_lon=round(lon % 30, 4),
    )


def _natal_planets() -> list[PlanetPosition]:
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    result = []
    for pid, name in _TRAD:
        r, _ = swe.calc_ut(jd, pid, FLAGS)
        sign = _SIGNS[int(r[0] / 30) % 12]
        result.append(PlanetPosition(
            id=pid, name=name, lon=round(r[0], 4), lat=round(r[1], 4),
            speed=round(r[3], 6), retrograde=r[3] < 0,
            sign=sign, sign_lon=round(r[0] % 30, 4),
        ))
    return result


# ── Unit tests: _planet_in_house ──────────────────────────────────────────────

def test_house_placement_basic():
    """Planet at 15° Aries with Aries rising is in house 1."""
    # Whole-sign-like: 12 equal cusps starting at 0°
    cusps = [float(i * 30) for i in range(12)]
    assert _planet_in_house(15.0, cusps) == 1
    assert _planet_in_house(45.0, cusps) == 2
    assert _planet_in_house(350.0, cusps) == 12


def test_house_placement_wrap_around():
    """Planet just before 360° wraps into house 12."""
    cusps = [float(i * 30) for i in range(12)]
    assert _planet_in_house(359.9, cusps) == 12


def test_house_placement_at_cusp():
    """Planet exactly on a cusp is assigned to the next house."""
    cusps = [float(i * 30) for i in range(12)]
    assert _planet_in_house(30.0, cusps) == 2


def test_house_placement_unequal_cusps():
    """Works with unequal cusps (Alcabitius-style)."""
    # Simulate irregular cusps
    cusps = [5.0, 37.0, 65.0, 95.0, 125.0, 155.0,
             185.0, 217.0, 245.0, 275.0, 305.0, 335.0]
    assert _planet_in_house(10.0, cusps) == 1
    assert _planet_in_house(40.0, cusps) == 2
    assert _planet_in_house(340.0, cusps) == 12


# ── Unit tests: _is_applying_cross ────────────────────────────────────────────

def test_applying_cross_conjunction():
    """Return planet moving toward natal planet is applying."""
    # Return planet at 89°, natal at 90°, speed +1 → moves toward 90°
    applying = _is_applying_cross(ret_lon=89.0, ret_speed=1.0, nat_lon=90.0, aspect_angle=0.0)
    assert applying is True


def test_separating_cross_conjunction():
    """Return planet moving away from natal planet is separating."""
    # Return planet at 91°, natal at 90°, speed +1 → moves away from 90°
    applying = _is_applying_cross(ret_lon=91.0, ret_speed=1.0, nat_lon=90.0, aspect_angle=0.0)
    assert applying is False


def test_applying_cross_opposition():
    """Return planet applying to opposition with natal planet."""
    # Return at 358°, natal at 179°: arc = 179°, orb = 1°.
    # Speed +1°/day → next day at 359°, arc = 180°, orb = 0° → applying.
    applying = _is_applying_cross(ret_lon=358.0, ret_speed=1.0, nat_lon=179.0, aspect_angle=180.0)
    assert applying is True


# ── Core overlay tests ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def overlay_result():
    """Build overlay using real birth and return chart data."""
    natal_ps = _natal_planets()

    # Build a minimal return chart using the 2025 solar return moment
    jd_birth = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    r_natal, _ = swe.calc_ut(jd_birth, swe.SUN, FLAGS)
    from core.solar_return import find_solar_return_jd
    jd_ret = find_solar_return_jd(r_natal[0], 2025, 6, 15, 10.5)

    ret_planets = []
    for pid, name in _TRAD:
        r, _ = swe.calc_ut(jd_ret, pid, FLAGS)
        sign = _SIGNS[int(r[0] / 30) % 12]
        ret_planets.append(PlanetPosition(
            id=pid, name=name, lon=round(r[0], 4), lat=round(r[1], 4),
            speed=round(r[3], 6), retrograde=r[3] < 0,
            sign=sign, sign_lon=round(r[0] % 30, 4),
        ))

    cusps_raw, _ = swe.houses(jd_ret, 41.9, 12.5, b"B")
    cusps = [round(c, 4) for c in cusps_raw]

    return calc_return_natal_overlay(ret_planets, natal_ps, cusps)


def test_overlay_placements_count(overlay_result):
    """All 7 natal traditional planets get a house placement."""
    assert len(overlay_result.placements) == 7


def test_overlay_placements_valid_house(overlay_result):
    """Every natal planet placement is in house 1-12."""
    for p in overlay_result.placements:
        assert 1 <= p.return_house <= 12, (
            f"{p.planet_name}: invalid house {p.return_house}"
        )


def test_overlay_placements_lon_preserved(overlay_result):
    """Placement preserves the natal planet's longitude."""
    for p in overlay_result.placements:
        assert 0.0 <= p.natal_lon < 360.0, (
            f"{p.planet_name}: lon out of range {p.natal_lon}"
        )


def test_overlay_cross_aspects_nonempty(overlay_result):
    """At least some cross-aspects are found between real charts."""
    assert len(overlay_result.cross_aspects) > 0, "Expected cross-aspects between return and natal"


def test_overlay_cross_aspects_orb_in_range(overlay_result):
    """All cross-aspects have orb < max_orb."""
    for a in overlay_result.cross_aspects:
        assert a.orb <= a.max_orb + 1e-6, (
            f"{a.return_planet_name}→{a.natal_planet_name} "
            f"{a.aspect_name}: orb {a.orb} > max_orb {a.max_orb}"
        )


def test_overlay_no_self_aspects(overlay_result):
    """No aspect between a planet and its own natal position."""
    for a in overlay_result.cross_aspects:
        assert a.return_planet_id != a.natal_planet_id, (
            f"Self-aspect found: return {a.return_planet_name} vs natal {a.natal_planet_name}"
        )


def test_overlay_sorted_by_orb(overlay_result):
    """Cross-aspects are sorted tightest first."""
    orbs = [a.orb for a in overlay_result.cross_aspects]
    assert orbs == sorted(orbs)


def test_overlay_aspect_types_valid(overlay_result):
    """Aspect types are in the range 0-4 (Ptolemaic)."""
    for a in overlay_result.cross_aspects:
        assert 0 <= a.aspect_type <= 4, f"Invalid aspect type {a.aspect_type}"


# ── API: Solar Return with overlay ───────────────────────────────────────────

@pytest.fixture(scope="module")
def sr_overlay():
    resp = client.post("/chart/solar-return", json={**SR_REQUEST, "include_natal_overlay": True})
    assert resp.status_code == 200, f"API error: {resp.text}"
    return resp.json()


def test_sr_overlay_present(sr_overlay):
    assert sr_overlay["natal_overlay"] is not None


def test_sr_overlay_has_natal_planets(sr_overlay):
    nat_ps = sr_overlay["natal_overlay"]["natal_planets"]
    assert len(nat_ps) == 7
    names = {p["name"] for p in nat_ps}
    assert names == {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}


def test_sr_overlay_placements_seven(sr_overlay):
    placements = sr_overlay["natal_overlay"]["placements"]
    assert len(placements) == 7


def test_sr_overlay_placements_houses_valid(sr_overlay):
    for p in sr_overlay["natal_overlay"]["placements"]:
        assert 1 <= p["return_house"] <= 12, f"{p['planet_name']}: house {p['return_house']}"


def test_sr_overlay_cross_aspects_present(sr_overlay):
    assert len(sr_overlay["natal_overlay"]["cross_aspects"]) > 0


def test_sr_overlay_cross_aspects_no_self(sr_overlay):
    for a in sr_overlay["natal_overlay"]["cross_aspects"]:
        assert a["return_planet_id"] != a["natal_planet_id"]


def test_sr_overlay_cross_aspects_fields(sr_overlay):
    for a in sr_overlay["natal_overlay"]["cross_aspects"]:
        assert "return_planet_name" in a
        assert "natal_planet_name" in a
        assert "aspect_name" in a
        assert "orb" in a
        assert "applying" in a
        assert "exact" in a


def test_sr_no_overlay_by_default():
    """Without include_natal_overlay, natal_overlay is null."""
    resp = client.post("/chart/solar-return", json=SR_REQUEST).json()
    assert resp.get("natal_overlay") is None


# ── API: Lunar Return with overlay ────────────────────────────────────────────

@pytest.fixture(scope="module")
def lr_overlay():
    resp = client.post("/chart/lunar-return", json={**LR_REQUEST, "include_natal_overlay": True})
    assert resp.status_code == 200, f"API error: {resp.text}"
    return resp.json()


def test_lr_overlay_each_entry_has_overlay(lr_overlay):
    for i, entry in enumerate(lr_overlay["returns"]):
        assert entry["natal_overlay"] is not None, f"Entry {i}: missing natal_overlay"


def test_lr_overlay_each_entry_placements(lr_overlay):
    for i, entry in enumerate(lr_overlay["returns"]):
        placements = entry["natal_overlay"]["placements"]
        assert len(placements) == 7, f"Entry {i}: expected 7 placements"
        for p in placements:
            assert 1 <= p["return_house"] <= 12, (
                f"Entry {i}, {p['planet_name']}: invalid house {p['return_house']}"
            )


def test_lr_overlay_each_entry_cross_aspects(lr_overlay):
    for i, entry in enumerate(lr_overlay["returns"]):
        ca = entry["natal_overlay"]["cross_aspects"]
        assert len(ca) > 0, f"Entry {i}: no cross-aspects found"


def test_lr_overlay_no_self_aspects(lr_overlay):
    for i, entry in enumerate(lr_overlay["returns"]):
        for a in entry["natal_overlay"]["cross_aspects"]:
            assert a["return_planet_id"] != a["natal_planet_id"], (
                f"Entry {i}: self-aspect {a['return_planet_name']}"
            )


def test_lr_no_overlay_by_default():
    """Without include_natal_overlay, natal_overlay is null on each entry."""
    resp = client.post("/chart/lunar-return", json=LR_REQUEST).json()
    for entry in resp["returns"]:
        assert entry.get("natal_overlay") is None
