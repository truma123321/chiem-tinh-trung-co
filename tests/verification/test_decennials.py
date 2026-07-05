"""
Epic 7.2 — Decennials (Paulus Alexandrinus) tests.

129-year Chaldean time-lord system.
  Starting planet = lord of birth planetary hour (seasonal hours).
  7 major periods in Chaldean sequence from starting planet.
  7 sub-periods within each major period, same Chaldean sequence.
  Sub-period duration = (major_years × sub_years) / 129 years.

Verifies:
  1.  Core: result is DecennialsResult
  2.  Core: birth_hour_lord_id is one of 7 classical planet IDs
  3.  Core: birth_hour_lord_name is a non-empty string
  4.  Core: periods list has exactly 7 entries
  5.  Core: all major planets are distinct (no duplicates)
  6.  Core: major planet IDs are a permutation of [0..6] (all 7 planets)
  7.  Core: each major duration_years matches MINOR_YEARS
  8.  Core: sum of major duration_years == 129
  9.  Core: each major period has exactly 7 sub-periods
 10.  Core: sub-planet IDs are a permutation of [0..6]
 11.  Core: sub-period duration_years formula: (major × sub) / 129
 12.  Core: sum of sub-period durations == major_years (within 0.001)
 13.  Core: major periods are contiguous (end == next start)
 14.  Core: sub-periods are contiguous within major
 15.  Core: exactly one major is_current == True
 16.  Core: exactly one sub is_current == True within current major
 17.  Core: current_period is not None
 18.  Core: current_sub is not None
 19.  Core: current_period matches flagged major period
 20.  Core: current_sub matches flagged sub in current major
 21.  Core: major sequence starts at birth_hour_lord_id
 22.  Core: major sequence follows Chaldean order
 23.  Core: cycle_start_jd <= birth_jd + 129*365.25
 24.  Core: start dates are valid calendar dates (year > 0)
 25.  Core: sub start/end DatePoints have jd > 0
 26.  API endpoint: POST /chart/decennials 200 OK
 27.  API endpoint: response has 7 periods
 28.  API endpoint: current_period is not None
 29.  API endpoint: current_sub is not None
 30.  API endpoint: current_period.planet_name is a known planet
 31.  Natal: decennials field present in natal response
 32.  Natal: natal decennials.current_period not None
 33.  Natal: natal decennials.birth_hour_lord_name non-empty
 34.  Natal: natal decennials.periods count == 7
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.decennials import (
    calc_decennials, MINOR_YEARS, TOTAL_YEARS, DecennialsResult,
)

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

client = TestClient(app)

BIRTH_REQ = {
    "year": 1990, "month": 6, "day": 15,
    "hour": 10.0, "minute": 30,
    "lat": 41.9, "lon": 12.5,
    "ut_offset": 0.0,
}

JD = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
LAT, LON = 41.9, 12.5

_CHALDEAN = [6, 5, 4, 0, 3, 2, 1]  # Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon
_PLANET_NAMES = {0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
                 4: "Mars", 5: "Jupiter", 6: "Saturn"}


@pytest.fixture(scope="module")
def result():
    return calc_decennials(JD, LAT, LON)


@pytest.fixture(scope="module")
def api_resp():
    r = client.post("/chart/decennials", json=BIRTH_REQ)
    assert r.status_code == 200
    return r.json()


@pytest.fixture(scope="module")
def api_natal():
    natal_req = {**BIRTH_REQ, "hour": 10, "minute": 30, "hsys": "P"}
    r = client.post("/chart/natal", json=natal_req)
    assert r.status_code == 200
    return r.json()


# ── Core tests ─────────────────────────────────────────────────────────────────

def test_result_type(result):
    assert isinstance(result, DecennialsResult)


def test_hour_lord_is_classical_planet(result):
    assert result.birth_hour_lord_id in range(7)


def test_hour_lord_name_nonempty(result):
    assert isinstance(result.birth_hour_lord_name, str)
    assert len(result.birth_hour_lord_name) > 0


def test_seven_major_periods(result):
    assert len(result.periods) == 7


def test_major_planets_distinct(result):
    ids = [p.planet_id for p in result.periods]
    assert len(ids) == len(set(ids))


def test_major_planets_all_seven(result):
    ids = sorted(p.planet_id for p in result.periods)
    assert ids == list(range(7))


def test_major_duration_matches_minor_years(result):
    for p in result.periods:
        assert p.duration_years == MINOR_YEARS[p.planet_id], (
            f"{p.planet_name}: got {p.duration_years}, expected {MINOR_YEARS[p.planet_id]}"
        )


def test_major_durations_sum_to_129(result):
    total = sum(p.duration_years for p in result.periods)
    assert total == TOTAL_YEARS


def test_each_major_has_seven_subs(result):
    for p in result.periods:
        assert len(p.sub_periods) == 7, f"{p.planet_name} has {len(p.sub_periods)} subs"


def test_sub_planets_all_seven(result):
    for p in result.periods:
        ids = sorted(s.planet_id for s in p.sub_periods)
        assert ids == list(range(7)), f"{p.planet_name} subs: {ids}"


def test_sub_duration_formula(result):
    for p in result.periods:
        for s in p.sub_periods:
            expected = (p.duration_years * MINOR_YEARS[s.planet_id]) / TOTAL_YEARS
            assert abs(s.duration_years - expected) < 0.001, (
                f"{p.planet_name}/{s.planet_name}: got {s.duration_years}, expected {expected:.4f}"
            )


def test_sub_durations_sum_to_major(result):
    for p in result.periods:
        total_sub = sum(s.duration_years for s in p.sub_periods)
        assert abs(total_sub - p.duration_years) < 0.001, (
            f"{p.planet_name}: sub sum {total_sub:.4f} != {p.duration_years}"
        )


def test_major_periods_contiguous(result):
    for i in range(len(result.periods) - 1):
        end_jd = result.periods[i].end.jd
        start_jd = result.periods[i + 1].start.jd
        assert abs(end_jd - start_jd) < 0.01, (
            f"Period {i} end {end_jd} != period {i+1} start {start_jd}"
        )


def test_sub_periods_contiguous(result):
    for p in result.periods:
        for i in range(len(p.sub_periods) - 1):
            end_jd = p.sub_periods[i].end.jd
            start_jd = p.sub_periods[i + 1].start.jd
            assert abs(end_jd - start_jd) < 0.01, (
                f"{p.planet_name} sub {i} end {end_jd} != sub {i+1} start {start_jd}"
            )


def test_exactly_one_current_major(result):
    currents = [p for p in result.periods if p.is_current]
    assert len(currents) == 1


def test_exactly_one_current_sub(result):
    cur_period = next(p for p in result.periods if p.is_current)
    currents = [s for s in cur_period.sub_periods if s.is_current]
    assert len(currents) == 1


def test_current_period_not_none(result):
    assert result.current_period is not None


def test_current_sub_not_none(result):
    assert result.current_sub is not None


def test_current_period_matches_flag(result):
    flagged = next(p for p in result.periods if p.is_current)
    assert result.current_period.planet_id == flagged.planet_id


def test_current_sub_matches_flag(result):
    cur_period = next(p for p in result.periods if p.is_current)
    flagged_sub = next(s for s in cur_period.sub_periods if s.is_current)
    assert result.current_sub.planet_id == flagged_sub.planet_id


def test_major_sequence_starts_at_hour_lord(result):
    assert result.periods[0].planet_id == result.birth_hour_lord_id


def test_major_sequence_follows_chaldean(result):
    start_idx = _CHALDEAN.index(result.birth_hour_lord_id)
    for i, p in enumerate(result.periods):
        expected = _CHALDEAN[(start_idx + i) % 7]
        assert p.planet_id == expected, (
            f"Period {i}: got {p.planet_name}, expected {_PLANET_NAMES[expected]}"
        )


def test_cycle_start_within_bounds(result):
    # cycle_start should be between birth_jd and birth_jd + 129 years
    assert result.cycle_start_jd >= result.birth_jd
    assert result.cycle_start_jd < result.birth_jd + TOTAL_YEARS * 365.25


def test_start_dates_valid(result):
    for p in result.periods:
        assert p.start.year > 0
        assert 1 <= p.start.month <= 12
        assert 1 <= p.start.day <= 31


def test_sub_jd_positive(result):
    for p in result.periods:
        for s in p.sub_periods:
            assert s.start.jd > 0
            assert s.end.jd > s.start.jd


# ── API endpoint tests ─────────────────────────────────────────────────────────

def test_api_200(api_resp):
    assert "periods" in api_resp


def test_api_seven_periods(api_resp):
    assert len(api_resp["periods"]) == 7


def test_api_current_period_present(api_resp):
    assert api_resp["current_period"] is not None


def test_api_current_sub_present(api_resp):
    assert api_resp["current_sub"] is not None


def test_api_current_period_planet_known(api_resp):
    name = api_resp["current_period"]["planet_name"]
    assert name in _PLANET_NAMES.values()


# ── Natal integration tests ────────────────────────────────────────────────────

def test_natal_has_decennials(api_natal):
    assert "decennials" in api_natal
    assert api_natal["decennials"] is not None


def test_natal_decennials_current_period(api_natal):
    assert api_natal["decennials"]["current_period"] is not None


def test_natal_decennials_hour_lord_name(api_natal):
    name = api_natal["decennials"]["birth_hour_lord_name"]
    assert isinstance(name, str) and len(name) > 0


def test_natal_decennials_seven_periods(api_natal):
    assert len(api_natal["decennials"]["periods"]) == 7
