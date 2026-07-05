"""
Epic 8.1 — Synastry Aspects tests.

POST /chart/synastry compares two natal charts:
  - Cross-aspects: A's planets vs B's planets (5 Ptolemaic aspects)
  - Overlay houses: A planets in B's houses, B planets in A's houses
  - Antiscia synastry: shadow points of A vs B planets and vice versa

Verifies:
  1.  Core: result type is SynastryResult
  2.  Core: cross_aspects is a list
  3.  Core: a_planets_in_b_houses has exactly 7 entries
  4.  Core: b_planets_in_a_houses has exactly 7 entries
  5.  Core: all overlay houses are in 1–12
  6.  Core: all cross-aspect orbs <= max_orb
  7.  Core: cross-aspect aspect names are valid Ptolemaic names
  8.  Core: cross-aspect planet names are valid classical names
  9.  Core: self-synastry produces exactly 7 self-conjunctions (orb=0)
  10. Core: self-synastry self-conjunctions all have orb == 0.0
  11. Core: no duplicate (planet_a_id, planet_b_id, aspect_angle) triples
  12. Core: antiscia_aspects is a list
  13. Core: antiscia aspect orbs <= their max orb
  14. Core: antiscia source is "A" or "B"
  15. Core: antiscia shadow_type is "antiscion" or "contra_antiscion"
  16. Core: antiscia aspect names valid
  17. Core: antiscion formula — antiscion(0°) == 180°
  18. Core: antiscion formula — antiscion(90°) == 90°
  19. Core: contra-antiscion formula — contra_antiscion(45°) == 315°
  20. Core: exact conjunction — same longitude planets form conjunction orb 0.0
  21. Core: exact opposition — 180° apart planets form opposition orb 0.0
  22. Core: outside orb — no aspect for 90.1° arc with 7° square orb
  23. Core: overlay house boundary — planet at ASC degree → house 1
  24. Core: overlay planet_lon matches input longitude
  25. Core: cross-aspect symmetry (A vs B and B vs A give same orbs)
  26. API: POST /chart/synastry returns 200
  27. API: cross_aspects not empty for different charts
  28. API: a_planets_in_b_houses count == 7
  29. API: b_planets_in_a_houses count == 7
  30. API: all overlay houses 1–12
  31. API: all aspect orbs <= max_orb
  32. API: self-synastry has 7 self-conjunctions with orb 0.0
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.synastry import (
    calc_synastry, SynastryResult,
    SYNASTRY_ORBS, ANTISCIA_ORBS, ASPECT_NAMES,
    _antiscion, _contra_antiscion, _arc,
)

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

client = TestClient(app)

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

_VALID_PLANETS = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
_VALID_ASPECTS = set(ASPECT_NAMES.values())
_VALID_SHADOW_TYPES = {"antiscion", "contra_antiscion"}


def _make_chart(y, m, d, h, lat, lon, hsys="P"):
    jd = swe.julday(y, m, d, h, swe.GREG_CAL)
    lons: dict[int, float] = {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, _FLAGS)
        lons[pid] = r[0]
    cusps_raw, _ = swe.houses(jd, lat, lon, hsys.encode())
    return lons, list(cusps_raw)   # 12 cusp longitudes


# Chart A: Rome 1990-06-15 10:30
LONS_A, CUSPS_A = _make_chart(1990, 6, 15, 10.5, 41.9, 12.5)
# Chart B: London 1985-01-01 08:00
LONS_B, CUSPS_B = _make_chart(1985, 1, 1, 8.0, 51.5, 0.0)

# Self-synastry
LONS_SELF = LONS_A
CUSPS_SELF = CUSPS_A

# API request bodies
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

SYNASTRY_REQ = {"chart_a": CHART_A_REQ, "chart_b": CHART_B_REQ}
SELF_REQ     = {"chart_a": CHART_A_REQ, "chart_b": CHART_A_REQ}


@pytest.fixture(scope="module")
def result():
    return calc_synastry(LONS_A, LONS_B, CUSPS_A, CUSPS_B)


@pytest.fixture(scope="module")
def self_result():
    return calc_synastry(LONS_SELF, LONS_SELF, CUSPS_SELF, CUSPS_SELF)


# ── Core tests ─────────────────────────────────────────────────────────────────

def test_result_type(result):
    assert isinstance(result, SynastryResult)


def test_cross_aspects_is_list(result):
    assert isinstance(result.cross_aspects, list)


def test_a_in_b_houses_count(result):
    assert len(result.a_planets_in_b_houses) == 7


def test_b_in_a_houses_count(result):
    assert len(result.b_planets_in_a_houses) == 7


def test_overlay_houses_in_range(result):
    for p in result.a_planets_in_b_houses + result.b_planets_in_a_houses:
        assert 1 <= p.house <= 12, f"{p.planet_name} house={p.house}"


def test_cross_aspect_orbs_valid(result):
    for a in result.cross_aspects:
        assert a.orb <= a.max_orb, (
            f"{a.planet_a_name}/{a.planet_b_name}: orb={a.orb} > max={a.max_orb}"
        )


def test_cross_aspect_names_valid(result):
    for a in result.cross_aspects:
        assert a.aspect_name in _VALID_ASPECTS


def test_cross_aspect_planet_names_valid(result):
    for a in result.cross_aspects:
        assert a.planet_a_name in _VALID_PLANETS
        assert a.planet_b_name in _VALID_PLANETS


def test_self_synastry_seven_self_conjunctions(self_result):
    self_conj = [
        a for a in self_result.cross_aspects
        if a.planet_a_id == a.planet_b_id and a.aspect_angle == 0
    ]
    assert len(self_conj) == 7


def test_self_synastry_self_conjunctions_orb_zero(self_result):
    self_conj = [
        a for a in self_result.cross_aspects
        if a.planet_a_id == a.planet_b_id and a.aspect_angle == 0
    ]
    for a in self_conj:
        assert a.orb == 0.0, f"{a.planet_a_name}: orb={a.orb}"


def test_no_duplicate_aspects(result):
    seen = set()
    for a in result.cross_aspects:
        key = (a.planet_a_id, a.planet_b_id, a.aspect_angle)
        assert key not in seen, f"Duplicate: {key}"
        seen.add(key)


def test_antiscia_aspects_is_list(result):
    assert isinstance(result.antiscia_aspects, list)


def test_antiscia_orbs_valid(result):
    for a in result.antiscia_aspects:
        max_orb = ANTISCIA_ORBS[a.aspect_angle]
        assert a.orb <= max_orb, (
            f"orb={a.orb} > max={max_orb} for angle={a.aspect_angle}"
        )


def test_antiscia_source_valid(result):
    for a in result.antiscia_aspects:
        assert a.source in {"A", "B"}


def test_antiscia_shadow_type_valid(result):
    for a in result.antiscia_aspects:
        assert a.shadow_type in _VALID_SHADOW_TYPES


def test_antiscia_aspect_names_valid(result):
    for a in result.antiscia_aspects:
        assert a.aspect_name in _VALID_ASPECTS


def test_antiscion_formula_0():
    assert abs(_antiscion(0.0) - 180.0) < 0.001


def test_antiscion_formula_90():
    assert abs(_antiscion(90.0) - 90.0) < 0.001


def test_contra_antiscion_formula_45():
    assert abs(_contra_antiscion(45.0) - 315.0) < 0.001


def test_exact_conjunction():
    """Same-longitude planets form exact conjunctions with orb 0.0 (49 pairs, all same lon)."""
    lons = {pid: 45.0 for pid in range(7)}   # all at 45°
    cusps = [i * 30.0 for i in range(12)]
    r = calc_synastry(lons, lons, cusps, cusps)
    conj_orb_zero = [a for a in r.cross_aspects if a.aspect_angle == 0 and a.orb == 0.0]
    # 7×7=49 pairs all conjunct — all with orb 0.0
    assert len(conj_orb_zero) == 49
    assert all(a.orb == 0.0 for a in conj_orb_zero)


def test_exact_opposition():
    """Planets 180° apart form an opposition with orb 0.0."""
    lons_a = {pid: 0.0 for pid in range(7)}
    lons_b = {pid: 180.0 for pid in range(7)}
    cusps = [i * 30.0 for i in range(12)]
    r = calc_synastry(lons_a, lons_b, cusps, cusps)
    opps = [a for a in r.cross_aspects if a.aspect_angle == 180 and a.orb == 0.0]
    assert len(opps) == 7 * 7   # all 49 pairs form exact opposition... wait
    # Actually all 7 A planets at 0° vs all 7 B planets at 180° = 49 exact oppositions
    assert len(opps) == 49


def test_outside_orb_no_square():
    """91° arc with 7° square orb should produce no square."""
    lons_a = {0: 0.0}
    lons_b = {0: 91.0}
    # Pad remaining planets far away
    for pid in range(1, 7):
        lons_a[pid] = 200.0 + pid
        lons_b[pid] = 200.0 + pid
    cusps = [i * 30.0 for i in range(12)]
    r = calc_synastry(lons_a, lons_b, cusps, cusps)
    # 91° arc vs 90° square → orb = 1° which is within 7° → should have square!
    # Let's use 100° which is outside square orb (100-90=10 > 7)
    lons_a2 = {pid: (200.0 + pid if pid > 0 else 0.0) for pid in range(7)}
    lons_b2 = {pid: (200.0 + pid if pid > 0 else 100.0) for pid in range(7)}
    r2 = calc_synastry(lons_a2, lons_b2, cusps, cusps)
    sun_sq = [a for a in r2.cross_aspects
              if a.planet_a_id == 0 and a.planet_b_id == 0 and a.aspect_angle == 90]
    assert len(sun_sq) == 0


def test_overlay_planet_at_asc():
    """A planet at the ASC of chart B should fall in house 1."""
    asc_lon = CUSPS_B[0]   # house 1 cusp = ASC
    lons_a_mod = dict(LONS_A)
    lons_a_mod[0] = asc_lon + 0.1   # Sun just past the ASC → house 1
    r = calc_synastry(lons_a_mod, LONS_B, CUSPS_A, CUSPS_B)
    sun_entry = next(p for p in r.a_planets_in_b_houses if p.planet_id == 0)
    assert sun_entry.house == 1


def test_overlay_planet_lon_matches_input(result):
    for p in result.a_planets_in_b_houses:
        assert abs(p.planet_lon - round(LONS_A[p.planet_id], 4)) < 0.001


def test_cross_aspect_symmetry():
    """A→B and B→A give same aspect types and same orbs (just swapped)."""
    r_ab = calc_synastry(LONS_A, LONS_B, CUSPS_A, CUSPS_B)
    r_ba = calc_synastry(LONS_B, LONS_A, CUSPS_B, CUSPS_A)
    # Build set of (a_id, b_id, angle, orb) from AB and (b_id, a_id, angle, orb) from BA
    ab_set = {(a.planet_a_id, a.planet_b_id, a.aspect_angle, a.orb) for a in r_ab.cross_aspects}
    ba_set = {(a.planet_b_id, a.planet_a_id, a.aspect_angle, a.orb) for a in r_ba.cross_aspects}
    assert ab_set == ba_set


# ── API endpoint tests ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_resp():
    r = client.post("/chart/synastry", json=SYNASTRY_REQ)
    assert r.status_code == 200
    return r.json()


@pytest.fixture(scope="module")
def api_self():
    r = client.post("/chart/synastry", json=SELF_REQ)
    assert r.status_code == 200
    return r.json()


def test_api_200(api_resp):
    assert "cross_aspects" in api_resp


def test_api_cross_aspects_nonempty(api_resp):
    assert len(api_resp["cross_aspects"]) > 0


def test_api_a_in_b_count(api_resp):
    assert len(api_resp["a_planets_in_b_houses"]) == 7


def test_api_b_in_a_count(api_resp):
    assert len(api_resp["b_planets_in_a_houses"]) == 7


def test_api_overlay_houses_valid(api_resp):
    for p in api_resp["a_planets_in_b_houses"] + api_resp["b_planets_in_a_houses"]:
        assert 1 <= p["house"] <= 12


def test_api_aspect_orbs_valid(api_resp):
    for a in api_resp["cross_aspects"]:
        assert a["orb"] <= a["max_orb"]


def test_api_self_synastry_seven_self_conjunctions(api_self):
    self_conj = [
        a for a in api_self["cross_aspects"]
        if a["planet_a_id"] == a["planet_b_id"] and a["aspect_angle"] == 0
    ]
    assert len(self_conj) == 7


def test_api_self_synastry_orb_zero(api_self):
    self_conj = [
        a for a in api_self["cross_aspects"]
        if a["planet_a_id"] == a["planet_b_id"] and a["aspect_angle"] == 0
    ]
    for a in self_conj:
        assert a["orb"] == 0.0


def test_api_aspect_names_valid(api_resp):
    for a in api_resp["cross_aspects"]:
        assert a["aspect_name"] in _VALID_ASPECTS


def test_api_planet_names_valid(api_resp):
    for p in api_resp["a_planets_in_b_houses"] + api_resp["b_planets_in_a_houses"]:
        assert p["planet_name"] in _VALID_PLANETS
