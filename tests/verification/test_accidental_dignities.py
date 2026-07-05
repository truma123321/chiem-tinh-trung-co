"""
Epic 6.2 — Accidental Dignities Full Scoring tests.

Verifies:
  1.  Core: calc_accidental_dignities returns 7 results (Sun-Saturn)
  2.  Core: planet_id order matches 0..6
  3.  Core: planet_name strings match known names
  4.  Core: house is 1-12 for every planet
  5.  Core: exactly one of is_angular/is_succedent/is_cadent is True
  6.  Core: fast_in_motion and slow_in_motion are mutually exclusive
  7.  Core: direct and retrograde are mutually exclusive and exhaustive
  8.  Core: Sun has increasing_light=False, decreasing_light=False
  9.  Core: non-Sun planets have exactly one of increasing/decreasing light True
 10.  Core: Sun has cazimi=combust=under_beams=free_from_beams=False
 11.  Core: non-Sun planets have exactly one solar proximity flag True
 12.  Core: house_score is 5 for angular, 3 for succedent, 1 for cadent
 13.  Core: motion_score is +2/−2/0 matching fast/slow flags
 14.  Core: direction_score is −5 for retrograde, +4 for direct
 15.  Core: light_score is +2/−2 matching increasing/decreasing (0 for Sun)
 16.  Core: solar_score is +5/−5/−4/+5 matching cazimi/combust/beams/free
 17.  Core: hayz_score is +6 when in_hayz, else 0
 18.  Core: joy_score is +1 when in_joy, else 0
 19.  Core: accidental_score equals sum of all component scores
 20.  Core: _planet_house assigns correct houses in a simple Whole-Sign chart
 21.  Core: in_joy correct — Mercury H1, Moon H3, Venus H5, Mars H6, Sun H9,
            Jupiter H11, Saturn H12
 22.  Core: retrograde planet has negative speed (consistency with planet_speeds)
 23.  API: POST /chart/natal returns accidental_dignities list
 24.  API: accidental_dignities has 7 elements
 25.  API: each element has essential_score and total_dignity_score fields
 26.  API: total_dignity_score == essential_score + accidental_score
 27.  API: house values are integers in [1, 12]
 28.  API: all boolean fields are actual booleans
 29.  API: score fields are integers
 30.  API: day chart Sun is direct (speed > 0)
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.accidental_dignities import calc_accidental_dignities
from core.sect import planet_house
from core.conditions import calc_conditions
from core.sect import calc_sect
from core.dignities import is_day_chart

# ── Ephemeris setup ────────────────────────────────────────────────────────────

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

# ── Reference chart: Rome 1990-06-15 10:30 UT ─────────────────────────────────

JD_ROME = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
LAT_ROME, LON_ROME = 41.9, 12.5

client = TestClient(app)

NATAL_REQ = {
    "year": 1990, "month": 6, "day": 15,
    "hour": 10, "minute": 30,
    "lat": LAT_ROME, "lon": LON_ROME,
    "hsys": "P",   # Placidus
    "ut_offset": 0,
}


# ── Core fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def rome_data():
    """Compute all inputs for Rome 1990 chart."""
    planet_lons   = {}
    planet_speeds = {}
    for pid in range(7):
        r, _ = swe.calc_ut(JD_ROME, pid, FLAGS)
        planet_lons[pid]   = r[0]
        planet_speeds[pid] = r[3]

    cusps_raw, ascmc = swe.houses(JD_ROME, LAT_ROME, LON_ROME, b"P")
    asc = ascmc[0]
    day = is_day_chart(planet_lons[0], asc)

    cond_result = calc_conditions(planet_lons, planet_speeds)
    sect_result = calc_sect(planet_lons, asc, day)

    results = calc_accidental_dignities(
        planet_lons, planet_speeds, list(cusps_raw), cond_result, sect_result
    )
    return results, planet_lons, planet_speeds, list(cusps_raw)


@pytest.fixture(scope="module")
def acc_results(rome_data):
    return rome_data[0]


# ── API fixture ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_resp():
    resp = client.post("/chart/natal", json=NATAL_REQ)
    assert resp.status_code == 200, f"API error: {resp.text}"
    return resp.json()


@pytest.fixture(scope="module")
def api_acc(api_resp):
    return api_resp["accidental_dignities"]


# ── Core tests ─────────────────────────────────────────────────────────────────

def test_core_returns_seven(acc_results):
    assert len(acc_results) == 7


def test_core_planet_id_order(acc_results):
    ids = [a.planet_id for a in acc_results]
    assert ids == list(range(7))


def test_core_planet_names(acc_results):
    names = [a.planet_name for a in acc_results]
    assert names == ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]


def test_core_house_range(acc_results):
    for a in acc_results:
        assert 1 <= a.house <= 12, f"{a.planet_name} house={a.house}"


def test_core_house_type_exclusive(acc_results):
    for a in acc_results:
        flags = [a.is_angular, a.is_succedent, a.is_cadent]
        assert sum(flags) == 1, (
            f"{a.planet_name} house={a.house}: "
            f"angular={a.is_angular} succedent={a.is_succedent} cadent={a.is_cadent}"
        )


def test_core_motion_exclusive(acc_results):
    for a in acc_results:
        assert not (a.fast_in_motion and a.slow_in_motion), (
            f"{a.planet_name}: both fast and slow cannot be True"
        )


def test_core_direction_exclusive_exhaustive(acc_results):
    for a in acc_results:
        assert a.direct != a.retrograde, (
            f"{a.planet_name}: direct and retrograde must differ"
        )


def test_core_sun_no_light_phase(acc_results):
    sun = next(a for a in acc_results if a.planet_id == 0)
    assert not sun.increasing_light
    assert not sun.decreasing_light


def test_core_non_sun_light_exclusive(acc_results):
    for a in acc_results:
        if a.planet_id == 0:
            continue
        flags = [a.increasing_light, a.decreasing_light]
        assert sum(flags) == 1, (
            f"{a.planet_name}: exactly one light phase must be True"
        )


def test_core_sun_no_solar_proximity(acc_results):
    sun = next(a for a in acc_results if a.planet_id == 0)
    assert not sun.cazimi
    assert not sun.combust
    assert not sun.under_beams
    assert not sun.free_from_beams


def test_core_non_sun_solar_proximity_exclusive(acc_results):
    for a in acc_results:
        if a.planet_id == 0:
            continue
        flags = [a.cazimi, a.combust, a.under_beams, a.free_from_beams]
        assert sum(flags) == 1, (
            f"{a.planet_name}: exactly one solar proximity flag must be True"
        )


def test_core_house_score_values(acc_results):
    for a in acc_results:
        if a.is_angular:
            assert a.house_score == 5
        elif a.is_succedent:
            assert a.house_score == 3
        else:
            assert a.house_score == 1


def test_core_motion_score_values(acc_results):
    for a in acc_results:
        if a.fast_in_motion:
            assert a.motion_score == 2
        elif a.slow_in_motion:
            assert a.motion_score == -2
        else:
            assert a.motion_score == 0


def test_core_direction_score_values(acc_results):
    for a in acc_results:
        assert a.direction_score == (-5 if a.retrograde else 4)


def test_core_light_score_values(acc_results):
    for a in acc_results:
        if a.planet_id == 0:
            assert a.light_score == 0
        elif a.increasing_light:
            assert a.light_score == 2
        else:
            assert a.light_score == -2


def test_core_solar_score_values(acc_results):
    for a in acc_results:
        if a.planet_id == 0:
            assert a.solar_score == 0
        elif a.cazimi:
            assert a.solar_score == 5
        elif a.combust:
            assert a.solar_score == -5
        elif a.under_beams:
            assert a.solar_score == -4
        else:
            assert a.solar_score == 5  # free from beams


def test_core_hayz_score_values(acc_results):
    for a in acc_results:
        assert a.hayz_score == (6 if a.in_hayz else 0)


def test_core_joy_score_values(acc_results):
    for a in acc_results:
        assert a.joy_score == (1 if a.in_joy else 0)


def test_core_accidental_score_is_sum(acc_results):
    for a in acc_results:
        expected = (
            a.house_score + a.motion_score + a.direction_score + a.light_score
            + a.solar_score + a.hayz_score + a.joy_score
        )
        assert a.accidental_score == expected, (
            f"{a.planet_name}: accidental_score={a.accidental_score} != sum={expected}"
        )


def test_core_planet_house_whole_sign():
    """In a simplified Whole-Sign approximation, each sign = one house.
    Use manually constructed cusps: [0, 30, 60, ... 330] (Aries rising).
    """
    from core.sect import planet_house as _planet_house
    aries_cusps = [i * 30.0 for i in range(12)]

    assert _planet_house(0.0,   aries_cusps) == 1   # 0°Aries → H1
    assert _planet_house(29.9,  aries_cusps) == 1   # 29°Aries → H1
    assert _planet_house(30.0,  aries_cusps) == 2   # 0°Taurus → H2
    assert _planet_house(359.9, aries_cusps) == 12  # 29°Pisces → H12
    assert _planet_house(270.0, aries_cusps) == 10  # 0°Cap → H10 (MC)


def test_core_planet_house_boundary_wrap():
    """House 12 wraps through 0° when Capricorn/Aquarius rising."""
    from core.sect import planet_house as _planet_house
    # Offset cusps so H1 starts at 300° (Capricorn rising)
    # H1=300-330, H2=330-0, H3=0-30, ..., H12=270-300
    cap_cusps = [(300 + i * 30) % 360 for i in range(12)]

    assert _planet_house(300.0, cap_cusps) == 1   # start of H1
    assert _planet_house(355.0, cap_cusps) == 2   # 25° into H2 (330°-360°)
    assert _planet_house(5.0,   cap_cusps) == 3   # past wrap → H3 starts at 0°
    assert _planet_house(290.0, cap_cusps) == 12  # H12: 270°-300°


def test_core_joy_assignment(acc_results, rome_data):
    """Planets in their joy house must have in_joy=True."""
    _, _, _, cusps = rome_data
    JOY_HOUSE = {2: 1, 1: 3, 3: 5, 4: 6, 0: 9, 5: 11, 6: 12}

    for a in acc_results:
        expected_joy = a.house == JOY_HOUSE.get(a.planet_id, -1)
        assert a.in_joy == expected_joy, (
            f"{a.planet_name} in house {a.house}: in_joy={a.in_joy}, "
            f"expected joy house={JOY_HOUSE.get(a.planet_id)}"
        )


def test_core_retrograde_speed_consistency(rome_data):
    """Retrograde flag must agree with the actual speed sign."""
    acc_results, _, planet_speeds, _ = rome_data
    for a in acc_results:
        spd = planet_speeds[a.planet_id]
        assert a.retrograde == (spd < 0), (
            f"{a.planet_name}: retrograde={a.retrograde} but speed={spd:.4f}"
        )


# ── API tests ──────────────────────────────────────────────────────────────────

def test_api_has_accidental_dignities(api_resp):
    assert "accidental_dignities" in api_resp


def test_api_seven_planets(api_acc):
    assert len(api_acc) == 7


def test_api_essential_score_present(api_acc):
    for a in api_acc:
        assert "essential_score" in a
        assert "total_dignity_score" in a


def test_api_total_dignity_score_formula(api_acc):
    for a in api_acc:
        assert a["total_dignity_score"] == a["essential_score"] + a["accidental_score"], (
            f"{a['planet_name']}: total={a['total_dignity_score']} != "
            f"ess={a['essential_score']} + acc={a['accidental_score']}"
        )


def test_api_house_range(api_acc):
    for a in api_acc:
        assert 1 <= a["house"] <= 12, f"{a['planet_name']} house={a['house']}"


def test_api_boolean_fields(api_acc):
    bool_fields = [
        "is_angular", "is_succedent", "is_cadent",
        "fast_in_motion", "slow_in_motion",
        "direct", "retrograde",
        "increasing_light", "decreasing_light",
        "cazimi", "free_from_beams", "under_beams", "combust",
        "in_hayz", "in_joy",
    ]
    for a in api_acc:
        for f in bool_fields:
            assert isinstance(a[f], bool), (
                f"{a['planet_name']}.{f} is {type(a[f])}, expected bool"
            )


def test_api_score_fields_are_int(api_acc):
    int_fields = [
        "house_score", "motion_score", "direction_score",
        "light_score", "solar_score", "hayz_score", "joy_score",
        "accidental_score", "essential_score", "total_dignity_score",
    ]
    for a in api_acc:
        for f in int_fields:
            assert isinstance(a[f], int), (
                f"{a['planet_name']}.{f} = {a[f]} is not int"
            )


def test_api_sun_is_direct(api_acc):
    sun = next(a for a in api_acc if a["planet_name"] == "Sun")
    assert sun["direct"]
    assert not sun["retrograde"]


def test_api_house_type_exclusive(api_acc):
    for a in api_acc:
        flags = [a["is_angular"], a["is_succedent"], a["is_cadent"]]
        assert sum(flags) == 1, (
            f"{a['planet_name']}: exactly one house-type flag must be True"
        )


def test_api_direction_retrograde_exclusive(api_acc):
    for a in api_acc:
        assert a["direct"] != a["retrograde"]


def test_api_accidental_score_within_range(api_acc):
    """Theoretical min/max: [-5-2-5-2-5+0+0] = -19  …  [+5+2+4+2+5+6+1] = +25"""
    for a in api_acc:
        assert -19 <= a["accidental_score"] <= 25, (
            f"{a['planet_name']} accidental_score={a['accidental_score']} out of range"
        )
