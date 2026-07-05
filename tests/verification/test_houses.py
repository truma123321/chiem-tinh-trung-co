"""
Story 4 — House Systems Verification (Alcabitius + Regiomontanus)

Test strategy:
  Layer 1: API output vs direct pyswisseph (catches bugs in wrapper)
  Layer 2: Print table for manual comparison with Morinus

Để chạy:
  cd backend && source .venv/bin/activate
  pytest ../tests/verification/test_houses.py -v
  pytest ../tests/verification/test_houses.py::test_print_morinus_comparison_table -v -s
"""

import pytest
import swisseph as swe
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from tests.verification.conftest import TEST_CHARTS, TOLERANCE

HOUSE_SYSTEMS = [
    ("B", "Alcabitius"),
    ("R", "Regiomontanus"),
]

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


def calc_jd(chart: dict) -> float:
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart["ut_offset"]
    return swe.julday(chart["year"], chart["month"], chart["day"], hour_ut, swe.GREG_CAL)


def lon_to_sign(lon: float) -> tuple[str, float]:
    idx = int(lon / 30) % 12
    return SIGNS[idx], lon % 30


# ─────────────────────────────────────────────
# Test 1: Cusp longitudes in valid range
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
@pytest.mark.parametrize("hsys,hsys_name", HOUSE_SYSTEMS)
def test_cusp_longitude_range(chart_id, chart, hsys, hsys_name):
    """Tất cả house cusps phải trong [0°, 360°)."""
    jd = calc_jd(chart)
    cusps, ascmc = swe.houses(jd, chart["lat"], chart["lon"], hsys.encode())
    for i, cusp in enumerate(cusps, start=1):  # cusps[0]=H1 .. cusps[11]=H12
        assert 0 <= cusp < 360, (
            f"{hsys_name} house {i} out of range in {chart_id}: {cusp:.4f}°"
        )


# ─────────────────────────────────────────────
# Test 2: ASC và MC trong valid range
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
@pytest.mark.parametrize("hsys,hsys_name", HOUSE_SYSTEMS)
def test_asc_mc_range(chart_id, chart, hsys, hsys_name):
    """ASC và MC phải trong [0°, 360°)."""
    jd = calc_jd(chart)
    cusps, ascmc = swe.houses(jd, chart["lat"], chart["lon"], hsys.encode())
    asc, mc = ascmc[0], ascmc[1]
    assert 0 <= asc < 360, f"{hsys_name} ASC out of range in {chart_id}: {asc:.4f}°"
    assert 0 <= mc < 360, f"{hsys_name} MC out of range in {chart_id}: {mc:.4f}°"


# ─────────────────────────────────────────────
# Note: pyswisseph swe.houses() returns 0-indexed cusps (len=12)
# cusps[0] = H1 = ASC, cusps[9] = H10 = MC
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# Test 3: House 1 cusp == ASC
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
@pytest.mark.parametrize("hsys,hsys_name", HOUSE_SYSTEMS)
def test_house1_equals_asc(chart_id, chart, hsys, hsys_name):
    """House 1 cusp (cusps[0]) phải bằng ASC."""
    jd = calc_jd(chart)
    cusps, ascmc = swe.houses(jd, chart["lat"], chart["lon"], hsys.encode())
    asc = ascmc[0]
    house1 = cusps[0]  # 0-indexed: cusps[0] = H1
    assert abs(house1 - asc) < TOLERANCE, (
        f"{hsys_name} House 1 != ASC in {chart_id}: "
        f"H1={house1:.4f}°, ASC={asc:.4f}°"
    )


# ─────────────────────────────────────────────
# Test 4: House 10 cusp == MC
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
@pytest.mark.parametrize("hsys,hsys_name", HOUSE_SYSTEMS)
def test_house10_equals_mc(chart_id, chart, hsys, hsys_name):
    """House 10 cusp (cusps[9]) phải bằng MC."""
    jd = calc_jd(chart)
    cusps, ascmc = swe.houses(jd, chart["lat"], chart["lon"], hsys.encode())
    mc = ascmc[1]
    house10 = cusps[9]  # 0-indexed: cusps[9] = H10
    assert abs(house10 - mc) < TOLERANCE, (
        f"{hsys_name} House 10 != MC in {chart_id}: "
        f"H10={house10:.4f}°, MC={mc:.4f}°"
    )


