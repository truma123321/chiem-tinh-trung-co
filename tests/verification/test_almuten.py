"""
Story 6 — Almuten Figuris Verification

Test strategy:
  Layer 1: Lot of Fortune formula (day/night)
  Layer 2: Prenatal Syzygy detection (New/Full Moon)
  Layer 3: Almuten scoring logic
  Layer 4: API output == direct core.almuten call
  Layer 5: Print table for manual comparison with Morinus

Để chạy:
  cd backend && source .venv/bin/activate
  pytest ../tests/verification/test_almuten.py -v
  pytest ../tests/verification/test_almuten.py::test_print_almuten_table -v -s
"""

import pytest
import swisseph as swe
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from tests.verification.conftest import TEST_CHARTS
from core.dignities import calc_dignities, is_day_chart, PLANET_NAMES
from core.almuten import (
    calc_lot_of_fortune,
    calc_prenatal_syzygy,
    calc_almuten,
)

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


# ─────────────────────────────────────────────
# Test 1: Lot of Fortune — formula
# ─────────────────────────────────────────────

def test_lof_day_formula():
    """Day chart: LoF = (ASC + Moon - Sun) % 360"""
    asc, moon, sun = 100.0, 200.0, 50.0
    expected = (100 + 200 - 50) % 360  # 250°
    assert abs(calc_lot_of_fortune(asc, moon, sun, daytime=True) - expected) < 0.001


def test_lof_night_formula():
    """Night chart: LoF = (ASC + Sun - Moon) % 360"""
    asc, moon, sun = 100.0, 200.0, 50.0
    expected = (100 + 50 - 200) % 360  # 310°
    assert abs(calc_lot_of_fortune(asc, moon, sun, daytime=False) - expected) < 0.001


def test_lof_result_in_range():
    """LoF must always be in [0°, 360°)."""
    for asc in (0, 90, 180, 270, 350):
        for moon in (0, 90, 180, 270, 350):
            for sun in (0, 90, 180, 270):
                lof = calc_lot_of_fortune(asc, moon, sun, daytime=True)
                assert 0 <= lof < 360, f"LoF out of range: {lof}"
                lof = calc_lot_of_fortune(asc, moon, sun, daytime=False)
                assert 0 <= lof < 360, f"LoF out of range: {lof}"


def test_lof_day_night_differ_when_sun_moon_differ():
    """Day and night LoF should give different results unless Moon == Sun."""
    lof_day   = calc_lot_of_fortune(100, 200, 50, daytime=True)
    lof_night = calc_lot_of_fortune(100, 200, 50, daytime=False)
    assert lof_day != lof_night


def test_lof_same_when_sun_equals_moon():
    """If Sun == Moon (New Moon), day and night LoF are identical."""
    lof_day   = calc_lot_of_fortune(100, 150, 150, daytime=True)
    lof_night = calc_lot_of_fortune(100, 150, 150, daytime=False)
    assert abs(lof_day - lof_night) < 0.001


# ─────────────────────────────────────────────
# Test 2: Prenatal Syzygy — validation
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_syzygy_in_range(chart_id, chart):
    """Syzygy longitude must be in [0°, 360°)."""
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart["ut_offset"]
    jd = swe.julday(chart["year"], chart["month"], chart["day"], hour_ut, swe.GREG_CAL)
    lon, _ = calc_prenatal_syzygy(jd)
    assert 0 <= lon < 360, f"{chart_id}: syzygy lon out of range: {lon}"


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_syzygy_is_before_birth(chart_id, chart):
    """The syzygy must have occurred BEFORE birth (phase near 0° or 180° at syzygy time)."""
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart["ut_offset"]
    jd = swe.julday(chart["year"], chart["month"], chart["day"], hour_ut, swe.GREG_CAL)
    syz_lon, is_new = calc_prenatal_syzygy(jd)

    # Verify: at syzygy time, Moon was at syz_lon
    # We can't easily verify the exact JD, but we can check the syzygy type:
    # The current phase should match what we expect
    FLAGS = swe.FLG_SWIEPH
    sun_res, _ = swe.calc_ut(jd, swe.SUN, FLAGS)
    moon_res, _ = swe.calc_ut(jd, swe.MOON, FLAGS)
    phase = (moon_res[0] - sun_res[0]) % 360

    # If is_new: phase should be < 180 (New Moon was more recent)
    # If is_full: phase should be > 180 (Full Moon was more recent)
    if is_new:
        assert phase < 180, (
            f"{chart_id}: expected phase < 180 for New Moon syzygy, got {phase:.1f}°"
        )
    else:
        assert phase > 180, (
            f"{chart_id}: expected phase > 180 for Full Moon syzygy, got {phase:.1f}°"
        )


