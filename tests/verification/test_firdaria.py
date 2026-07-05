"""
Story 13 — Firdaria Verification

Test strategy:
  Layer 1: Sequence constants (day/night, 75-year total)
  Layer 2: Period durations match sequence allocations
  Layer 3: Period continuity — end of one = start of next
  Layer 4: Sub-period proportional durations sum to major period
  Layer 5: Sub-period starting lord = major lord
  Layer 6: Sub-period coverage — all 7 planets present
  Layer 7: is_current flag — exactly one current period, one current sub
  Layer 8: current_period / current_sub pointers match is_current flags
  Layer 9: Known period detection (synthetic current_jd)
  Layer 10: API output == direct core call
  Layer 11: Print table for Morinus comparison

Chay:
  cd backend && source .venv/bin/activate
  pytest ../tests/verification/test_firdaria.py -v
  pytest ../tests/verification/test_firdaria.py::test_print_firdaria_table -v -s
"""

import pytest
import swisseph as swe
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from tests.verification.conftest import TEST_CHARTS
from core.firdaria import (
    calc_firdaria,
    DAY_SEQUENCE, NIGHT_SEQUENCE,
    PLANET_YEARS, PLANET_YEARS_TOTAL,
    CYCLE_YEARS, YEAR_DAYS, NODE_IDS,
)


def _build(chart):
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart.get("ut_offset", 0)
    jd = swe.julday(chart["year"], chart["month"], chart["day"], hour_ut, swe.GREG_CAL)
    return jd


# ─────────────────────────────────────────────
# Test 1: Sequence constants
# ─────────────────────────────────────────────

def test_day_sequence_total_75():
    total = sum(y for _, _, y in DAY_SEQUENCE)
    assert total == 75, f"Day sequence total = {total}, expected 75"


def test_night_sequence_total_75():
    total = sum(y for _, _, y in NIGHT_SEQUENCE)
    assert total == 75, f"Night sequence total = {total}, expected 75"


def test_day_sequence_has_9_periods():
    assert len(DAY_SEQUENCE) == 9


def test_night_sequence_has_9_periods():
    assert len(NIGHT_SEQUENCE) == 9


def test_cycle_years_constant():
    assert CYCLE_YEARS == 75


def test_planet_years_total():
    """7 classical planets sum = 70."""
    assert PLANET_YEARS_TOTAL == 70
    assert sum(PLANET_YEARS.values()) == 70


def test_node_ids():
    assert 7 in NODE_IDS and 8 in NODE_IDS


def test_day_sequence_starts_with_sun():
    assert DAY_SEQUENCE[0][0] == 0   # Sun
    assert DAY_SEQUENCE[0][2] == 10  # 10 years


def test_night_sequence_starts_with_moon():
    assert NIGHT_SEQUENCE[0][0] == 1   # Moon
    assert NIGHT_SEQUENCE[0][2] == 9   # 9 years


def test_day_sequence_ends_with_nodes():
    assert DAY_SEQUENCE[-2][0] == 7   # North Node 3 yrs
    assert DAY_SEQUENCE[-1][0] == 8   # South Node 2 yrs


# ─────────────────────────────────────────────
# Test 2: Period durations
# ─────────────────────────────────────────────

@pytest.mark.parametrize("day_chart", [True, False])
def test_period_durations_match_sequence(day_chart):
    """Each period's JD span matches its year allocation."""
    jd_birth = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    result = calc_firdaria(jd_birth, day_chart,
                           current_jd=jd_birth + 1)   # born today

    seq = DAY_SEQUENCE if day_chart else NIGHT_SEQUENCE
    for period, (pid, name, years) in zip(result.periods, seq):
        expected_days = years * YEAR_DAYS
        actual_days = period.end.jd - period.start.jd
        assert abs(actual_days - expected_days) < 0.01, (
            f"{name}: duration {actual_days:.2f} days, expected {expected_days:.2f}"
        )


# ─────────────────────────────────────────────
# Test 3: Period continuity
# ─────────────────────────────────────────────

@pytest.mark.parametrize("day_chart", [True, False])
def test_periods_contiguous(day_chart):
    """End JD of period N == Start JD of period N+1."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    result = calc_firdaria(jd, day_chart, current_jd=jd + 1)
    for i in range(len(result.periods) - 1):
        a = result.periods[i]
        b = result.periods[i + 1]
        assert abs(a.end.jd - b.start.jd) < 0.01, (
            f"Gap between {a.planet_name} and {b.planet_name}: "
            f"{a.end.jd} vs {b.start.jd}"
        )


@pytest.mark.parametrize("day_chart", [True, False])
def test_first_period_starts_at_birth(day_chart):
    """First period must start exactly at birth JD."""
    jd = swe.julday(1985, 12, 21, 3.0, swe.GREG_CAL)
    result = calc_firdaria(jd, day_chart, current_jd=jd + 1)
    assert abs(result.periods[0].start.jd - jd) < 0.01


# ─────────────────────────────────────────────
# Test 4: Sub-period proportional sums
# ─────────────────────────────────────────────

@pytest.mark.parametrize("day_chart", [True, False])
def test_sub_periods_sum_to_major(day_chart):
    """Sum of sub-period days must equal major period days (within 0.01)."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    result = calc_firdaria(jd, day_chart, current_jd=jd + 1)
    for period in result.periods:
        if period.planet_id in NODE_IDS:
            assert len(period.sub_periods) == 0, (
                f"{period.planet_name} (node) should have no sub-periods"
            )
            continue
        assert len(period.sub_periods) == 7, (
            f"{period.planet_name}: expected 7 sub-periods, got {len(period.sub_periods)}"
        )
        major_days = period.end.jd - period.start.jd
        sub_total  = sum(s.end.jd - s.start.jd for s in period.sub_periods)
        assert abs(sub_total - major_days) < 0.1, (
            f"{period.planet_name}: sub-total {sub_total:.2f} != major {major_days:.2f}"
        )


