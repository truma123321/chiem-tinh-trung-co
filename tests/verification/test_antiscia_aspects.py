"""
Epic 6.7 — Antiscia: All 5 Major Aspects tests.

Aspects checked: Conjunction (0°), Sextile (60°), Square (90°),
                 Trine (120°), Opposition (180°).
Orbs: Conjunction 1°, all others 0.5°.

Verifies:
  1.  Core: ANTISCIA_ASPECTS dict has exactly 5 entries
  2.  Core: ANTISCIA_ASPECTS keys are {0, 60, 90, 120, 180}
  3.  Core: ANTISCIA_ORB == 1.0, ANTISCIA_ASPECT_ORB == 0.5
  4.  Core: each AntisciaAspect has aspect_angle + aspect_name
  5.  Core: aspect_angle values in {0, 60, 90, 120, 180}
  6.  Core: aspect_name matches angle (Conjunction/Sextile/Square/Trine/Opposition)
  7.  Core: conjunction orbs <= 1.0°
  8.  Core: non-conjunction orbs <= 0.5°
  9.  Core: all orbs >= 0°
 10.  Core: aspect_type in {"antiscion", "contra_antiscion"}
 11.  Core: antiscion conjunction detected (Moon at Sun's antiscion)
 12.  Core: antiscion sextile detected (Moon 60° from Sun's antiscion)
 13.  Core: antiscion square detected (Moon 90° from Sun's antiscion)
 14.  Core: antiscion trine detected (Moon 120° from Sun's antiscion)
 15.  Core: antiscion opposition detected (Moon 180° from Sun's antiscion)
 16.  Core: contra-antiscion conjunction detected
 17.  Core: contra-antiscion sextile detected
 18.  Core: contra-antiscion square detected
 19.  Core: contra-antiscion trine detected
 20.  Core: contra-antiscion opposition detected
 21.  Core: conjunction at orb boundary (1.0°) included
 22.  Core: conjunction outside orb (1.1°) excluded
 23.  Core: non-conj at orb boundary (0.5°) included
 24.  Core: non-conj outside orb (0.6°) excluded
 25.  Core: no duplicate (A, B, type, angle) pairs
 26.  Core: aspects sorted by orb tightest first
 27.  API: aspect_angle in {0, 60, 90, 120, 180}
 28.  API: aspect_name present and valid
 29.  API: non-conjunction aspects present (Rome 1990 chart)
 30.  API: conjunction orbs <= 1.0, non-conj orbs <= 0.5
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.antiscia import (
    calc_antiscia, ANTISCIA_ORB, ANTISCIA_ASPECT_ORB, ANTISCIA_ASPECTS,
    _antiscion, _contra,
)

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

client = TestClient(app)

NATAL_REQ = {
    "year": 1990, "month": 6, "day": 15,
    "hour": 10, "minute": 30,
    "lat": 41.9, "lon": 12.5,
    "hsys": "P",
    "ut_offset": 0,
}

VALID_ANGLES = {0, 60, 90, 120, 180}
VALID_NAMES  = {"Conjunction", "Sextile", "Square", "Trine", "Opposition"}
VALID_TYPES  = {"antiscion", "contra_antiscion"}

JD_ROME = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)


def _all_at(lon: float, overrides: dict | None = None) -> dict:
    """All 7 planets at lon, with optional overrides."""
    lons = {pid: lon for pid in range(7)}
    if overrides:
        lons.update(overrides)
    return lons


@pytest.fixture(scope="module")
def rome_result():
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    lons = {}
    for pid in range(7):
        r, _ = swe.calc_ut(JD_ROME, pid, FLAGS)
        lons[pid] = r[0]
    return calc_antiscia(lons)


@pytest.fixture(scope="module")
def api_resp():
    resp = client.post("/chart/natal", json=NATAL_REQ)
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture(scope="module")
def api_anti(api_resp):
    return api_resp["antiscia"]


# ── Constants ──────────────────────────────────────────────────────────────────

def test_antiscia_aspects_dict_five_entries():
    assert len(ANTISCIA_ASPECTS) == 5


def test_antiscia_aspects_dict_keys():
    assert set(ANTISCIA_ASPECTS.keys()) == VALID_ANGLES


def test_orb_constants():
    assert ANTISCIA_ORB == 1.0
    assert ANTISCIA_ASPECT_ORB == 0.5


# ── Field structure ────────────────────────────────────────────────────────────

def test_core_aspect_has_angle_and_name(rome_result):
    for a in rome_result.aspects:
        assert hasattr(a, "aspect_angle")
        assert hasattr(a, "aspect_name")


def test_core_aspect_angles_valid(rome_result):
    for a in rome_result.aspects:
        assert a.aspect_angle in VALID_ANGLES


def test_core_aspect_names_valid(rome_result):
    for a in rome_result.aspects:
        assert a.aspect_name in VALID_NAMES


def test_core_name_matches_angle(rome_result):
    name_map = {0: "Conjunction", 60: "Sextile", 90: "Square",
                120: "Trine", 180: "Opposition"}
    for a in rome_result.aspects:
        assert a.aspect_name == name_map[a.aspect_angle]


def test_core_conjunction_orbs_max_1(rome_result):
    for a in rome_result.aspects:
        if a.aspect_angle == 0:
            assert a.orb <= ANTISCIA_ORB


def test_core_non_conj_orbs_max_half(rome_result):
    for a in rome_result.aspects:
        if a.aspect_angle != 0:
            assert a.orb <= ANTISCIA_ASPECT_ORB


def test_core_orbs_non_negative(rome_result):
    for a in rome_result.aspects:
        assert a.orb >= 0.0


def test_core_aspect_type_valid(rome_result):
    for a in rome_result.aspects:
        assert a.aspect_type in VALID_TYPES


# ── Antiscion aspect detection ─────────────────────────────────────────────────

def _detect_anti(sun_lon, moon_target, expected_angle):
    """Sun at sun_lon, Moon at moon_target; return antiscion aspects at expected_angle."""
    lons = _all_at(200.0, {0: sun_lon, 1: moon_target % 360.0})
    result = calc_antiscia(lons)
    return [a for a in result.aspects
            if {a.planet_a, a.planet_b} == {0, 1}
            and a.aspect_type == "antiscion"
            and a.aspect_angle == expected_angle]


def test_core_antiscion_conjunction():
    sun = 30.0
    anti = _antiscion(sun)  # 150°
    hits = _detect_anti(sun, anti, 0)
    assert hits, "Moon at Sun's antiscion → conjunction expected"
    assert hits[0].orb < 0.001


def test_core_antiscion_sextile():
    sun = 30.0
    anti = _antiscion(sun)
    hits = _detect_anti(sun, (anti + 60.0) % 360.0, 60)
    assert hits, "Moon 60° from antiscion → sextile expected"


def test_core_antiscion_square():
    sun = 30.0
    anti = _antiscion(sun)
    hits = _detect_anti(sun, (anti + 90.0) % 360.0, 90)
    assert hits, "Moon 90° from antiscion → square expected"


def test_core_antiscion_trine():
    sun = 30.0
    anti = _antiscion(sun)
    hits = _detect_anti(sun, (anti + 120.0) % 360.0, 120)
    assert hits, "Moon 120° from antiscion → trine expected"


def test_core_antiscion_opposition():
    sun = 30.0
    anti = _antiscion(sun)
    hits = _detect_anti(sun, (anti + 180.0) % 360.0, 180)
    assert hits, "Moon 180° from antiscion → opposition expected"


# ── Contra-antiscion aspect detection ─────────────────────────────────────────

def _detect_contra(sun_lon, moon_target, expected_angle):
    lons = _all_at(200.0, {0: sun_lon, 1: moon_target % 360.0})
    result = calc_antiscia(lons)
    return [a for a in result.aspects
            if {a.planet_a, a.planet_b} == {0, 1}
            and a.aspect_type == "contra_antiscion"
            and a.aspect_angle == expected_angle]


def test_core_contra_conjunction():
    sun = 45.0
    contra = _contra(sun)  # 315°
    hits = _detect_contra(sun, contra, 0)
    assert hits, "Moon at contra-antiscion → conjunction expected"
    assert hits[0].orb < 0.001


def test_core_contra_sextile():
    sun = 45.0
    contra = _contra(sun)
    hits = _detect_contra(sun, (contra + 60.0) % 360.0, 60)
    assert hits, "Moon 60° from contra-antiscion → sextile expected"


def test_core_contra_square():
    sun = 45.0
    contra = _contra(sun)
    hits = _detect_contra(sun, (contra + 90.0) % 360.0, 90)
    assert hits, "Moon 90° from contra-antiscion → square expected"


def test_core_contra_trine():
    sun = 45.0
    contra = _contra(sun)
    hits = _detect_contra(sun, (contra + 120.0) % 360.0, 120)
    assert hits, "Moon 120° from contra-antiscion → trine expected"


def test_core_contra_opposition():
    sun = 45.0
    contra = _contra(sun)
    hits = _detect_contra(sun, (contra + 180.0) % 360.0, 180)
    assert hits, "Moon 180° from contra-antiscion → opposition expected"


# ── Orb boundaries ─────────────────────────────────────────────────────────────

def test_core_conj_at_boundary_included():
    """Moon at antiscion + exactly 1.0° → conjunction included."""
    sun = 30.0
    anti = _antiscion(sun)
    hits = _detect_anti(sun, (anti + ANTISCIA_ORB) % 360.0, 0)
    assert hits, "Conjunction at exact orb boundary should be included"


def test_core_conj_outside_boundary_excluded():
    """Moon at antiscion + 1.1° → conjunction excluded."""
    sun = 30.0
    anti = _antiscion(sun)
    hits = _detect_anti(sun, (anti + 1.1) % 360.0, 0)
    assert not hits, "Conjunction 1.1° from antiscion should be excluded"


def test_core_non_conj_at_boundary_included():
    """Moon 90° + 0.5° from antiscion → square included."""
    sun = 30.0
    anti = _antiscion(sun)
    hits = _detect_anti(sun, (anti + 90.0 + ANTISCIA_ASPECT_ORB) % 360.0, 90)
    assert hits, "Square at exact non-conj orb boundary should be included"


def test_core_non_conj_outside_boundary_excluded():
    """Moon 90° + 0.6° from antiscion → square excluded."""
    sun = 30.0
    anti = _antiscion(sun)
    hits = _detect_anti(sun, (anti + 90.0 + 0.6) % 360.0, 90)
    assert not hits, "Square 0.6° past 90° should be excluded"


# ── Structural guarantees ──────────────────────────────────────────────────────

def test_core_aspects_sorted_by_orb(rome_result):
    orbs = [a.orb for a in rome_result.aspects]
    assert orbs == sorted(orbs), "Aspects must be sorted tightest first"


def test_core_no_duplicate_pairs(rome_result):
    seen = set()
    for a in rome_result.aspects:
        key = (a.planet_a, a.planet_b, a.aspect_type, a.aspect_angle)
        assert key not in seen, f"Duplicate: {key}"
        seen.add(key)


# ── API tests ──────────────────────────────────────────────────────────────────

def test_api_aspect_angles_valid(api_anti):
    for a in api_anti["aspects"]:
        assert a["aspect_angle"] in VALID_ANGLES


def test_api_aspect_names_valid(api_anti):
    for a in api_anti["aspects"]:
        assert a["aspect_name"] in VALID_NAMES


def test_api_non_conj_aspects_exist(api_anti):
    """Rome 1990 should have at least some non-conjunction antiscia aspects."""
    non_conj = [a for a in api_anti["aspects"] if a["aspect_angle"] != 0]
    assert len(non_conj) > 0, "Expected non-conjunction antiscia aspects in Rome 1990"


def test_api_conjunction_orbs_max_1(api_anti):
    for a in api_anti["aspects"]:
        if a["aspect_angle"] == 0:
            assert a["orb"] <= 1.0


def test_api_non_conj_orbs_max_half(api_anti):
    for a in api_anti["aspects"]:
        if a["aspect_angle"] != 0:
            assert a["orb"] <= 0.5, (
                f"{a['name_a']} {a['aspect_type']} {a['aspect_name']} {a['name_b']} orb={a['orb']}"
            )
