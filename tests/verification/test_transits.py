"""
Epic 5.1 — Transits Overlay tests.

Verifies:
  1. Core: _find_exact_jd converges on target longitude
  2. Core: exact_jd within max_days or returns None
  3. Core: _is_applying flag correct for approaching vs departing planet
  4. Core: all aspects within combined orb
  5. Core: cusp conjunctions within cusp_orb
  6. Core: aspects sorted by orb (tightest first)
  7. API: /chart/transits returns correct structure
  8. API: transit_planets have 7+ entries (traditional set)
  9. API: natal_planets always 7 traditional
 10. API: all aspect types 0-4 valid
 11. API: exact_jd is a valid JD or null
 12. API: cusp_number always 1-12
 13. API: cusp_conjunctions absent when include_cusp_conjunctions=False
 14. API: orb param limits aspects found
 15. API: outer planets in transit when include_outer=True
 16. API: applying flag is boolean for all aspects
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.transits import (
    calc_transits_full, _find_exact_jd, _is_applying, _arc,
)
from models.chart import PlanetPosition

# ── ephemeris path ─────────────────────────────────────────────────────────────

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

# ── Shared test data ──────────────────────────────────────────────────────────

BIRTH = {"year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 30, "ut_offset": 0.0}

TR_REQUEST = {
    **BIRTH,
    "lat": 41.9, "lon": 12.5,
    "transit_year": 2025, "transit_month": 6, "transit_day": 15,
    "hsys": "B",
    "orb": 2.0,
    "cusp_orb": 1.0,
}

client = TestClient(app)

BIRTH_JD   = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
TRANSIT_JD = swe.julday(2025, 6, 15, 12.0, swe.GREG_CAL)

_TRAD = [
    (swe.SUN, "Sun"), (swe.MOON, "Moon"), (swe.MERCURY, "Mercury"),
    (swe.VENUS, "Venus"), (swe.MARS, "Mars"), (swe.JUPITER, "Jupiter"),
    (swe.SATURN, "Saturn"),
]
_SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces",
]


def _make_planet(pid, name, lon, speed=1.0) -> PlanetPosition:
    sign = _SIGNS[int(lon / 30) % 12]
    return PlanetPosition(
        id=pid, name=name, lon=lon, lat=0.0, speed=speed,
        retrograde=speed < 0, sign=sign, sign_lon=round(lon % 30, 4),
    )


def _real_planets(jd) -> list[PlanetPosition]:
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


# ── Unit tests: _find_exact_jd ────────────────────────────────────────────────

def test_find_exact_jd_sun():
    """At returned JD, Sun should be at target_lon to < 0.001°."""
    r_sun, _ = swe.calc_ut(TRANSIT_JD, swe.SUN, FLAGS)
    target = (r_sun[0] + 5.0) % 360.0   # 5° ahead of current
    jd = _find_exact_jd(TRANSIT_JD, swe.SUN, target, max_days=30.0)
    assert jd is not None
    r_check, _ = swe.calc_ut(jd, swe.SUN, FLAGS)
    diff = abs((r_check[0] - target + 180) % 360 - 180)
    assert diff < 0.001, f"Sun at exact_jd differs by {diff:.6f}°"


def test_find_exact_jd_moon():
    """Moon exact date: Moon at target_lon to < 0.001°."""
    r_moon, _ = swe.calc_ut(TRANSIT_JD, swe.MOON, FLAGS)
    target = (r_moon[0] + 10.0) % 360.0
    jd = _find_exact_jd(TRANSIT_JD, swe.MOON, target, max_days=5.0)
    assert jd is not None
    r_check, _ = swe.calc_ut(jd, swe.MOON, FLAGS)
    diff = abs((r_check[0] - target + 180) % 360 - 180)
    assert diff < 0.001, f"Moon at exact_jd differs by {diff:.6f}°"


def test_find_exact_jd_returns_none_beyond_window():
    """Target 200° ahead of Jupiter: beyond 90 days, returns None."""
    r_jup, _ = swe.calc_ut(TRANSIT_JD, swe.JUPITER, FLAGS)
    target = (r_jup[0] + 200.0) % 360.0
    jd = _find_exact_jd(TRANSIT_JD, swe.JUPITER, target, max_days=90.0)
    # Jupiter moves ~0.08°/day → 200° takes ~2500 days >> 90
    assert jd is None


def test_find_exact_jd_within_window():
    """Target 10° ahead of Moon: within 5 days, returns a JD."""
    r_moon, _ = swe.calc_ut(TRANSIT_JD, swe.MOON, FLAGS)
    target = (r_moon[0] + 10.0) % 360.0
    jd = _find_exact_jd(TRANSIT_JD, swe.MOON, target, max_days=5.0)
    assert jd is not None
    assert abs(jd - TRANSIT_JD) <= 5.0


# ── Unit tests: _is_applying ──────────────────────────────────────────────────

def test_is_applying_true():
    """Planet at 88°, natal at 90°, speed +1 → applying to conjunction."""
    assert _is_applying(88.0, 1.0, 90.0, 0.0) is True


def test_is_applying_false():
    """Planet at 92°, natal at 90°, speed +1 → separating from conjunction."""
    assert _is_applying(92.0, 1.0, 90.0, 0.0) is False


def test_is_applying_retrograde():
    """Retrograde planet approaching from above (higher lon) → applying."""
    # At 92°, speed -1, conjunction with 90° → moves toward 91°, 90° → applying
    assert _is_applying(92.0, -1.0, 90.0, 0.0) is True


# ── Core overlay tests ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def transit_result():
    transit_ps = _real_planets(TRANSIT_JD)
    natal_ps   = _real_planets(BIRTH_JD)
    _, ascmc = swe.houses(BIRTH_JD, 41.9, 12.5, b"B")
    cusps_raw, _ = swe.houses(BIRTH_JD, 41.9, 12.5, b"B")
    return calc_transits_full(
        transit_jd=TRANSIT_JD,
        transit_planets=transit_ps,
        natal_planets=natal_ps,
        natal_cusps=list(cusps_raw),
        max_orb=2.0,
        cusp_orb=1.0,
        exact_max_days=90.0,
    )


def test_aspects_sorted_by_orb(transit_result):
    orbs = [a.orb for a in transit_result.aspects]
    assert orbs == sorted(orbs)


def test_aspects_within_orb(transit_result):
    for a in transit_result.aspects:
        assert a.orb <= a.max_orb + 1e-6, (
            f"{a.transit_planet_name}→{a.natal_planet_name}: orb {a.orb} > max {a.max_orb}"
        )


def test_aspect_types_valid(transit_result):
    for a in transit_result.aspects:
        assert 0 <= a.aspect_type <= 4


def test_cusp_conjunctions_within_orb(transit_result):
    for c in transit_result.cusp_conjunctions:
        assert c.orb <= 1.0 + 1e-6


def test_cusp_numbers_valid(transit_result):
    for c in transit_result.cusp_conjunctions:
        assert 1 <= c.cusp_number <= 12


def test_cusp_conjunctions_sorted(transit_result):
    orbs = [c.orb for c in transit_result.cusp_conjunctions]
    assert orbs == sorted(orbs)


def test_exact_jd_accuracy(transit_result):
    """For each aspect with exact_jd, the orb at that JD should be < 0.01°."""
    for a in transit_result.aspects:
        if a.exact_jd is None:
            continue
        r, _ = swe.calc_ut(a.exact_jd, a.transit_planet_id, FLAGS)
        arc_at_exact = _arc(r[0], a.natal_lon)
        from core.transits import ASPECT_ANGLES
        angle = ASPECT_ANGLES[a.aspect_type]
        residual = abs(arc_at_exact - angle)
        assert residual < 0.01, (
            f"{a.transit_planet_name}→{a.natal_planet_name} "
            f"{a.aspect_name}: residual at exact_jd = {residual:.4f}°"
        )


def test_cusp_exact_jd_accuracy(transit_result):
    """For cusp conjunctions with exact_jd, planet should be at cusp_lon."""
    for c in transit_result.cusp_conjunctions:
        if c.exact_jd is None:
            continue
        r, _ = swe.calc_ut(c.exact_jd, c.transit_planet_id, FLAGS)
        diff = abs((r[0] - c.cusp_lon + 180) % 360 - 180)
        assert diff < 0.01, (
            f"{c.transit_planet_name} cusp {c.cusp_number}: residual = {diff:.4f}°"
        )


# ── API endpoint tests ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def tr_chart():
    resp = client.post("/chart/transits", json=TR_REQUEST)
    assert resp.status_code == 200, f"API error: {resp.text}"
    return resp.json()


def test_tr_response_status():
    resp = client.post("/chart/transits", json=TR_REQUEST)
    assert resp.status_code == 200


def test_tr_top_level_fields(tr_chart):
    for f in ["natal_jd", "transit_jd", "transit_planets",
              "natal_planets", "aspects", "cusp_conjunctions"]:
        assert f in tr_chart, f"Missing field: {f}"


def test_tr_natal_jd_matches_birth(tr_chart):
    assert abs(tr_chart["natal_jd"] - BIRTH_JD) < 1.0


def test_tr_transit_jd_matches_date(tr_chart):
    assert abs(tr_chart["transit_jd"] - TRANSIT_JD) < 0.1


def test_tr_transit_planets_count(tr_chart):
    """7 traditional + True/Mean Node = 9 by default."""
    assert len(tr_chart["transit_planets"]) >= 7


def test_tr_natal_planets_seven(tr_chart):
    assert len(tr_chart["natal_planets"]) == 7
    names = {p["name"] for p in tr_chart["natal_planets"]}
    for n in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]:
        assert n in names


def test_tr_aspects_sorted_by_orb(tr_chart):
    orbs = [a["orb"] for a in tr_chart["aspects"]]
    assert orbs == sorted(orbs)


def test_tr_aspects_within_orb(tr_chart):
    for a in tr_chart["aspects"]:
        assert a["orb"] <= a["max_orb"] + 1e-5


def test_tr_aspect_types_valid(tr_chart):
    for a in tr_chart["aspects"]:
        assert 0 <= a["aspect_type"] <= 4


def test_tr_applying_is_bool(tr_chart):
    for a in tr_chart["aspects"]:
        assert isinstance(a["applying"], bool)


def test_tr_cusp_numbers_valid(tr_chart):
    for c in tr_chart["cusp_conjunctions"]:
        assert 1 <= c["cusp_number"] <= 12


def test_tr_cusp_orb_within_limit(tr_chart):
    for c in tr_chart["cusp_conjunctions"]:
        assert c["orb"] <= 1.0 + 1e-5


def test_tr_cusp_conjunctions_absent_when_disabled():
    resp = client.post("/chart/transits", json={
        **TR_REQUEST, "include_cusp_conjunctions": False
    }).json()
    assert resp["cusp_conjunctions"] == []


def test_tr_orb_param_limits_aspects():
    wide   = client.post("/chart/transits", json={**TR_REQUEST, "orb": 8.0}).json()
    narrow = client.post("/chart/transits", json={**TR_REQUEST, "orb": 0.5}).json()
    assert len(narrow["aspects"]) <= len(wide["aspects"])


def test_tr_outer_planets_in_transit():
    resp = client.post("/chart/transits", json={
        **TR_REQUEST, "include_outer": True
    }).json()
    names = {p["name"] for p in resp["transit_planets"]}
    assert "Uranus" in names
    assert "Neptune" in names
    assert "Pluto" in names


def test_tr_exact_jd_is_valid_or_null(tr_chart):
    for a in tr_chart["aspects"]:
        if a["exact_jd"] is not None:
            assert a["exact_jd"] > 0
            # JD must be within reasonable range (±90 days of transit)
            assert abs(a["exact_jd"] - tr_chart["transit_jd"]) <= 91.0
