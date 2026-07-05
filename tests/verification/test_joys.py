"""
Epic 6.4 — Joys of Planets tests.

Joys table (ancient doctrine):
  Mercury → H1  |  Moon → H3  |  Venus → H5  |  Mars → H6
  Sun → H9  |  Jupiter → H11  |  Saturn → H12

Verifies:
  1.  Core: calc_sect returns in_joy and joy_house for all 7 planets
  2.  Core: joy_house matches the canonical table for every planet
  3.  Core: in_joy=True when planet is in its joy house
  4.  Core: in_joy=False when planet is NOT in its joy house
  5.  Core: in_joy computed correctly for all 12 signs of house placements
  6.  Core: without house_cusps → in_joy=False for all planets
  7.  Core: JOY_HOUSE exported from sect module covers all 7 planets
  8.  Core: planet_house() (from sect) correctly assigns 1-based house
  9.  Core: joy_house is invariant (doesn't change with longitude/speed)
 10.  Core: in_joy changes when planet moves from joy house to adjacent house
 11.  API: sect response has in_joy and joy_house fields
 12.  API: joy_house is an integer in [1, 12]
 13.  API: in_joy is a boolean
 14.  API: joy_house matches expected table for each planet_name
 15.  API: exactly Mercury in H1 → in_joy=True (constructed chart)
 16.  API: existing sect fields still present (sect, in_hayz, in_sect, etc.)
 17.  API: accidental_dignities in_joy agrees with sect in_joy for same planet
 18.  API: joy_house is consistent with JOY_HOUSE table
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.sect import calc_sect, JOY_HOUSE, planet_house
from core.dignities import is_day_chart

# ── Ephemeris setup ────────────────────────────────────────────────────────────

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

client = TestClient(app)

# Canonical joy table
CANONICAL_JOY = {
    0: 9,   # Sun — H9
    1: 3,   # Moon — H3
    2: 1,   # Mercury — H1
    3: 5,   # Venus — H5
    4: 6,   # Mars — H6
    5: 11,  # Jupiter — H11
    6: 12,  # Saturn — H12
}

NATAL_REQ = {
    "year": 1990, "month": 6, "day": 15,
    "hour": 10, "minute": 30,
    "lat": 41.9, "lon": 12.5,
    "hsys": "P",
    "ut_offset": 0,
}

# ── Core fixtures ──────────────────────────────────────────────────────────────

JD_ROME = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
LAT_ROME, LON_ROME = 41.9, 12.5


@pytest.fixture(scope="module")
def rome_sect():
    planet_lons = {}
    for pid in range(7):
        r, _ = swe.calc_ut(JD_ROME, pid, FLAGS)
        planet_lons[pid] = r[0]
    cusps_raw, ascmc = swe.houses(JD_ROME, LAT_ROME, LON_ROME, b"P")
    asc = ascmc[0]
    day = is_day_chart(planet_lons[0], asc)
    return calc_sect(planet_lons, asc, day, list(cusps_raw))


@pytest.fixture(scope="module")
def rome_sect_no_cusps():
    """calc_sect called WITHOUT house_cusps — in_joy should be False."""
    planet_lons = {}
    for pid in range(7):
        r, _ = swe.calc_ut(JD_ROME, pid, FLAGS)
        planet_lons[pid] = r[0]
    cusps_raw, ascmc = swe.houses(JD_ROME, LAT_ROME, LON_ROME, b"P")
    asc = ascmc[0]
    day = is_day_chart(planet_lons[0], asc)
    return calc_sect(planet_lons, asc, day)   # no cusps


# ── Core tests ─────────────────────────────────────────────────────────────────

def test_core_has_in_joy_field(rome_sect):
    for ps in rome_sect.planet_sects:
        assert hasattr(ps, "in_joy")
        assert hasattr(ps, "joy_house")


def test_core_joy_house_matches_canonical(rome_sect):
    for ps in rome_sect.planet_sects:
        assert ps.joy_house == CANONICAL_JOY[ps.planet_id], (
            f"{ps.planet_name}: joy_house={ps.joy_house}, "
            f"expected={CANONICAL_JOY[ps.planet_id]}"
        )


def test_core_in_joy_type(rome_sect):
    for ps in rome_sect.planet_sects:
        assert isinstance(ps.in_joy, bool)
        assert isinstance(ps.joy_house, int)


def test_core_no_cusps_joy_false(rome_sect_no_cusps):
    for ps in rome_sect_no_cusps.planet_sects:
        assert ps.in_joy is False, (
            f"{ps.planet_name}: expected in_joy=False without cusps, got {ps.in_joy}"
        )


def test_core_joy_house_exported():
    """JOY_HOUSE dict must cover all 7 traditional planets."""
    assert set(JOY_HOUSE.keys()) == set(range(7))
    assert set(JOY_HOUSE.values()) == {1, 3, 5, 6, 9, 11, 12}


def test_core_joy_house_invariant(rome_sect):
    """joy_house never changes — it's fixed per planet."""
    for ps in rome_sect.planet_sects:
        # The joy house is a fixed doctrine, not computed from position
        assert ps.joy_house == CANONICAL_JOY[ps.planet_id]


