"""
Epic 6.6 — Fixed Stars: All 5 Major Aspects tests.

Aspects checked: Conjunction (0°), Sextile (60°), Square (90°),
                 Trine (120°), Opposition (180°).
Orbs: Conjunction 1°, all others 0.5°.

Verifies:
  1.  Core: calc_fixed_stars returns FixedStarsResult with aspects list
  2.  Core: aspect_angle values are in {0, 60, 90, 120, 180}
  3.  Core: aspect_name matches angle (Conjunction/Sextile/Square/Trine/Opposition)
  4.  Core: conjunction orbs ≤ 1.0°
  5.  Core: non-conjunction orbs ≤ 0.5°
  6.  Core: all orbs ≥ 0°
  7.  Core: planet_id in range 0..6
  8.  Core: star_lon in [0°, 360°)
  9.  Core: aspects sorted by orb (tightest first)
 10.  Core: planet exactly at star_lon → conjunction with orb=0
 11.  Core: planet at star_lon + 60° → sextile detected
 12.  Core: planet at star_lon + 90° → square detected
 13.  Core: planet at star_lon + 120° → trine detected
 14.  Core: planet at star_lon + 180° → opposition detected
 15.  Core: planet at star_lon + 0.5° → conjunction within orb (1°)
 16.  Core: planet at star_lon + 1.1° → conjunction outside orb (excluded)
 17.  Core: planet at star_lon + 60.4° → sextile within orb (0.5°)
 18.  Core: planet at star_lon + 60.6° → sextile outside orb (excluded)
 19.  Core: ≥90 stars loaded in star_positions (catalog has 114 entries)
 20.  Core: STAR_ASPECTS dict covers exactly 5 aspects
 21.  API: fixed_stars.aspects list present (not conjunctions)
 22.  API: each aspect has aspect_angle and aspect_name
 23.  API: conjunction orbs ≤ 1.0°
 24.  API: non-conjunction orbs ≤ 0.5°
 25.  API: aspect_angle in {0, 60, 90, 120, 180}
 26.  API: aspects sorted by orb
 27.  API: star_positions has ≥90 entries
 28.  API: planet_ids valid (0–6)
 29.  API: non-conjunction aspects present (at least some in Rome 1990)
 30.  API: "conjunctions" key NO LONGER in fixed_stars response
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.fixed_stars import (
    calc_fixed_stars, FIXED_STARS, STAR_ASPECTS,
    CONJUNCTION_ORB, ASPECT_ORB,
)

# ── Ephemeris setup ────────────────────────────────────────────────────────────

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

client = TestClient(app)

NATAL_REQ = {
    "year": 1990, "month": 6, "day": 15,
    "hour": 10, "minute": 30,
    "lat": 41.9, "lon": 12.5,
    "hsys": "P",
    "ut_offset": 0,
}

JD_ROME = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)

VALID_ANGLES = {0, 60, 90, 120, 180}
VALID_NAMES  = {"Conjunction", "Sextile", "Square", "Trine", "Opposition"}

# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_lons(overrides: dict) -> dict:
    """Build planet_lons with all 7 planets at 180° then apply overrides."""
    lons = {pid: 180.0 for pid in range(7)}
    lons.update(overrides)
    return lons


def _get_spica_lon(jd: float) -> float:
    """Return precessed longitude of Spica at given JD."""
    coords, _, _ = swe.fixstar_ut("Spica,alVir", jd, swe.FLG_SWIEPH)
    return coords[0]


# ── Core fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def rome_result():
    lons = {}
    for pid in range(7):
        r, _ = swe.calc_ut(JD_ROME, pid, FLAGS)
        lons[pid] = r[0]
    return calc_fixed_stars(lons, JD_ROME)


# ── Core tests — structure ─────────────────────────────────────────────────────

def test_core_has_aspects_field(rome_result):
    from core.fixed_stars import FixedStarsResult
    assert isinstance(rome_result, FixedStarsResult)
    assert hasattr(rome_result, "aspects")


def test_core_aspect_angles_valid(rome_result):
    for a in rome_result.aspects:
        assert a.aspect_angle in VALID_ANGLES, (
            f"{a.star_name}–{a.planet_name}: invalid angle {a.aspect_angle}"
        )


def test_core_aspect_names_valid(rome_result):
    for a in rome_result.aspects:
        assert a.aspect_name in VALID_NAMES


def test_core_name_matches_angle(rome_result):
    name_map = {0: "Conjunction", 60: "Sextile", 90: "Square",
                120: "Trine", 180: "Opposition"}
    for a in rome_result.aspects:
        assert a.aspect_name == name_map[a.aspect_angle]


def test_core_conjunction_orb_max_1(rome_result):
    for a in rome_result.aspects:
        if a.aspect_angle == 0:
            assert a.orb <= CONJUNCTION_ORB, (
                f"{a.star_name} conjunction orb={a.orb} > {CONJUNCTION_ORB}"
            )


def test_core_non_conj_orb_max_half(rome_result):
    for a in rome_result.aspects:
        if a.aspect_angle != 0:
            assert a.orb <= ASPECT_ORB, (
                f"{a.star_name} {a.aspect_name} orb={a.orb} > {ASPECT_ORB}"
            )


def test_core_orbs_non_negative(rome_result):
    for a in rome_result.aspects:
        assert a.orb >= 0.0


def test_core_planet_ids_valid(rome_result):
    for a in rome_result.aspects:
        assert 0 <= a.planet_id <= 6


def test_core_star_lons_valid(rome_result):
    for a in rome_result.aspects:
        assert 0.0 <= a.star_lon < 360.0


def test_core_aspects_sorted_by_orb(rome_result):
    orbs = [a.orb for a in rome_result.aspects]
    assert orbs == sorted(orbs), "Aspects should be sorted tightest-first"


def test_core_star_positions_count(rome_result):
    # Catalog has 114 entries; allow some SE name misses (≥ 90 must load)
    assert len(rome_result.star_positions) >= 90


def test_core_star_aspects_dict_five_entries():
    assert len(STAR_ASPECTS) == 5
    assert set(STAR_ASPECTS.keys()) == VALID_ANGLES


# ── Core tests — aspect detection by angle ────────────────────────────────────

def _find_aspect(jd, planet_lon, angle, expected_angle):
    """Place Moon (pid=1) at planet_lon and check for expected aspect."""
    lons = _make_lons({1: planet_lon % 360.0})
    result = calc_fixed_stars(lons, jd)
    return any(
        a.planet_id == 1 and a.aspect_angle == expected_angle
        for a in result.aspects
    )


def test_core_conjunction_detected():
    spica = _get_spica_lon(JD_ROME)
    lons = _make_lons({1: spica})   # Moon exactly on Spica
    result = calc_fixed_stars(lons, JD_ROME)
    conj = [a for a in result.aspects
            if a.planet_id == 1 and a.aspect_angle == 0
            and a.star_name == "Spica"]
    assert conj, "Moon exactly on Spica should give conjunction"
    assert conj[0].orb < 0.001


def test_core_sextile_detected():
    spica = _get_spica_lon(JD_ROME)
    target = (spica + 60.0) % 360.0
    lons = _make_lons({1: target})
    result = calc_fixed_stars(lons, JD_ROME)
    found = any(a.planet_id == 1 and a.aspect_angle == 60
                and a.star_name == "Spica" for a in result.aspects)
    assert found, "Moon 60° from Spica should give sextile"


def test_core_square_detected():
    spica = _get_spica_lon(JD_ROME)
    target = (spica + 90.0) % 360.0
    lons = _make_lons({1: target})
    result = calc_fixed_stars(lons, JD_ROME)
    found = any(a.planet_id == 1 and a.aspect_angle == 90
                and a.star_name == "Spica" for a in result.aspects)
    assert found, "Moon 90° from Spica should give square"


def test_core_trine_detected():
    spica = _get_spica_lon(JD_ROME)
    target = (spica + 120.0) % 360.0
    lons = _make_lons({1: target})
    result = calc_fixed_stars(lons, JD_ROME)
    found = any(a.planet_id == 1 and a.aspect_angle == 120
                and a.star_name == "Spica" for a in result.aspects)
    assert found, "Moon 120° from Spica should give trine"


def test_core_opposition_detected():
    spica = _get_spica_lon(JD_ROME)
    target = (spica + 180.0) % 360.0
    lons = _make_lons({1: target})
    result = calc_fixed_stars(lons, JD_ROME)
    found = any(a.planet_id == 1 and a.aspect_angle == 180
                and a.star_name == "Spica" for a in result.aspects)
    assert found, "Moon 180° from Spica should give opposition"


def test_core_conjunction_within_orb():
    """Moon at Spica +0.5° → still within conjunction orb (1°)."""
    spica = _get_spica_lon(JD_ROME)
    lons = _make_lons({1: (spica + 0.5) % 360.0})
    result = calc_fixed_stars(lons, JD_ROME)
    found = any(a.planet_id == 1 and a.aspect_angle == 0
                and a.star_name == "Spica" for a in result.aspects)
    assert found


def test_core_conjunction_outside_orb():
    """Moon at Spica +1.1° → outside conjunction orb (excluded)."""
    spica = _get_spica_lon(JD_ROME)
    lons = _make_lons({1: (spica + 1.1) % 360.0})
    result = calc_fixed_stars(lons, JD_ROME)
    found = any(a.planet_id == 1 and a.aspect_angle == 0
                and a.star_name == "Spica" for a in result.aspects)
    assert not found


def test_core_sextile_within_orb():
    """Moon at Spica +60.4° → within sextile orb (0.5°)."""
    spica = _get_spica_lon(JD_ROME)
    lons = _make_lons({1: (spica + 60.4) % 360.0})
    result = calc_fixed_stars(lons, JD_ROME)
    found = any(a.planet_id == 1 and a.aspect_angle == 60
                and a.star_name == "Spica" for a in result.aspects)
    assert found


def test_core_sextile_outside_orb():
    """Moon at Spica +60.6° → outside sextile orb (excluded)."""
    spica = _get_spica_lon(JD_ROME)
    lons = _make_lons({1: (spica + 60.6) % 360.0})
    result = calc_fixed_stars(lons, JD_ROME)
    found = any(a.planet_id == 1 and a.aspect_angle == 60
                and a.star_name == "Spica" for a in result.aspects)
    assert not found


# ── API tests ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_resp():
    resp = client.post("/chart/natal", json=NATAL_REQ)
    assert resp.status_code == 200, f"API error: {resp.text}"
    return resp.json()


@pytest.fixture(scope="module")
def api_fs(api_resp):
    return api_resp["fixed_stars"]


def test_api_aspects_field_present(api_fs):
    assert "aspects" in api_fs


def test_api_conjunctions_key_gone(api_fs):
    """The old 'conjunctions' field must no longer exist."""
    assert "conjunctions" not in api_fs


def test_api_aspects_have_angle_and_name(api_fs):
    for a in api_fs["aspects"]:
        assert "aspect_angle" in a
        assert "aspect_name" in a


def test_api_conjunction_orbs_max_1(api_fs):
    for a in api_fs["aspects"]:
        if a["aspect_angle"] == 0:
            assert a["orb"] <= 1.0


def test_api_non_conj_orbs_max_half(api_fs):
    for a in api_fs["aspects"]:
        if a["aspect_angle"] != 0:
            assert a["orb"] <= 0.5, (
                f"{a['star_name']} {a['aspect_name']} orb={a['orb']}"
            )


def test_api_aspect_angles_valid(api_fs):
    for a in api_fs["aspects"]:
        assert a["aspect_angle"] in VALID_ANGLES


def test_api_aspects_sorted(api_fs):
    orbs = [a["orb"] for a in api_fs["aspects"]]
    assert orbs == sorted(orbs)


def test_api_star_positions_count(api_fs):
    # Catalog has 114 entries; allow some SE name misses (≥ 90 must load)
    assert len(api_fs["star_positions"]) >= 90


def test_api_planet_ids_valid(api_fs):
    for a in api_fs["aspects"]:
        assert 0 <= a["planet_id"] <= 6


def test_api_non_conj_aspects_exist(api_fs):
    """Rome 1990 should have at least some sextile/square/trine/opposition aspects."""
    non_conj = [a for a in api_fs["aspects"] if a["aspect_angle"] != 0]
    assert len(non_conj) > 0, (
        "Expected at least one non-conjunction aspect in Rome 1990 chart"
    )
