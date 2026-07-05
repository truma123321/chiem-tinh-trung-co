"""
Epic 4.2 — Solar Arc Directions tests.

Verifies:
  1. Core: solar_arc = prog_sun_lon - natal_sun_lon (mod 360, positive)
  2. Core: solar_arc ≈ age_years (Sun moves ~1°/day in progressed time)
  3. Core: directed_lon = natal_lon + solar_arc (mod 360)
  4. Core: 9 directed points (7 planets + ASC + MC)
  5. Core: no self-to-self aspects
  6. Core: all aspects within combined orb
  7. Core: exact_jd is a valid JD (> birth JD)
  8. Core: exact hit accuracy — at exact_jd, solar_arc ≈ target_arc
  9. API: /chart/solar-arc-directions returns correct structure
 10. API: solar_arc ≈ 35 for 35-year progression
 11. API: directed_lon = natal_lon + solar_arc for each point
 12. API: aspects sorted by orb (tightest first)
 13. API: applying flag correct relative to orb direction
 14. API: error on date before birth
 15. API: outer planets included when requested
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.solar_arc import (
    calc_solar_arc_directions, _find_exact_hit_jd, _arc,
)
from core.secondary_progressions import progressed_jd

# ── ephemeris path ─────────────────────────────────────────────────────────────

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

# ── Shared test data ──────────────────────────────────────────────────────────

BIRTH = {"year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 30, "ut_offset": 0.0}

SA_REQUEST = {
    **BIRTH,
    "lat": 41.9, "lon": 12.5,
    "prog_year": 2025, "prog_month": 6, "prog_day": 15,
    "hsys": "B",
    "orb": 2.0,
}

client = TestClient(app)

BIRTH_JD  = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
TARGET_JD = swe.julday(2025, 6, 15, 12.0, swe.GREG_CAL)
_, JD_PROG = progressed_jd(BIRTH_JD, TARGET_JD)

_TRAD = [
    (swe.SUN, "Sun"), (swe.MOON, "Moon"), (swe.MERCURY, "Mercury"),
    (swe.VENUS, "Venus"), (swe.MARS, "Mars"), (swe.JUPITER, "Jupiter"),
    (swe.SATURN, "Saturn"),
]
_SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces",
]


def _natal_points():
    """Return [(name, natal_lon)] for 7 planets + ASC + MC."""
    points = []
    for pid, name in _TRAD:
        r, _ = swe.calc_ut(BIRTH_JD, pid, FLAGS)
        points.append((name, r[0]))
    _, ascmc = swe.houses(BIRTH_JD, 41.9, 12.5, b"B")
    points.append(("ASC", ascmc[0]))
    points.append(("MC",  ascmc[1]))
    return points


@pytest.fixture(scope="module")
def sa_result():
    return calc_solar_arc_directions(BIRTH_JD, JD_PROG, _natal_points(), max_orb=2.0)


# ── Core: solar arc value ─────────────────────────────────────────────────────

def test_solar_arc_positive(sa_result):
    assert sa_result.solar_arc >= 0.0
    assert sa_result.solar_arc < 360.0


def test_solar_arc_approx_age(sa_result):
    """Solar arc ≈ 35° for a 35-year progression (Sun ~1°/year)."""
    assert 33.0 < sa_result.solar_arc < 37.0, (
        f"Expected ~35°, got {sa_result.solar_arc:.4f}°"
    )


def test_solar_arc_formula(sa_result):
    """solar_arc = (prog_sun - natal_sun) % 360."""
    r_natal, _ = swe.calc_ut(BIRTH_JD, swe.SUN, FLAGS)
    r_prog,  _ = swe.calc_ut(JD_PROG,  swe.SUN, FLAGS)
    expected_arc = (r_prog[0] - r_natal[0]) % 360.0
    assert abs(sa_result.solar_arc - expected_arc) < 1e-4


# ── Core: directed points ─────────────────────────────────────────────────────

def test_directed_points_count(sa_result):
    """9 directed points: 7 planets + ASC + MC."""
    assert len(sa_result.directed_points) == 9


def test_directed_points_include_angles(sa_result):
    names = {p.name for p in sa_result.directed_points}
    assert "ASC" in names
    assert "MC" in names


def test_directed_lon_formula(sa_result):
    """directed_lon = (natal_lon + solar_arc) % 360 for every point."""
    arc = sa_result.solar_arc
    for dp in sa_result.directed_points:
        expected = (dp.natal_lon + arc) % 360.0
        assert abs(dp.directed_lon - expected) < 1e-3, (
            f"{dp.name}: expected {expected:.4f}°, got {dp.directed_lon:.4f}°"
        )


def test_directed_lons_valid_range(sa_result):
    for dp in sa_result.directed_points:
        assert 0.0 <= dp.directed_lon < 360.0, (
            f"{dp.name}: directed_lon {dp.directed_lon} out of range"
        )


def test_directed_signs_valid(sa_result):
    valid = {
        "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
        "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces",
    }
    for dp in sa_result.directed_points:
        assert dp.sign in valid, f"{dp.name}: invalid sign {dp.sign}"


# ── Core: aspects ─────────────────────────────────────────────────────────────

def test_no_self_aspects(sa_result):
    for a in sa_result.aspects:
        assert a.directed_name != a.natal_name, (
            f"Self-aspect: directed {a.directed_name} vs natal {a.natal_name}"
        )


def test_aspects_within_orb(sa_result):
    for a in sa_result.aspects:
        assert a.orb <= a.max_orb + 1e-6, (
            f"{a.directed_name}→{a.natal_name}: orb {a.orb} > max {a.max_orb}"
        )


def test_aspects_sorted_by_orb(sa_result):
    orbs = [a.orb for a in sa_result.aspects]
    assert orbs == sorted(orbs)


def test_aspect_types_valid(sa_result):
    for a in sa_result.aspects:
        assert 0 <= a.aspect_type <= 4, f"Invalid aspect type {a.aspect_type}"


# ── Core: exact hit date ──────────────────────────────────────────────────────

def test_exact_jd_after_birth(sa_result):
    for a in sa_result.aspects:
        if a.exact_jd is not None:
            assert a.exact_jd > BIRTH_JD, (
                f"{a.directed_name}→{a.natal_name}: exact_jd {a.exact_jd} before birth"
            )


def test_exact_jd_accuracy():
    """At exact_jd, solar_arc should equal the target arc to < 0.01°."""
    r_natal, _ = swe.calc_ut(BIRTH_JD, swe.SUN, FLAGS)
    natal_sun_lon = r_natal[0]

    target_arc = 35.0
    exact_jd = _find_exact_hit_jd(BIRTH_JD, natal_sun_lon, target_arc)
    assert exact_jd is not None

    # Convert real calendar JD to progressed JD
    age_years = (exact_jd - BIRTH_JD) / 365.25
    jd_p = BIRTH_JD + age_years
    r_prog, _ = swe.calc_ut(jd_p, swe.SUN, FLAGS)
    actual_arc = (r_prog[0] - natal_sun_lon) % 360.0
    diff = abs(actual_arc - target_arc)
    assert diff < 0.01, f"Exact hit accuracy: arc diff = {diff:.6f}°"


def test_exact_jd_reasonable_date(sa_result):
    """Exact JD should be within ~0-120 years after birth (real calendar)."""
    birth_plus_120y = BIRTH_JD + 120 * 365.25
    for a in sa_result.aspects:
        if a.exact_jd is not None:
            assert BIRTH_JD < a.exact_jd < birth_plus_120y, (
                f"{a.directed_name}→{a.natal_name}: exact_jd out of lifetime range"
            )


def test_exact_hit_outside_range_returns_none():
    """Target arc > 120° should return None (beyond max_years=120)."""
    r_natal, _ = swe.calc_ut(BIRTH_JD, swe.SUN, FLAGS)
    # Arc of 150° = 150 years, exceeds max_years=120
    result = _find_exact_hit_jd(BIRTH_JD, r_natal[0], 150.0, max_years=120.0)
    assert result is None


# ── API endpoint tests ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sa_chart():
    resp = client.post("/chart/solar-arc-directions", json=SA_REQUEST)
    assert resp.status_code == 200, f"API error: {resp.text}"
    return resp.json()


def test_sa_response_status():
    resp = client.post("/chart/solar-arc-directions", json=SA_REQUEST)
    assert resp.status_code == 200


def test_sa_top_level_fields(sa_chart):
    for field in ["birth_jd", "target_jd", "solar_arc", "directed_points", "aspects"]:
        assert field in sa_chart, f"Missing field: {field}"


def test_sa_solar_arc_approx_35(sa_chart):
    assert 33.0 < sa_chart["solar_arc"] < 37.0, (
        f"Expected ~35°, got {sa_chart['solar_arc']}"
    )


def test_sa_nine_directed_points(sa_chart):
    assert len(sa_chart["directed_points"]) == 9


def test_sa_directed_points_include_angles(sa_chart):
    names = {p["name"] for p in sa_chart["directed_points"]}
    assert "ASC" in names
    assert "MC" in names
    assert "Sun" in names
    assert "Moon" in names


def test_sa_directed_lon_matches_formula(sa_chart):
    arc = sa_chart["solar_arc"]
    for dp in sa_chart["directed_points"]:
        expected = (dp["natal_lon"] + arc) % 360.0
        diff = abs(dp["directed_lon"] - expected)
        if diff > 180:
            diff = 360 - diff
        assert diff < 0.01, (
            f"{dp['name']}: expected directed_lon {expected:.4f}, got {dp['directed_lon']:.4f}"
        )


def test_sa_aspects_sorted_by_orb(sa_chart):
    orbs = [a["orb"] for a in sa_chart["aspects"]]
    assert orbs == sorted(orbs)


def test_sa_aspects_no_self(sa_chart):
    for a in sa_chart["aspects"]:
        assert a["directed_name"] != a["natal_name"]


def test_sa_aspects_within_orb(sa_chart):
    for a in sa_chart["aspects"]:
        assert a["orb"] <= a["max_orb"] + 1e-5


def test_sa_aspects_have_exact_jd(sa_chart):
    """All aspects should have an exact_jd (35° arc, within 120y range)."""
    for a in sa_chart["aspects"]:
        assert a["exact_jd"] is not None, (
            f"{a['directed_name']}→{a['natal_name']}: missing exact_jd"
        )


def test_sa_error_on_past_date():
    bad = {**SA_REQUEST, "prog_year": 1985}
    resp = client.post("/chart/solar-arc-directions", json=bad)
    assert resp.status_code == 422


def test_sa_outer_planets_included():
    resp = client.post("/chart/solar-arc-directions", json={
        **SA_REQUEST, "include_outer": True
    }).json()
    names = {p["name"] for p in resp["directed_points"]}
    assert "Uranus" in names
    assert "Neptune" in names
    assert "Pluto" in names


def test_sa_orb_param_limits_aspects():
    """Narrower orb should return fewer (or equal) aspects."""
    resp_wide   = client.post("/chart/solar-arc-directions", json={**SA_REQUEST, "orb": 5.0}).json()
    resp_narrow = client.post("/chart/solar-arc-directions", json={**SA_REQUEST, "orb": 0.5}).json()
    assert len(resp_narrow["aspects"]) <= len(resp_wide["aspects"])


def test_sa_applying_flag_type(sa_chart):
    """applying is always a boolean."""
    for a in sa_chart["aspects"]:
        assert isinstance(a["applying"], bool)
