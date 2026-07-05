"""
Story 14 — Annual Profections Verification

Test strategy:
  Layer 1: Profected ASC formula (natal ASC + age×30°)
  Layer 2: House progression 1→12 over 12 years, repeats at 13
  Layer 3: Lord of the Year = domicile ruler of profected sign
  Layer 4: Sign mapping correctness (Aries→Mars, Taurus→Venus, etc.)
  Layer 5: Cycle detection (age 0-11 = cycle 0, age 12-23 = cycle 1, etc.)
  Layer 6: is_current flag — exactly one year active
  Layer 7: Activated planets in profected sign
  Layer 8: Date integrity — start/end continuity within cycle
  Layer 9: Known-age spot checks
  Layer 10: API output == direct core call
  Layer 11: Print table for Morinus comparison

Chay:
  cd backend && source .venv/bin/activate
  pytest ../tests/verification/test_profections.py -v
  pytest ../tests/verification/test_profections.py::test_print_profections_table -v -s
"""

import pytest
import swisseph as swe
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from tests.verification.conftest import TEST_CHARTS
from core.profections import calc_profections, YEAR_DAYS, SIGNS
from core.dignities import DOMICILE, PLANET_NAMES, is_day_chart


def _build(chart):
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart.get("ut_offset", 0)
    jd = swe.julday(chart["year"], chart["month"], chart["day"], hour_ut, swe.GREG_CAL)
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    lons = {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, FLAGS)
        lons[pid] = r[0]
    cusps, ascmc = swe.houses(jd, chart["lat"], chart["lon"], b"B")
    asc = ascmc[0]
    return jd, lons, asc


# ─────────────────────────────────────────────
# Test 1: Profected ASC formula
# ─────────────────────────────────────────────

def test_profected_asc_at_birth():
    """Age 0: profected ASC == natal ASC."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    lons = {pid: 0.0 for pid in range(7)}
    asc = 45.0
    result = calc_profections(jd, asc, lons, current_jd=jd + 0.1)
    assert abs(result.years[0].profected_asc - asc) < 0.01


def test_profected_asc_at_age_1():
    """Age 1: profected ASC == natal ASC + 30°."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    lons = {pid: 0.0 for pid in range(7)}
    asc = 45.0
    result = calc_profections(jd, asc, lons, current_jd=jd + 0.1)
    year1 = result.years[1]
    assert abs(year1.profected_asc - (asc + 30.0) % 360) < 0.01


def test_profected_asc_wraps_360():
    """Profected ASC wraps at 360°."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    lons = {pid: 0.0 for pid in range(7)}
    asc = 350.0   # close to 360°
    result = calc_profections(jd, asc, lons, current_jd=jd + 0.1)
    # age 1: (350 + 30) % 360 = 20°
    year1 = result.years[1]
    assert abs(year1.profected_asc - 20.0) < 0.01


def test_profected_asc_age_12_equals_birth():
    """Age 12 profected ASC == natal ASC (full cycle)."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    lons = {pid: 0.0 for pid in range(7)}
    asc = 75.3
    # current_jd at age 12
    r1 = calc_profections(jd, asc, lons, current_jd=jd + 0.1)   # age 0 cycle
    r2 = calc_profections(jd, asc, lons, current_jd=jd + 12 * YEAR_DAYS + 1)  # age 12
    # age 0 in cycle 0 and age 12 (house 1 in cycle 1) should have same profected ASC
    assert abs(r1.years[0].profected_asc - r2.current_year.profected_asc) < 0.01


# ─────────────────────────────────────────────
# Test 2: House progression
# ─────────────────────────────────────────────

def test_houses_1_through_12_in_cycle():
    """Years[0..11].house must be 1..12."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    lons = {pid: 0.0 for pid in range(7)}
    result = calc_profections(jd, 0.0, lons, current_jd=jd + 0.1)
    houses = [y.house for y in result.years]
    assert houses == list(range(1, 13)), f"Houses: {houses}"


def test_house_cycles_correctly():
    """Age 12 = house 1 again."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    lons = {pid: 0.0 for pid in range(7)}
    result = calc_profections(jd, 0.0, lons, current_jd=jd + 12 * YEAR_DAYS + 1)
    assert result.current_year.house == 1
    assert result.current_year.age == 12