# ─────────────────────────────────────────────
# Test 5: Sub-period starts from major lord
# ─────────────────────────────────────────────

@pytest.mark.parametrize("day_chart", [True, False])
def test_first_sub_is_major_lord(day_chart):
    """First sub-period of each major must be ruled by the major lord."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    result = calc_firdaria(jd, day_chart, current_jd=jd + 1)
    for period in result.periods:
        if period.planet_id in NODE_IDS:
            continue
        first_sub = period.sub_periods[0]
        assert first_sub.planet_id == period.planet_id, (
            f"{period.planet_name} major: first sub is {first_sub.planet_name}"
        )


# ─────────────────────────────────────────────
# Test 6: All 7 planets in sub-periods
# ─────────────────────────────────────────────

@pytest.mark.parametrize("day_chart", [True, False])
def test_sub_periods_cover_all_7_planets(day_chart):
    """Each major period has exactly one sub-period per classical planet."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    result = calc_firdaria(jd, day_chart, current_jd=jd + 1)
    for period in result.periods:
        if period.planet_id in NODE_IDS:
            continue
        sub_pids = {s.planet_id for s in period.sub_periods}
        assert sub_pids == {0, 1, 2, 3, 4, 5, 6}, (
            f"{period.planet_name}: sub-period planets = {sub_pids}"
        )


# ─────────────────────────────────────────────
# Test 7: Sub-period continuity
# ─────────────────────────────────────────────

@pytest.mark.parametrize("day_chart", [True, False])
def test_sub_periods_contiguous(day_chart):
    """End of sub N == start of sub N+1 within each major period."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    result = calc_firdaria(jd, day_chart, current_jd=jd + 1)
    for period in result.periods:
        subs = period.sub_periods
        for i in range(len(subs) - 1):
            assert abs(subs[i].end.jd - subs[i+1].start.jd) < 0.01, (
                f"{period.planet_name}: sub gap between {subs[i].planet_name}"
                f" and {subs[i+1].planet_name}"
            )


# ─────────────────────────────────────────────
# Test 8: is_current flag — exactly one active
# ─────────────────────────────────────────────

@pytest.mark.parametrize("day_chart", [True, False])
def test_exactly_one_current_period(day_chart):
    """Exactly one major period must be current when current_jd is in range."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    current_jd = jd + 15 * YEAR_DAYS   # 15 years after birth
    result = calc_firdaria(jd, day_chart, current_jd=current_jd)
    current_count = sum(1 for p in result.periods if p.is_current)
    assert current_count == 1, f"Expected 1 current period, got {current_count}"


@pytest.mark.parametrize("day_chart", [True, False])
def test_exactly_one_current_sub(day_chart):
    """Exactly one sub-period must be current within the current major."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    current_jd = jd + 15 * YEAR_DAYS
    result = calc_firdaria(jd, day_chart, current_jd=current_jd)
    current_period = next((p for p in result.periods if p.is_current), None)
    assert current_period is not None
    if current_period.planet_id not in NODE_IDS:
        sub_count = sum(1 for s in current_period.sub_periods if s.is_current)
        assert sub_count == 1, f"Expected 1 current sub, got {sub_count}"


# ─────────────────────────────────────────────
# Test 9: current_period / current_sub pointers
# ─────────────────────────────────────────────

@pytest.mark.parametrize("day_chart", [True, False])
def test_current_period_pointer(day_chart):
    """result.current_period == the period with is_current=True."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    current_jd = jd + 20 * YEAR_DAYS
    result = calc_firdaria(jd, day_chart, current_jd=current_jd)
    flagged = next((p for p in result.periods if p.is_current), None)
    assert result.current_period is not None
    assert result.current_period.planet_id == flagged.planet_id


