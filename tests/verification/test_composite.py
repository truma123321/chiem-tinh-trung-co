"""
Epic 8.2 — Composite Chart (midpoint method) tests.

POST /chart/composite computes the near midpoint of corresponding points
from two natal charts:
  - 7 classical planets (Sun–Saturn)
  - Ascendant and Midheaven
  - Aspects between composite planets

Near midpoint: on the shorter arc between two ecliptic longitudes.

Verifies:
  1.  Core: result type is CompositeResult
  2.  Core: exactly 7 composite planets
  3.  Core: planets ordered by planet_id (0–6)
  4.  Core: all composite lons in [0°, 360°)
  5.  Core: sign_lon = lon % 30 (within 0.001)
  6.  Core: sign names are valid zodiac signs
  7.  Core: midpoint formula — midpoint(0°, 90°) == 45°
  8.  Core: midpoint wrap — midpoint(350°, 10°) == 0°
  9.  Core: midpoint wrap symmetry — midpoint(A,B) == midpoint(B,A)
  10. Core: midpoint(90°, 270°) == 180° (shorter arc midpoint)
  11. Core: self-composite planets == natal planets (same chart)
  12. Core: self-composite ASC == natal ASC
  13. Core: self-composite MC == natal MC
  14. Core: composite ASC in [0°, 360°)
  15. Core: composite MC in [0°, 360°)
  16. Core: aspects list is a list
  17. Core: all aspect orbs <= max_orb
  18. Core: aspect names valid Ptolemaic names
  19. Core: no self-aspects (planet_a_id != planet_b_id)
  20. Core: no duplicate aspects (planet_a_id, planet_b_id, angle)
  21. Core: aspect planet_a_id < planet_b_id (unique pairs)
  22. Core: retrograde True only if both natal planets retrograde
  23. Core: composite lon matches formula for known planets
  24. Core: asc_sign matches sign of composite ASC
  25. Core: mc_sign matches sign of composite MC
  26. API: POST /chart/composite returns 200
  27. API: planets count == 7
  28. API: all lons in [0°, 360°)
  29. API: all signs valid
  30. API: all aspect orbs <= max_orb
  31. API: asc in [0°, 360°)
  32. API: mc in [0°, 360°)
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.composite import (
    calc_composite, CompositeResult,
    COMPOSITE_ORBS, ASPECT_NAMES,
    _midpoint, _arc,
)

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

client = TestClient(app)

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

_VALID_SIGNS = {
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
}
_VALID_ASPECTS = set(ASPECT_NAMES.values())


def _get_chart(y, m, d, h, lat, lon, hsys="P"):
    jd = swe.julday(y, m, d, h, swe.GREG_CAL)
    lons, speeds = {}, {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, _FLAGS)
        lons[pid] = r[0]
        speeds[pid] = r[3]
    _, ascmc = swe.houses(jd, lat, lon, hsys.encode())
    return lons, speeds, ascmc[0], ascmc[1]


# Chart A: Rome 1990-06-15 10:30
LONS_A, SPEEDS_A, ASC_A, MC_A = _get_chart(1990, 6, 15, 10.5, 41.9, 12.5)
# Chart B: London 1985-01-01 08:00
LONS_B, SPEEDS_B, ASC_B, MC_B = _get_chart(1985, 1, 1, 8.0, 51.5, 0.0)

CHART_A_REQ = {
    "year": 1990, "month": 6, "day": 15,
    "hour": 10, "minute": 30,
    "lat": 41.9, "lon": 12.5, "hsys": "P", "ut_offset": 0,
}
CHART_B_REQ = {
    "year": 1985, "month": 1, "day": 1,
    "hour": 8, "minute": 0,
    "lat": 51.5, "lon": 0.0, "hsys": "P", "ut_offset": 0,
}

COMPOSITE_REQ = {"chart_a": CHART_A_REQ, "chart_b": CHART_B_REQ}
SELF_REQ      = {"chart_a": CHART_A_REQ, "chart_b": CHART_A_REQ}


@pytest.fixture(scope="module")
def result():
    return calc_composite(LONS_A, LONS_B, SPEEDS_A, SPEEDS_B, ASC_A, ASC_B, MC_A, MC_B)


@pytest.fixture(scope="module")
def self_result():
    return calc_composite(LONS_A, LONS_A, SPEEDS_A, SPEEDS_A, ASC_A, ASC_A, MC_A, MC_A)


# ── Core tests ─────────────────────────────────────────────────────────────────

def test_result_type(result):
    assert isinstance(result, CompositeResult)


def test_seven_planets(result):
    assert len(result.planets) == 7


def test_planets_ordered_by_id(result):
    ids = [p.planet_id for p in result.planets]
    assert ids == list(range(7))


def test_all_lons_in_range(result):
    for p in result.planets:
        assert 0.0 <= p.lon < 360.0, f"{p.planet_name}: lon={p.lon}"


def test_sign_lon_formula(result):
    """sign_lon must equal lon % 30."""
    for p in result.planets:
        expected = p.lon % 30.0
        assert abs(p.sign_lon - expected) < 0.001, (
            f"{p.planet_name}: sign_lon={p.sign_lon}, expected {expected:.4f}"
        )


def test_sign_names_valid(result):
    for p in result.planets:
        assert p.sign in _VALID_SIGNS, f"{p.planet_name}: sign='{p.sign}'"


def test_midpoint_0_90():
    assert abs(_midpoint(0.0, 90.0) - 45.0) < 0.001


def test_midpoint_wrap_350_10():
    """350° and 10° → near midpoint = 0°."""
    assert abs(_midpoint(350.0, 10.0)) < 0.001 or abs(_midpoint(350.0, 10.0) - 360.0) < 0.001


def test_midpoint_symmetry():
    """midpoint(A, B) == midpoint(B, A)."""
    pairs = [(0, 90), (350, 10), (45, 315), (120, 240), (1, 359)]
    for a, b in pairs:
        assert abs(_midpoint(a, b) - _midpoint(b, a)) < 0.001, (
            f"midpoint({a},{b})={_midpoint(a,b)}, midpoint({b},{a})={_midpoint(b,a)}"
        )


def test_midpoint_90_270():
    """midpoint(90°, 270°) == 180° (shorter arc midpoint)."""
    assert abs(_midpoint(90.0, 270.0) - 180.0) < 0.001


def test_self_composite_planets(self_result):
    """Self-composite of same chart produces the original positions."""
    for p in self_result.planets:
        orig_lon = round(LONS_A[p.planet_id] % 360.0, 4)
        assert abs(p.lon - orig_lon) < 0.01, (
            f"{p.planet_name}: composite={p.lon}, original={orig_lon}"
        )


def test_self_composite_asc(self_result):
    assert abs(self_result.asc - round(ASC_A % 360.0, 4)) < 0.01


def test_self_composite_mc(self_result):
    assert abs(self_result.mc - round(MC_A % 360.0, 4)) < 0.01


def test_asc_in_range(result):
    assert 0.0 <= result.asc < 360.0


def test_mc_in_range(result):
    assert 0.0 <= result.mc < 360.0


def test_aspects_is_list(result):
    assert isinstance(result.aspects, list)


def test_aspect_orbs_valid(result):
    for a in result.aspects:
        assert a.orb <= a.max_orb, (
            f"{a.planet_a_name}/{a.planet_b_name}: orb={a.orb} > max={a.max_orb}"
        )


def test_aspect_names_valid(result):
    for a in result.aspects:
        assert a.aspect_name in _VALID_ASPECTS


def test_no_self_aspects(result):
    for a in result.aspects:
        assert a.planet_a_id != a.planet_b_id


def test_no_duplicate_aspects(result):
    seen = set()
    for a in result.aspects:
        key = (a.planet_a_id, a.planet_b_id, a.aspect_angle)
        assert key not in seen, f"Duplicate: {key}"
        seen.add(key)


def test_aspects_unique_pairs(result):
    """planet_a_id < planet_b_id in all aspects (unique ordered pairs)."""
    for a in result.aspects:
        assert a.planet_a_id < a.planet_b_id, (
            f"Unordered pair: {a.planet_a_id} > {a.planet_b_id}"
        )


def test_retrograde_both_required(result):
    """Composite retrograde is True only if both natal planets are retrograde."""
    for p in result.planets:
        pid = p.planet_id
        both_retro = (SPEEDS_A[pid] < 0) and (SPEEDS_B[pid] < 0)
        assert p.retrograde == both_retro, (
            f"{p.planet_name}: composite retrograde={p.retrograde}, "
            f"A_speed={SPEEDS_A[pid]:.4f}, B_speed={SPEEDS_B[pid]:.4f}"
        )


def test_composite_lon_formula(result):
    """Each composite lon == near midpoint of the two natal lons."""
    for p in result.planets:
        pid = p.planet_id
        expected = round(_midpoint(LONS_A[pid], LONS_B[pid]) % 360.0, 4)
        assert abs(p.lon - expected) < 0.001, (
            f"{p.planet_name}: got {p.lon}, expected {expected}"
        )


def test_asc_sign_matches_lon(result):
    sign_idx = int(result.asc / 30) % 12
    _SIGNS = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    ]
    assert result.asc_sign == _SIGNS[sign_idx]


def test_mc_sign_matches_lon(result):
    sign_idx = int(result.mc / 30) % 12
    _SIGNS = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    ]
    assert result.mc_sign == _SIGNS[sign_idx]


# ── API endpoint tests ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_resp():
    r = client.post("/chart/composite", json=COMPOSITE_REQ)
    assert r.status_code == 200
    return r.json()


@pytest.fixture(scope="module")
def api_self():
    r = client.post("/chart/composite", json=SELF_REQ)
    assert r.status_code == 200
    return r.json()


def test_api_200(api_resp):
    assert "planets" in api_resp


def test_api_seven_planets(api_resp):
    assert len(api_resp["planets"]) == 7


def test_api_lons_in_range(api_resp):
    for p in api_resp["planets"]:
        assert 0.0 <= p["lon"] < 360.0


def test_api_signs_valid(api_resp):
    for p in api_resp["planets"]:
        assert p["sign"] in _VALID_SIGNS


def test_api_aspect_orbs_valid(api_resp):
    for a in api_resp["aspects"]:
        assert a["orb"] <= a["max_orb"]


def test_api_asc_in_range(api_resp):
    assert 0.0 <= api_resp["asc"] < 360.0


def test_api_mc_in_range(api_resp):
    assert 0.0 <= api_resp["mc"] < 360.0