def test_house_at_age_35():
    """Age 35: 35 % 12 = 11 → house 12."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    lons = {pid: 0.0 for pid in range(7)}
    result = calc_profections(jd, 0.0, lons, current_jd=jd + 35 * YEAR_DAYS + 1)
    assert result.current_age == 35
    assert result.current_year.house == 12   # 35 % 12 = 11 → house 12 (0-indexed 11 → 1-based 12)


# ─────────────────────────────────────────────
# Test 3: Lord of the Year matches DOMICILE
# ─────────────────────────────────────────────

def test_lord_matches_domicile():
    """Lord of the Year must be DOMICILE[profected_sign_idx]."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    lons = {pid: 0.0 for pid in range(7)}
    asc = 0.0  # 0° Aries
    result = calc_profections(jd, asc, lons, current_jd=jd + 0.1)
    for y in result.years:
        expected_lord = DOMICILE[y.profected_sign_idx]
        assert y.lord_id == expected_lord, (
            f"Age {y.age} house {y.house}: lord={y.lord_id}, expected={expected_lord}"
        )


def test_lord_name_matches_planet_names():
    """lord_name == PLANET_NAMES[lord_id]."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    lons = {pid: 0.0 for pid in range(7)}
    result = calc_profections(jd, 0.0, lons, current_jd=jd + 0.1)
    for y in result.years:
        assert y.lord_name == PLANET_NAMES[y.lord_id]


# ─────────────────────────────────────────────
# Test 4: Known lord assignments (ASC=0° Aries)
# ─────────────────────────────────────────────

def test_aries_asc_lords_cycle():
    """ASC at 0° Aries: house 1=Mars, 2=Venus, 3=Mercury, 4=Moon, 5=Sun, 6=Mercury..."""
    # Known domicile lords for each sign 0-11
    expected_lords = [
        4,  # Aries → Mars
        3,  # Taurus → Venus
        2,  # Gemini → Mercury
        1,  # Cancer → Moon
        0,  # Leo → Sun
        2,  # Virgo → Mercury
        3,  # Libra → Venus
        4,  # Scorpio → Mars
        5,  # Sagittarius → Jupiter
        6,  # Capricorn → Saturn
        6,  # Aquarius → Saturn
        5,  # Pisces → Jupiter
    ]
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    lons = {pid: 0.0 for pid in range(7)}
    result = calc_profections(jd, 0.0, lons, current_jd=jd + 0.1)
    for i, y in enumerate(result.years):
        assert y.lord_id == expected_lords[i], (
            f"House {y.house}: got lord {y.lord_id}, expected {expected_lords[i]}"
        )


# ─────────────────────────────────────────────
# Test 5: is_current exactly one entry
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_exactly_one_current_year(chart_id, chart):
    """Exactly one ProfectionYear must be current."""
    jd, lons, asc = _build(chart)
    result = calc_profections(jd, asc, lons)
    current_count = sum(1 for y in result.years if y.is_current)
    assert current_count == 1, f"{chart_id}: {current_count} current years"


# ─────────────────────────────────────────────
# Test 6: current_year pointer
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_current_year_pointer_matches_flag(chart_id, chart):
    """result.current_year.age must match the is_current year."""
    jd, lons, asc = _build(chart)
    result = calc_profections(jd, asc, lons)
    flagged = next(y for y in result.years if y.is_current)
    assert result.current_year is not None
    assert result.current_year.age == flagged.age


# ─────────────────────────────────────────────
# Test 7: Activated planets
# ─────────────────────────────────────────────

def test_activated_planets_in_profected_sign():
    """Activated planets must be in the profected sign."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    asc = 0.0   # Aries, age 0 → house 1, Aries
    # Place Sun and Venus in Aries (sign 0), others elsewhere
    lons = {0: 10.0, 1: 200.0, 2: 60.0, 3: 25.0, 4: 120.0, 5: 180.0, 6: 240.0}
    result = calc_profections(jd, asc, lons, current_jd=jd + 0.1)
    activated = result.current_year.activated_planet_ids
    assert 0 in activated, "Sun in Aries should be activated"
    assert 3 in activated, "Venus in Aries should be activated"
    assert 1 not in activated, "Moon not in Aries should not be activated"