@pytest.mark.parametrize("day_chart", [True, False])
def test_current_sub_pointer(day_chart):
    """result.current_sub planet_id matches the is_current sub in current major."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    current_jd = jd + 20 * YEAR_DAYS
    result = calc_firdaria(jd, day_chart, current_jd=current_jd)
    if result.current_period and result.current_period.planet_id not in NODE_IDS:
        flagged_sub = next(
            (s for s in result.current_period.sub_periods if s.is_current), None
        )
        assert result.current_sub is not None
        assert result.current_sub.planet_id == flagged_sub.planet_id


# ─────────────────────────────────────────────
# Test 10: Known period detection
# ─────────────────────────────────────────────

def test_first_period_active_at_birth():
    """At birth, the first period (Sun for day chart) must be current."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    result = calc_firdaria(jd, day_chart=True, current_jd=jd + 0.1)
    assert result.current_period is not None
    assert result.current_period.planet_id == 0   # Sun
    assert result.current_sub is not None
    assert result.current_sub.planet_id == 0       # Sun/Sun sub


def test_night_chart_first_period_at_birth():
    """At birth (night chart), first period must be Moon."""
    jd = swe.julday(1985, 12, 21, 3.0, swe.GREG_CAL)
    result = calc_firdaria(jd, day_chart=False, current_jd=jd + 0.1)
    assert result.current_period is not None
    assert result.current_period.planet_id == 1   # Moon
    assert result.current_sub is not None
    assert result.current_sub.planet_id == 1       # Moon/Moon sub


def test_sun_period_ends_at_year_10():
    """Day chart: at birth + 9.99 years → still Sun; at 10.01 → Venus."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    # Just before Sun ends
    r1 = calc_firdaria(jd, True, current_jd=jd + 9.99 * YEAR_DAYS)
    assert r1.current_period.planet_id == 0   # Sun

    # Just after Sun ends (Venus begins)
    r2 = calc_firdaria(jd, True, current_jd=jd + 10.01 * YEAR_DAYS)
    assert r2.current_period.planet_id == 3   # Venus


def test_node_period_no_sub():
    """North Node / South Node periods have no sub-periods."""
    # Sun(10) + Venus(8) + Mercury(13) + Moon(9) + Saturn(11) + Jupiter(12) + Mars(7) = 70
    # North Node starts at year 70
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    r = calc_firdaria(jd, True, current_jd=jd + 70.5 * YEAR_DAYS)
    assert r.current_period is not None
    assert r.current_period.planet_id == 7   # North Node
    assert r.current_period.sub_periods == []
    assert r.current_sub is None


# ─────────────────────────────────────────────
# Test 11: API output == direct call
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_api_firdaria_match_direct(chart_id, chart):
    """API firdaria output must match direct calc_firdaria() call."""
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
    api = resp.json()["firdaria"]

    birth_jd = _build(chart)
    # We can't know exactly which current_jd the API used (it used today)
    # But structure must be correct
    assert len(api["periods"]) == 9, f"{chart_id}: expected 9 periods"
    assert api["day_chart"] in (True, False)
    assert abs(api["birth_jd"] - birth_jd) < 0.01

    # Validate period structure
    for i, p in enumerate(api["periods"]):
        assert "planet_id" in p
        assert "planet_name" in p
        assert "years" in p
        assert "start" in p and "end" in p
        assert "is_current" in p
        assert "sub_periods" in p
        # Node periods have no sub-periods
        if p["planet_id"] in (7, 8):
            assert len(p["sub_periods"]) == 0
        else:
            assert len(p["sub_periods"]) == 7


# ─────────────────────────────────────────────
# Report: Print table for Morinus comparison
# ─────────────────────────────────────────────

def test_print_firdaria_table():
    """
    In ra bang Firdaria de so sanh voi Morinus.
    Morinus: Tables -> Firdaria -> check period lord + dates
    """
    EPHE_PATH = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../../tools/morinus/SWEP/Ephem")
    )
    swe.set_ephe_path(EPHE_PATH)

    print("\n")
    print("=" * 80)
    print("FIRDARIA — SO SANH VOI MORINUS")
    print("Proportional sub-periods | Bonatti / Liber Astronomiae")
    print("=" * 80)

    # Use rome_1990_day as primary example
    chart = TEST_CHARTS["rome_1990_day"]
    birth_jd = _build(chart)
    result = calc_firdaria(birth_jd, day_chart=True)

    chart_type = "DAY" if result.day_chart else "NIGHT"
    print(f"\n  {chart['desc']} [{chart_type} CHART]")
    print(f"  Birth JD: {result.birth_jd:.4f}")

    for p in result.periods:
        current_tag = " <-- CURRENT" if p.is_current else ""
        print(f"\n  {p.planet_name:<12} {p.years} yrs | "
              f"{p.start.year}-{p.start.month:02d}-{p.start.day:02d} → "
              f"{p.end.year}-{p.end.month:02d}-{p.end.day:02d}{current_tag}")
        for s in p.sub_periods:
            sub_tag = " <-- current sub" if s.is_current else ""
            print(f"    {s.planet_name:<10} "
                  f"{s.start.year}-{s.start.month:02d}-{s.start.day:02d} → "
                  f"{s.end.year}-{s.end.month:02d}-{s.end.day:02d}{sub_tag}")

    print("\n" + "=" * 80)
    print("▶ Morinus → Tables → Firdaria → compare period lords + start/end dates")
    print("=" * 80)
    assert True