# ─────────────────────────────────────────────
# Test 5: Opposite houses 180° apart (Alcabitius property)
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_alcabitius_opposite_houses(chart_id, chart):
    """Alcabitius: opposite house cusps phải cách nhau đúng 180°."""
    jd = calc_jd(chart)
    cusps, _ = swe.houses(jd, chart["lat"], chart["lon"], b"B")
    # 0-indexed pairs: (H1,H7)=(0,6), (H2,H8)=(1,7), ..., (H6,H12)=(5,11)
    pairs = [(0, 6), (1, 7), (2, 8), (3, 9), (4, 10), (5, 11)]
    for i1, i2 in pairs:
        diff = abs(cusps[i1] - cusps[i2])
        if diff > 180:
            diff = 360 - diff
        assert abs(diff - 180) < TOLERANCE, (
            f"Alcabitius H{i1+1}/H{i2+1} not 180° apart in {chart_id}: "
            f"H{i1+1}={cusps[i1]:.4f}°, H{i2+1}={cusps[i2]:.4f}°, diff={diff:.4f}°"
        )


# ─────────────────────────────────────────────
# Test 6: API output == direct pyswisseph
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
@pytest.mark.parametrize("hsys,hsys_name", HOUSE_SYSTEMS)
def test_api_matches_direct_swisseph(chart_id, chart, hsys, hsys_name):
    """
    API house cusps phải khớp với direct pyswisseph calls trong TOLERANCE.
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
        "hsys": hsys,
        "ut_offset": chart["ut_offset"],
        "include_outer": False,
    })

    assert resp.status_code == 200, f"API error: {resp.text}"
    data = resp.json()

    jd = calc_jd(chart)
    exp_cusps, exp_ascmc = swe.houses(jd, chart["lat"], chart["lon"], hsys.encode())

    api_houses = data["houses"]

    # Check ASC and MC
    assert abs(api_houses["asc"] - exp_ascmc[0]) < TOLERANCE, (
        f"{hsys_name} ASC mismatch in {chart_id}: "
        f"API={api_houses['asc']:.4f}°, direct={exp_ascmc[0]:.4f}°"
    )
    assert abs(api_houses["mc"] - exp_ascmc[1]) < TOLERANCE, (
        f"{hsys_name} MC mismatch in {chart_id}: "
        f"API={api_houses['mc']:.4f}°, direct={exp_ascmc[1]:.4f}°"
    )

    # Check all 12 cusps (0-indexed: cusps[0]=H1 .. cusps[11]=H12)
    api_cusps = api_houses["cusps"]
    for i in range(12):
        assert abs(api_cusps[i] - exp_cusps[i]) < TOLERANCE, (
            f"{hsys_name} House {i+1} mismatch in {chart_id}: "
            f"API={api_cusps[i]:.4f}°, direct={exp_cusps[i]:.4f}°"
        )


# ─────────────────────────────────────────────
# Report: Print table for Morinus comparison
# ─────────────────────────────────────────────

def test_print_morinus_comparison_table():
    """
    Không phải test thực sự — in ra bảng để so sánh tay với Morinus.
    Chạy: pytest -v -s tests/verification/test_houses.py::test_print_morinus_comparison_table
    """
    print("\n")
    print("=" * 75)
    print("HOUSE CUSPS — SO SÁNH VỚI MORINUS")
    print("Tolerance: ≤ 0.01° | Systems: Alcabitius (B), Regiomontanus (R)")
    print("=" * 75)

    for chart_id, chart in TEST_CHARTS.items():
        jd = calc_jd(chart)
        print(f"\n📍 {chart['desc']}")
        print(f"   {chart['year']}-{chart['month']:02d}-{chart['day']:02d} "
              f"{chart['hour']:02d}:{chart['minute']:02d} UT | "
              f"Lat {chart['lat']}° Lon {chart['lon']}°")

        for hsys, hsys_name in HOUSE_SYSTEMS:
            cusps, ascmc = swe.houses(jd, chart["lat"], chart["lon"], hsys.encode())
            asc, mc = ascmc[0], ascmc[1]

            print(f"\n   [{hsys_name}]")
            print(f"   {'House':<8} {'Longitude':>10}  {'Sign':>13}")
            print(f"   {'-'*8} {'-'*10}  {'-'*13}")

            sign, slon = lon_to_sign(asc)
            deg, mins = int(slon), int((slon % 1) * 60)
            print(f"   {'ASC':<8} {asc:>10.4f}°  {deg:>2}°{mins:02d}' {sign:<9}")

            sign, slon = lon_to_sign(mc)
            deg, mins = int(slon), int((slon % 1) * 60)
            print(f"   {'MC':<8} {mc:>10.4f}°  {deg:>2}°{mins:02d}' {sign:<9}")

            for i in range(12):  # cusps[0]=H1 .. cusps[11]=H12
                sign, slon = lon_to_sign(cusps[i])
                deg, mins = int(slon), int((slon % 1) * 60)
                print(f"   {'H'+str(i+1):<8} {cusps[i]:>10.4f}°  {deg:>2}°{mins:02d}' {sign:<9}")

    print("\n" + "=" * 75)
    print("▶ Mở Morinus → nhập từng chart → Tables → Houses → so sánh values")
    print("=" * 75)
    assert True