def test_no_activated_planets_when_empty_sign():
    """If no planets are in the profected sign, activated list is empty."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    asc = 0.0   # Aries at age 0
    # All planets outside Aries (all above 30°)
    lons = {pid: 50.0 + pid * 30 for pid in range(7)}
    result = calc_profections(jd, asc, lons, current_jd=jd + 0.1)
    assert result.current_year.activated_planet_ids == []


# ─────────────────────────────────────────────
# Test 8: Table of 12 years
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_table_has_12_years(chart_id, chart):
    jd, lons, asc = _build(chart)
    result = calc_profections(jd, asc, lons)
    assert len(result.years) == 12, f"{chart_id}: {len(result.years)} years in table"


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_years_table_ages_sequential(chart_id, chart):
    """Ages in the table must be consecutive integers."""
    jd, lons, asc = _build(chart)
    result = calc_profections(jd, asc, lons)
    ages = [y.age for y in result.years]
    assert ages == list(range(ages[0], ages[0] + 12)), (
        f"{chart_id}: ages not sequential: {ages}"
    )


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_profected_asc_steps_by_30(chart_id, chart):
    """Consecutive profected ASC values differ by 30° (mod 360)."""
    jd, lons, asc = _build(chart)
    result = calc_profections(jd, asc, lons)
    for i in range(len(result.years) - 1):
        a = result.years[i].profected_asc
        b = result.years[i + 1].profected_asc
        diff = (b - a) % 360.0
        assert abs(diff - 30.0) < 0.01, (
            f"{chart_id}: step {i}→{i+1}: diff={diff:.4f}° (expected 30°)"
        )


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_sign_idx_matches_profected_asc(chart_id, chart):
    """profected_sign_idx must equal int(profected_asc/30) % 12."""
    jd, lons, asc = _build(chart)
    result = calc_profections(jd, asc, lons)
    for y in result.years:
        expected_idx = int(y.profected_asc / 30.0) % 12
        assert y.profected_sign_idx == expected_idx, (
            f"{chart_id} age {y.age}: sign_idx={y.profected_sign_idx}, expected={expected_idx}"
        )


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_sign_name_matches_idx(chart_id, chart):
    """profected_sign must match SIGNS[profected_sign_idx]."""
    jd, lons, asc = _build(chart)
    result = calc_profections(jd, asc, lons)
    for y in result.years:
        assert y.profected_sign == SIGNS[y.profected_sign_idx]


# ─────────────────────────────────────────────
# Test 9: API output == direct call
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_api_profections_match_direct(chart_id, chart):
    """API profections output must match direct calc_profections() call."""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    resp = client.post("/chart/natal", json={
        "year": chart["year"], "month": chart["month"], "day": chart["day"],
        "hour": chart["hour"], "minute": chart["minute"],
        "lat": chart["lat"], "lon": chart["lon"],
        "hsys": "B", "ut_offset": chart.get("ut_offset", 0),
    })
    assert resp.status_code == 200, f"API error: {resp.text}"
    api = resp.json()["profections"]

    jd, lons, asc = _build(chart)
    direct = calc_profections(jd, asc, lons)

    assert len(api["years"]) == 12
    assert abs(api["birth_jd"] - direct.birth_jd) < 0.01

    for api_y, dir_y in zip(api["years"], direct.years):
        assert api_y["age"] == dir_y.age
        assert api_y["house"] == dir_y.house
        assert api_y["lord_id"] == dir_y.lord_id
        assert abs(api_y["profected_asc"] - dir_y.profected_asc) < 0.001
        assert api_y["profected_sign"] == dir_y.profected_sign


# ─────────────────────────────────────────────
# Report: Print table for Morinus comparison
# ─────────────────────────────────────────────

def test_print_profections_table():
    """
    In ra bang profections de so sanh voi Morinus.
    Morinus: Tables -> Profections -> check house + lord per year
    """
    EPHE_PATH = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../../tools/morinus/SWEP/Ephem")
    )
    swe.set_ephe_path(EPHE_PATH)
    planet_names = {0:"Sun",1:"Moon",2:"Mercury",3:"Venus",4:"Mars",5:"Jupiter",6:"Saturn"}

    print("\n")
    print("=" * 80)
    print("ANNUAL PROFECTIONS — SO SANH VOI MORINUS")
    print("ASC advances 30° per year | Lord = domicile ruler of profected sign")
    print("=" * 80)

    for chart_id, chart in TEST_CHARTS.items():
        jd, lons, asc = _build(chart)
        result = calc_profections(jd, asc, lons)

        print(f"\n  {chart['desc']}")
        print(f"  Current age: {result.current_age}")
        print(f"  {'Age':<5} {'House':<6} {'Sign':<14} {'Lord':<10} "
              f"{'Start':>12}  {'End':>12}  Activated")
        print(f"  {'-'*5} {'-'*6} {'-'*14} {'-'*10} {'-'*12}  {'-'*12}  {'-'*15}")
        for y in result.years:
            tag = " <<" if y.is_current else ""
            activated_str = ",".join(planet_names[pid] for pid in y.activated_planet_ids) or "-"
            print(f"  {y.age:<5} {y.house:<6} {y.profected_sign:<14} {y.lord_name:<10} "
                  f"{y.start.year}-{y.start.month:02d}-{y.start.day:02d}  "
                  f"{y.end.year}-{y.end.month:02d}-{y.end.day:02d}  "
                  f"{activated_str}{tag}")

    print("\n" + "=" * 80)
    print("▶ Morinus → Tables → Profections → compare house + lord of the year")
    print("=" * 80)
    assert True