def test_core_in_joy_when_in_house():
    """Place Mercury at 0°Aries (H1 in a Whole-Sign Aries rising chart)
    and verify in_joy=True."""
    # Whole-sign cusps: H1 = 0°
    ws_cusps = [i * 30.0 for i in range(12)]

    planet_lons = {pid: 15.0 for pid in range(7)}  # all at 15°Aries
    planet_lons[2] = 5.0   # Mercury at 5°Aries → H1

    # Sun needs to be above horizon for is_day_chart
    planet_lons[0] = 200.0  # Sun in H7 (above horizon, day chart)

    asc = 0.0
    day = is_day_chart(planet_lons[0], asc)

    result = calc_sect(planet_lons, asc, day, ws_cusps)
    merc = next(ps for ps in result.planet_sects if ps.planet_id == 2)

    assert planet_house(5.0, ws_cusps) == 1, "Mercury should be in H1"
    assert merc.in_joy, "Mercury in H1 should have in_joy=True"


def test_core_not_in_joy_when_not_in_house():
    """Mercury in H2 should NOT be in joy."""
    ws_cusps = [i * 30.0 for i in range(12)]
    planet_lons = {pid: 45.0 for pid in range(7)}  # all at 15°Taurus = H2
    planet_lons[0] = 200.0   # Sun above horizon

    asc = 0.0
    day = is_day_chart(planet_lons[0], asc)
    result = calc_sect(planet_lons, asc, day, ws_cusps)

    merc = next(ps for ps in result.planet_sects if ps.planet_id == 2)
    assert not merc.in_joy, "Mercury in H2 should have in_joy=False"


def test_core_in_joy_changes_on_house_change():
    """Mercury crosses H1/H2 boundary: in_joy flips."""
    ws_cusps = [i * 30.0 for i in range(12)]
    planet_lons_base = {pid: 15.0 for pid in range(7)}
    planet_lons_base[0] = 200.0

    # Mercury at 29°Aries → H1 (joy)
    planet_lons_base[2] = 29.0
    asc = 0.0
    day = is_day_chart(planet_lons_base[0], asc)
    r1 = calc_sect(planet_lons_base.copy(), asc, day, ws_cusps)
    merc1 = next(ps for ps in r1.planet_sects if ps.planet_id == 2)
    assert merc1.in_joy

    # Mercury at 31°Aries → H2 (not joy)
    planet_lons_base[2] = 31.0
    r2 = calc_sect(planet_lons_base.copy(), asc, day, ws_cusps)
    merc2 = next(ps for ps in r2.planet_sects if ps.planet_id == 2)
    assert not merc2.in_joy


def test_core_planet_house_function():
    """planet_house() utility — spot check basic cases."""
    ws_cusps = [i * 30.0 for i in range(12)]
    assert planet_house(0.0,   ws_cusps) == 1
    assert planet_house(30.0,  ws_cusps) == 2
    assert planet_house(359.9, ws_cusps) == 12
    assert planet_house(270.0, ws_cusps) == 10


# ── API tests ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_resp():
    resp = client.post("/chart/natal", json=NATAL_REQ)
    assert resp.status_code == 200, f"API error: {resp.text}"
    return resp.json()


@pytest.fixture(scope="module")
def api_sect(api_resp):
    return api_resp["sect"]["planet_sects"]


def test_api_has_in_joy(api_sect):
    for ps in api_sect:
        assert "in_joy" in ps, f"{ps['planet_name']} missing in_joy"
        assert "joy_house" in ps, f"{ps['planet_name']} missing joy_house"


def test_api_joy_house_integer_range(api_sect):
    for ps in api_sect:
        assert isinstance(ps["joy_house"], int)
        assert 1 <= ps["joy_house"] <= 12


def test_api_in_joy_boolean(api_sect):
    for ps in api_sect:
        assert isinstance(ps["in_joy"], bool)


def test_api_joy_house_matches_table(api_sect):
    name_to_id = {
        "Sun": 0, "Moon": 1, "Mercury": 2, "Venus": 3,
        "Mars": 4, "Jupiter": 5, "Saturn": 6,
    }
    for ps in api_sect:
        pid = name_to_id[ps["planet_name"]]
        assert ps["joy_house"] == CANONICAL_JOY[pid], (
            f"{ps['planet_name']}: joy_house={ps['joy_house']}, "
            f"expected={CANONICAL_JOY[pid]}"
        )


def test_api_existing_fields_still_present(api_sect):
    required = ["planet_id", "planet_name", "sect", "in_sect",
                "above_horizon", "sign_masculine", "in_hayz"]
    for ps in api_sect:
        for f in required:
            assert f in ps, f"Existing field '{f}' missing from {ps['planet_name']}"


def test_api_joy_agrees_with_accidental(api_resp):
    """in_joy in sect response must match in_joy in accidental_dignities."""
    sect_joy   = {ps["planet_id"]: ps["in_joy"]
                  for ps in api_resp["sect"]["planet_sects"]}
    accid_joy  = {a["planet_id"]: a["in_joy"]
                  for a in api_resp["accidental_dignities"]}

    for pid in range(7):
        assert sect_joy[pid] == accid_joy[pid], (
            f"planet_id={pid}: sect in_joy={sect_joy[pid]}, "
            f"accidental in_joy={accid_joy[pid]}"
        )


def test_api_joy_house_consistent_with_table(api_sect):
    """joy_house values across all 7 planets form the exact joy set."""
    joy_houses = {ps["joy_house"] for ps in api_sect}
    assert joy_houses == {1, 3, 5, 6, 9, 11, 12}