# ─────────────────────────────────────────────
# Test 3: Almuten scoring
# ─────────────────────────────────────────────

def test_almuten_winner_has_max_score():
    """Winner's total must equal the maximum across all planets."""
    hour_ut = 10.5
    jd = swe.julday(1990, 6, 15, hour_ut, swe.GREG_CAL)
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    _, ascmc = swe.houses(jd, 41.9, 12.5, b"B")
    asc = ascmc[0]
    planet_lons = {}
    for pid in range(7):
        res, _ = swe.calc_ut(jd, pid, FLAGS)
        planet_lons[pid] = res[0]
    sun_lon  = planet_lons[0]
    moon_lon = planet_lons[1]
    day = is_day_chart(sun_lon, asc)

    result = calc_almuten(planet_lons, asc, sun_lon, moon_lon, day, jd)
    max_total = max(result.total_scores.values())
    assert result.total_scores[result.winner] == max_total


def test_almuten_has_5_points():
    """Almuten calculation always uses exactly 5 significator points."""
    hour_ut = 10.5
    jd = swe.julday(1990, 6, 15, hour_ut, swe.GREG_CAL)
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    _, ascmc = swe.houses(jd, 41.9, 12.5, b"B")
    asc = ascmc[0]
    planet_lons = {pid: swe.calc_ut(jd, pid, FLAGS)[0][0] for pid in range(7)}
    sun_lon = planet_lons[0]; moon_lon = planet_lons[1]
    day = is_day_chart(sun_lon, asc)

    result = calc_almuten(planet_lons, asc, sun_lon, moon_lon, day, jd)
    assert len(result.points) == 5
    point_names = {p.name for p in result.points}
    assert point_names == {"Sun", "Moon", "ASC", "Fortune", "Syzygy"}


def test_almuten_scores_are_sum_of_points():
    """Total score for each planet must equal sum across all 5 points."""
    hour_ut = 10.5
    jd = swe.julday(1990, 6, 15, hour_ut, swe.GREG_CAL)
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    _, ascmc = swe.houses(jd, 41.9, 12.5, b"B")
    asc = ascmc[0]
    planet_lons = {pid: swe.calc_ut(jd, pid, FLAGS)[0][0] for pid in range(7)}
    sun_lon = planet_lons[0]; moon_lon = planet_lons[1]
    day = is_day_chart(sun_lon, asc)

    result = calc_almuten(planet_lons, asc, sun_lon, moon_lon, day, jd)
    for pname, total in result.total_scores.items():
        summed = sum(pt.scores[pname] for pt in result.points)
        assert summed == total, (
            f"{pname}: total={total}, sum of points={summed}"
        )


