"""
Story 3 — Planetary Positions Verification

Test strategy:
  Layer 1: API output vs direct pyswisseph (catches bugs in our wrapper)
  Layer 2: Print table for manual comparison with Morinus and Astro.com

Để chạy:
  cd backend && source .venv/bin/activate
  pytest ../tests/verification/test_planets.py -v
"""

import pytest
import swisseph as swe
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from tests.verification.conftest import TEST_CHARTS, PLANETS_TO_TEST, TOLERANCE

FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


def lon_to_sign(lon: float) -> tuple[str, float]:
    idx = int(lon / 30) % 12
    return SIGNS[idx], lon % 30


def calc_jd(chart: dict) -> float:
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart["ut_offset"]
    return swe.julday(chart["year"], chart["month"], chart["day"], hour_ut, swe.GREG_CAL)


# ─────────────────────────────────────────────
# Test 1: Julian Day calculation
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_julian_day(chart_id, chart):
    """Julian Day phải chính xác — cơ sở cho mọi calculation khác."""
    jd = calc_jd(chart)
    assert abs(jd - chart["jd"]) < 0.001, (
        f"JD mismatch for {chart_id}: got {jd:.4f}, expected {chart['jd']:.4f}"
    )


# ─────────────────────────────────────────────
# Test 2: Planet positions — longitude range valid
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_planet_longitude_range(chart_id, chart):
    """Tất cả longitudes phải trong [0°, 360°)."""
    jd = calc_jd(chart)
    for pid, pname in PLANETS_TO_TEST:
        result, _ = swe.calc_ut(jd, pid, FLAGS)
        lon = result[0]
        assert 0 <= lon < 360, (
            f"{pname} longitude out of range in {chart_id}: {lon:.4f}°"
        )


# ─────────────────────────────────────────────
# Test 3: Planet speed — direction logic
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_planet_speed_reasonable(chart_id, chart):
    """Speed phải trong range hợp lý cho từng planet."""
    MAX_SPEED = {
        swe.SUN:       1.05,   # ~1°/day
        swe.MOON:      15.5,   # ~13°/day
        swe.MERCURY:   2.3,
        swe.VENUS:     1.3,
        swe.MARS:      0.8,
        swe.JUPITER:   0.25,
        swe.SATURN:    0.15,
        swe.TRUE_NODE: 0.25,  # True Node oscillates, can exceed 0.15 briefly
        swe.MEAN_NODE: 0.07,
    }
    jd = calc_jd(chart)
    for pid, pname in PLANETS_TO_TEST:
        result, _ = swe.calc_ut(jd, pid, FLAGS)
        speed = abs(result[3])
        max_s = MAX_SPEED.get(pid, 2.5)
        assert speed <= max_s, (
            f"{pname} speed unreasonable in {chart_id}: {speed:.4f}°/day (max {max_s})"
        )


# ─────────────────────────────────────────────
# Test 4: Retrograde consistency
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_retrograde_flag(chart_id, chart):
    """Retrograde flag phải consistent với speed sign."""
    jd = calc_jd(chart)
    for pid, pname in PLANETS_TO_TEST:
        result, _ = swe.calc_ut(jd, pid, FLAGS)
        speed = result[3]
        retrograde = speed < 0
        # Sun và Moon không bao giờ retrograde
        if pid in (swe.SUN, swe.MOON):
            assert not retrograde, f"{pname} should never be retrograde"


# ─────────────────────────────────────────────
# Test 5: API output == direct pyswisseph (main accuracy test)
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_api_matches_direct_swisseph(chart_id, chart):
    """
    API output phải khớp với direct pyswisseph calls trong TOLERANCE.
    Đây là test quan trọng nhất — catch mọi bug trong API wrapper.
    """
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    resp = client.post("/chart/natal", json={
        "year": chart["year"],
        "month": chart["month"],
        "day": chart["day"],
        "hour": chart["hour"],
        "minute": chart["minute"],
        "lat": chart["lat"],
        "lon": chart["lon"],
        "hsys": "B",
        "ut_offset": chart["ut_offset"],
        "include_outer": False,
    })

    assert resp.status_code == 200, f"API error: {resp.text}"
    data = resp.json()

    jd = calc_jd(chart)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

    for planet in data["planets"]:
        pid = planet["id"]
        expected, _ = swe.calc_ut(jd, pid, flags)
        expected_lon = expected[0]
        api_lon = planet["lon"]

        assert abs(api_lon - expected_lon) < TOLERANCE, (
            f"{planet['name']} mismatch in {chart_id}: "
            f"API={api_lon:.4f}°, direct={expected_lon:.4f}°, "
            f"diff={abs(api_lon - expected_lon):.4f}°"
        )


# ─────────────────────────────────────────────
# Report: Print table for Morinus comparison
# ─────────────────────────────────────────────

def test_print_morinus_comparison_table():
    """
    Không phải test thực sự — in ra bảng để so sánh tay với Morinus.
    Chạy: pytest -v -s tests/verification/test_planets.py::test_print_morinus_comparison_table
    """
    print("\n")
    print("=" * 75)
    print("PLANET POSITIONS — SO SÁNH VỚI MORINUS")
    print("Tolerance: ≤ 0.01° | Source: Swiss Ephemeris (pyswisseph 2.10.3)")
    print("=" * 75)

    for chart_id, chart in TEST_CHARTS.items():
        jd = calc_jd(chart)
        print(f"\n📍 {chart['desc']}")
        print(f"   {chart['year']}-{chart['month']:02d}-{chart['day']:02d} "
              f"{chart['hour']:02d}:{chart['minute']:02d} UT | "
              f"Lat {chart['lat']}° Lon {chart['lon']}° | JD {jd:.4f}")
        print(f"   {'Planet':<12} {'Longitude':>10}  {'Sign':>13}  {'Speed':>9}  {'R?':>3}")
        print(f"   {'-'*12} {'-'*10}  {'-'*13}  {'-'*9}  {'-'*3}")

        for pid, pname in PLANETS_TO_TEST:
            result, _ = swe.calc_ut(jd, pid, FLAGS)
            lon = result[0]
            speed = result[3]
            sign, sign_lon = lon_to_sign(lon)
            retro = "R" if speed < 0 else ""
            deg = int(sign_lon)
            minutes = int((sign_lon - deg) * 60)
            print(f"   {pname:<12} {lon:>10.4f}°  {deg:>2}°{minutes:02d}' {sign:<9}  {speed:>+9.4f}  {retro:>3}")

    print("\n" + "=" * 75)
    print("▶ Mở Morinus: cd tools/morinus && source .venv/bin/activate && python morinus.py")
    print("▶ Nhập từng chart ở trên và so sánh values")
    print("=" * 75)
    assert True  # luôn pass
