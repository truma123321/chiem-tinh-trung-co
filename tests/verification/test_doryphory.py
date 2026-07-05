"""
Epic 6.5 — Doryphory (Spear-Bearers) tests.

Morning spear-bearer: planet Oriental within 30° of Sun (0° < elong < 30°)
Evening spear-bearer: planet Occidental within 30° of Sun (330° < elong < 360°)
Sun (pid=0) is never a bearer of itself.

Verifies:
  1.  Core: calc_doryphory returns DoryphoryResult with morning/evening lists
  2.  Core: Sun is never in any bearer list
  3.  Core: morning bearers have elongation in (0°, 30°)
  4.  Core: evening bearers have elongation in (330°, 360°)
  5.  Core: sun_distance for morning == elongation
  6.  Core: sun_distance for evening == 360° − elongation
  7.  Core: all sun_distance values < 30°
  8.  Core: all sun_distance values > 0° (exact conjunction excluded)
  9.  Core: bearer_type is "morning" or "evening"
 10.  Core: bearer_count == len(morning) + len(evening)
 11.  Core: has_doryphory == bool(any bearers)
 12.  Core: planet exactly conjunct Sun (elong=0°) is excluded
 13.  Core: planet exactly at 30° elong is excluded (boundary not inclusive)
 14.  Core: planet exactly at 330° elong is excluded (boundary not inclusive)
 15.  Core: custom orb respected (e.g. orb=15° excludes a planet at 20°)
 16.  Core: all 6 non-Sun planets could be bearers if positioned correctly
 17.  Core: planet at 29.9° elong → morning bearer
 18.  Core: planet at 330.1° elong → evening bearer
 19.  API: POST /chart/natal response has doryphory field
 20.  API: doryphory has morning_bearers, evening_bearers, has_doryphory, bearer_count
 21.  API: bearer_type in {"morning", "evening"}
 22.  API: sun_distance < 30° for all bearers
 23.  API: bearer_count == len(morning) + len(evening)
 24.  API: morning_bearers have elongation < 30°
 25.  API: evening_bearers have elongation > 330°
 26.  API: has_doryphory == (bearer_count > 0)
 27.  API: no duplicate planet_id within morning or evening list
 28.  API: planet_name is a valid classical planet name
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.doryphory import calc_doryphory, DEFAULT_ORB

# ── Ephemeris ──────────────────────────────────────────────────────────────────

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

PLANET_NAMES = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}

# ── Helper: build a synthetic planet_lons dict with Sun at 0° ─────────────────

def _lons(sun=0.0, **overrides):
    """Return planet_lons with Sun at `sun` and all others far away by default."""
    base = {pid: (sun + 180.0) % 360.0 for pid in range(7)}  # all opposite Sun
    base[0] = sun
    for pid, lon in overrides.items():
        base[int(pid)] = lon
    return base


# ── Core fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def rome_lons():
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    lons = {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, FLAGS)
        lons[pid] = r[0]
    return lons


@pytest.fixture(scope="module")
def rome_result(rome_lons):
    return calc_doryphory(rome_lons)


# ── Core tests — structure ─────────────────────────────────────────────────────

def test_core_returns_result(rome_result):
    from core.doryphory import DoryphoryResult
    assert isinstance(rome_result, DoryphoryResult)


def test_core_has_morning_evening_lists(rome_result):
    assert isinstance(rome_result.morning_bearers, list)
    assert isinstance(rome_result.evening_bearers, list)


def test_core_sun_never_in_bearers(rome_result):
    all_ids = (
        [b.planet_id for b in rome_result.morning_bearers]
        + [b.planet_id for b in rome_result.evening_bearers]
    )
    assert 0 not in all_ids, "Sun should never be a spear-bearer"


def test_core_morning_elongation_range(rome_result):
    for b in rome_result.morning_bearers:
        assert 0.0 < b.elongation < DEFAULT_ORB, (
            f"{b.planet_name}: morning elongation={b.elongation} not in (0, {DEFAULT_ORB})"
        )


def test_core_evening_elongation_range(rome_result):
    for b in rome_result.evening_bearers:
        assert (360.0 - DEFAULT_ORB) < b.elongation < 360.0, (
            f"{b.planet_name}: evening elongation={b.elongation} not in "
            f"({360-DEFAULT_ORB}, 360)"
        )


def test_core_morning_sun_distance(rome_result):
    for b in rome_result.morning_bearers:
        assert abs(b.sun_distance - b.elongation) < 1e-6, (
            f"{b.planet_name}: morning sun_distance={b.sun_distance} != elongation={b.elongation}"
        )


def test_core_evening_sun_distance(rome_result):
    for b in rome_result.evening_bearers:
        expected = 360.0 - b.elongation
        assert abs(b.sun_distance - expected) < 1e-6, (
            f"{b.planet_name}: evening sun_distance={b.sun_distance} != "
            f"360-elongation={expected}"
        )


def test_core_all_sun_distances_positive(rome_result):
    all_bearers = rome_result.morning_bearers + rome_result.evening_bearers
    for b in all_bearers:
        assert b.sun_distance > 0.0


def test_core_all_sun_distances_under_orb(rome_result):
    all_bearers = rome_result.morning_bearers + rome_result.evening_bearers
    for b in all_bearers:
        assert b.sun_distance < DEFAULT_ORB, (
            f"{b.planet_name}: sun_distance={b.sun_distance} >= orb={DEFAULT_ORB}"
        )


def test_core_bearer_type_values(rome_result):
    for b in rome_result.morning_bearers:
        assert b.bearer_type == "morning"
    for b in rome_result.evening_bearers:
        assert b.bearer_type == "evening"


def test_core_bearer_count(rome_result):
    expected = len(rome_result.morning_bearers) + len(rome_result.evening_bearers)
    assert rome_result.bearer_count == expected


def test_core_has_doryphory_flag(rome_result):
    any_bearers = bool(rome_result.morning_bearers or rome_result.evening_bearers)
    assert rome_result.has_doryphory == any_bearers


# ── Core tests — boundary conditions ──────────────────────────────────────────

def test_core_conjunction_excluded():
    """Planet exactly conjunct Sun (elong=0°) is NOT a bearer."""
    lons = _lons(sun=10.0)
    lons[1] = 10.0  # Moon exactly conjunct Sun → elong=0°
    result = calc_doryphory(lons)
    ids = [b.planet_id for b in result.morning_bearers + result.evening_bearers]
    assert 1 not in ids, "Planet at elong=0° (conjunction) must not be a bearer"


def test_core_30deg_boundary_excluded():
    """Planet exactly at 30° elongation is NOT a bearer (boundary not inclusive)."""
    lons = _lons(sun=0.0)
    lons[1] = 30.0   # Moon at exactly 30° → excluded
    result = calc_doryphory(lons)
    morning_ids = [b.planet_id for b in result.morning_bearers]
    assert 1 not in morning_ids, "Planet at exactly 30° must not be a morning bearer"


def test_core_330deg_boundary_excluded():
    """Planet exactly at 330° elongation is NOT a bearer."""
    lons = _lons(sun=0.0)
    lons[1] = 330.0   # Moon at exactly 330° → excluded
    result = calc_doryphory(lons)
    evening_ids = [b.planet_id for b in result.evening_bearers]
    assert 1 not in evening_ids, "Planet at exactly 330° must not be an evening bearer"


def test_core_29_9_is_morning_bearer():
    """Planet at 29.9° elongation IS a morning bearer."""
    lons = _lons(sun=0.0)
    lons[1] = 29.9
    result = calc_doryphory(lons)
    morning_ids = [b.planet_id for b in result.morning_bearers]
    assert 1 in morning_ids, "Planet at 29.9° should be a morning bearer"


def test_core_330_1_is_evening_bearer():
    """Planet at 330.1° elongation IS an evening bearer."""
    lons = _lons(sun=0.0)
    lons[1] = 330.1
    result = calc_doryphory(lons)
    evening_ids = [b.planet_id for b in result.evening_bearers]
    assert 1 in evening_ids, "Planet at 330.1° should be an evening bearer"


def test_core_custom_orb_respected():
    """With orb=15°, a planet at 20° elongation is excluded."""
    lons = _lons(sun=0.0)
    lons[1] = 20.0   # Moon at 20°
    result_30 = calc_doryphory(lons, orb=30.0)
    result_15 = calc_doryphory(lons, orb=15.0)

    assert any(b.planet_id == 1 for b in result_30.morning_bearers), \
        "Moon at 20° should be included with orb=30°"
    assert not any(b.planet_id == 1 for b in result_15.morning_bearers), \
        "Moon at 20° should be excluded with orb=15°"


def test_core_all_six_planets_can_be_bearers():
    """All 6 non-Sun planets can be bearers simultaneously."""
    sun = 0.0
    lons = {0: sun}
    # Put Moon–Saturn alternately morning (5°,10°,15°) and evening (355°,350°,345°)
    lons[1] = 5.0    # morning
    lons[2] = 10.0   # morning
    lons[3] = 15.0   # morning
    lons[4] = 345.0  # evening
    lons[5] = 350.0  # evening
    lons[6] = 355.0  # evening

    result = calc_doryphory(lons)
    assert len(result.morning_bearers) == 3
    assert len(result.evening_bearers) == 3
    assert result.bearer_count == 6
    assert result.has_doryphory


def test_core_no_bearers_when_all_far():
    """All planets at 180° → no bearers."""
    lons = {pid: 180.0 for pid in range(7)}
    lons[0] = 0.0  # Sun at 0°
    result = calc_doryphory(lons)
    assert not result.has_doryphory
    assert result.bearer_count == 0


# ── API tests ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_resp():
    resp = client.post("/chart/natal", json=NATAL_REQ)
    assert resp.status_code == 200, f"API error: {resp.text}"
    return resp.json()


@pytest.fixture(scope="module")
def api_dory(api_resp):
    return api_resp["doryphory"]


def test_api_doryphory_present(api_resp):
    assert "doryphory" in api_resp


def test_api_top_level_fields(api_dory):
    for f in ["morning_bearers", "evening_bearers", "has_doryphory", "bearer_count"]:
        assert f in api_dory, f"Missing field: {f}"


def test_api_bearer_type_values(api_dory):
    for b in api_dory["morning_bearers"]:
        assert b["bearer_type"] == "morning"
    for b in api_dory["evening_bearers"]:
        assert b["bearer_type"] == "evening"


def test_api_sun_distance_under_30(api_dory):
    all_bearers = api_dory["morning_bearers"] + api_dory["evening_bearers"]
    for b in all_bearers:
        assert b["sun_distance"] < 30.0, (
            f"{b['planet_name']}: sun_distance={b['sun_distance']} >= 30°"
        )


def test_api_bearer_count_consistent(api_dory):
    expected = len(api_dory["morning_bearers"]) + len(api_dory["evening_bearers"])
    assert api_dory["bearer_count"] == expected


def test_api_morning_elongation_range(api_dory):
    for b in api_dory["morning_bearers"]:
        assert 0.0 < b["elongation"] < 30.0


def test_api_evening_elongation_range(api_dory):
    for b in api_dory["evening_bearers"]:
        assert 330.0 < b["elongation"] < 360.0


def test_api_has_doryphory_consistent(api_dory):
    assert api_dory["has_doryphory"] == (api_dory["bearer_count"] > 0)


def test_api_no_duplicate_planet_ids(api_dory):
    morning_ids = [b["planet_id"] for b in api_dory["morning_bearers"]]
    evening_ids = [b["planet_id"] for b in api_dory["evening_bearers"]]
    assert len(morning_ids) == len(set(morning_ids)), "Duplicate morning bearer"
    assert len(evening_ids) == len(set(evening_ids)), "Duplicate evening bearer"


def test_api_planet_names_valid(api_dory):
    all_bearers = api_dory["morning_bearers"] + api_dory["evening_bearers"]
    for b in all_bearers:
        assert b["planet_name"] in PLANET_NAMES, (
            f"Unknown planet: {b['planet_name']}"
        )
        assert b["planet_name"] != "Sun", "Sun cannot be a bearer"