# ─────────────────────────────────────────────
# Test 4: API output == direct core.almuten call
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_api_almuten_matches_direct(chart_id, chart):
    """API almuten output must match direct calc_almuten() call."""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    resp = client.post("/chart/natal", json={
        "year": chart["year"], "month": chart["month"], "day": chart["day"],
        "hour": chart["hour"], "minute": chart["minute"],
        "lat": chart["lat"], "lon": chart["lon"],
        "hsys": "B", "ut_offset": chart["ut_offset"],
    })
    assert resp.status_code == 200, f"API error: {resp.text}"
    data = resp.json()

    api_alm = data["almuten"]

    # Recompute directly
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart["ut_offset"]
    jd = swe.julday(chart["year"], chart["month"], chart["day"], hour_ut, swe.GREG_CAL)
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    _, ascmc = swe.houses(jd, chart["lat"], chart["lon"], b"B")
    asc = ascmc[0]
    planet_lons = {pid: swe.calc_ut(jd, pid, FLAGS)[0][0] for pid in range(7)}
    sun_lon = planet_lons[0]; moon_lon = planet_lons[1]
    day = is_day_chart(sun_lon, asc)

    direct = calc_almuten(planet_lons, asc, sun_lon, moon_lon, day, jd)

    assert api_alm["winner"] == direct.winner, (
        f"{chart_id}: winner API={api_alm['winner']}, direct={direct.winner}"
    )
    for pname in PLANET_NAMES.values():
        assert api_alm["total_scores"][pname] == direct.total_scores[pname], (
            f"{chart_id} {pname}: API={api_alm['total_scores'][pname]}, "
            f"direct={direct.total_scores[pname]}"
        )


# ─────────────────────────────────────────────
# Report: Print table for Morinus comparison
# ─────────────────────────────────────────────

def test_print_almuten_table():
    """
    In ra bảng để so sánh tay với Morinus Tables → Almuten Figuris.
    Chạy: pytest -v -s tests/verification/test_almuten.py::test_print_almuten_table
    """
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    EPHE_PATH = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../../tools/morinus/SWEP/Ephem")
    )
    swe.set_ephe_path(EPHE_PATH)

    print("\n")
    print("=" * 80)
    print("ALMUTEN FIGURIS — SO SÁNH VỚI MORINUS")
    print("5 Significators: Sun, Moon, ASC, Lot of Fortune, Prenatal Syzygy")
    print("=" * 80)

    for chart_id, chart in TEST_CHARTS.items():
        hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart["ut_offset"]
        jd = swe.julday(chart["year"], chart["month"], chart["day"], hour_ut, swe.GREG_CAL)
        _, ascmc = swe.houses(jd, chart["lat"], chart["lon"], b"B")
        asc = ascmc[0]
        planet_lons = {pid: swe.calc_ut(jd, pid, FLAGS)[0][0] for pid in range(7)}
        sun_lon = planet_lons[0]; moon_lon = planet_lons[1]
        day = is_day_chart(sun_lon, asc)

        result = calc_almuten(planet_lons, asc, sun_lon, moon_lon, day, jd)

        print(f"\n📍 {chart['desc']}  ({'Day' if day else 'Night'} chart)")
        print(f"   LoF: {result.lot_of_fortune:.2f}°  "
              f"Syzygy: {result.syzygy_lon:.2f}° ({'NM' if result.syzygy_is_new_moon else 'FM'})")

        # Header
        print(f"\n   {'Planet':<10}", end="")
        for pt in result.points:
            print(f"  {pt.name:>8}", end="")
        print(f"  {'TOTAL':>8}  Winner")
        print(f"   {'-'*10}", end="")
        for _ in result.points:
            print(f"  {'-'*8}", end="")
        print(f"  {'-'*8}  ------")

        max_score = max(result.total_scores.values())
        for pid in range(7):
            pname = PLANET_NAMES[pid]
            total = result.total_scores[pname]
            marker = " ◄" if total == max_score else ""
            print(f"   {pname:<10}", end="")
            for pt in result.points:
                s = pt.scores[pname]
                print(f"  {s:>8}", end="")
            print(f"  {total:>8}{marker}")

        print(f"\n   ★ Almuten Figuris: {result.winner}"
              + (" (dead heat)" if result.dead_heat else ""))

    print("\n" + "=" * 80)
    print("▶ Morinus → Tables → Chart Almuten → compare winner + scores")
    print("=" * 80)
    assert True
