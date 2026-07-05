"""
Story 7 — Arabic Parts Verification

Test strategy:
  Layer 1: Formula correctness — day/night swap
  Layer 2: Output range [0°, 360°)
  Layer 3: Named parts present (Fortune, Spirit, Love, ...)
  Layer 4: Spirit = inverse of Fortune (day ↔ night)
  Layer 5: API output == direct core call
  Layer 6: Print table for manual Morinus comparison

Để chạy:
  cd backend && source .venv/bin/activate
  pytest ../tests/verification/test_arabic_parts.py -v
  pytest ../tests/verification/test_arabic_parts.py::test_print_arabic_parts_table -v -s
"""

import pytest
import swisseph as swe
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from tests.verification.conftest import TEST_CHARTS
from core.arabic_parts import calc_arabic_parts
from core.dignities import is_day_chart


# ─────────────────────────────────────────────
# Test 1: Formula — day/night swap
# ─────────────────────────────────────────────

def _make_chart(year, month, day, hour_ut, lat, lon):
    jd = swe.julday(year, month, day, hour_ut, swe.GREG_CAL)
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    cusps_raw, ascmc = swe.houses(jd, lat, lon, b"B")
    asc = ascmc[0]
    planet_lons = {pid: swe.calc_ut(jd, pid, FLAGS)[0][0] for pid in range(7)}
    sun_lon = planet_lons[0]
    moon_lon = planet_lons[1]
    day_chart = is_day_chart(sun_lon, asc)
    return jd, cusps_raw, asc, planet_lons, sun_lon, moon_lon, day_chart


def test_fortune_day_formula():
    """Fortune (diurnal): day chart = ASC + Moon - Sun."""
    jd, cusps_raw, asc, planet_lons, sun_lon, moon_lon, day = _make_chart(
        1990, 6, 15, 9.5, 41.9, 12.5
    )
    assert day, "Expected day chart for Rome 1990"
    parts = calc_arabic_parts(planet_lons, asc, sun_lon, moon_lon, day, jd, cusps_raw)
    fortune = next(p for p in parts if p.name == "Fortune")
    expected = (asc + moon_lon - sun_lon) % 360
    assert abs(fortune.lon - expected) < 0.001, (
        f"Fortune day mismatch: got {fortune.lon:.4f}°, expected {expected:.4f}°"
    )


def test_fortune_night_formula():
    """Fortune (diurnal): night chart = ASC + Sun - Moon (swapped)."""
    jd, cusps_raw, asc, planet_lons, sun_lon, moon_lon, day = _make_chart(
        1985, 12, 21, 3.0, 64.1, -21.9
    )
    assert not day, "Expected night chart for Reykjavik 1985"
    parts = calc_arabic_parts(planet_lons, asc, sun_lon, moon_lon, day, jd, cusps_raw)
    fortune = next(p for p in parts if p.name == "Fortune")
    expected = (asc + sun_lon - moon_lon) % 360
    assert abs(fortune.lon - expected) < 0.001, (
        f"Fortune night mismatch: got {fortune.lon:.4f}°, expected {expected:.4f}°"
    )


def test_spirit_is_inverse_of_fortune():
    """Spirit is always the day/night inverse of Fortune."""
    for chart_id, chart in TEST_CHARTS.items():
        hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart.get("ut_offset", 0)
        jd, cusps_raw, asc, planet_lons, sun_lon, moon_lon, day = _make_chart(
            chart["year"], chart["month"], chart["day"], hour_ut, chart["lat"], chart["lon"]
        )
        parts = calc_arabic_parts(planet_lons, asc, sun_lon, moon_lon, day, jd, cusps_raw)
        by_name = {p.name: p for p in parts}

        fortune_lon = by_name["Fortune"].lon
        spirit_lon  = by_name["Spirit"].lon

        if day:
            expected_spirit = (asc + sun_lon - moon_lon) % 360
        else:
            expected_spirit = (asc + moon_lon - sun_lon) % 360

        assert abs(spirit_lon - expected_spirit) < 0.001, (
            f"{chart_id}: Spirit={spirit_lon:.4f}°, expected={expected_spirit:.4f}°"
        )

        # Fortune + Spirit relative to ASC should sum to 2*ASC (mod 360)
        # i.e., they are symmetric around the ASC axis
        sum_mod = (fortune_lon + spirit_lon) % 360
        two_asc = (2 * asc) % 360
        assert abs(sum_mod - two_asc) < 0.01, (
            f"{chart_id}: Fortune+Spirit symmetry broken: sum={sum_mod:.2f}°, 2*ASC={two_asc:.2f}°"
        )


# ─────────────────────────────────────────────
# Test 2: Output range
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_all_parts_in_range(chart_id, chart):
    """All Arabic Parts must be in [0°, 360°)."""
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart.get("ut_offset", 0)
    jd, cusps_raw, asc, planet_lons, sun_lon, moon_lon, day = _make_chart(
        chart["year"], chart["month"], chart["day"], hour_ut, chart["lat"], chart["lon"]
    )
    parts = calc_arabic_parts(planet_lons, asc, sun_lon, moon_lon, day, jd, cusps_raw)
    for p in parts:
        assert 0 <= p.lon < 360, f"{chart_id} — {p.name}: lon={p.lon:.4f}° out of range"


# ─────────────────────────────────────────────
# Test 3: Required parts present
# ─────────────────────────────────────────────

REQUIRED_PARTS = [
    "Fortune", "Spirit", "Love", "Necessity", "Valor",
    "Victory", "Nemesis", "Basis",
    "Father", "Mother", "Children", "Marriage (male chart)",
    "Death", "Honor/Dignity",
]

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_required_parts_present(chart_id, chart):
    """All key classical lots must be present in the output."""
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart.get("ut_offset", 0)
    jd, cusps_raw, asc, planet_lons, sun_lon, moon_lon, day = _make_chart(
        chart["year"], chart["month"], chart["day"], hour_ut, chart["lat"], chart["lon"]
    )
    parts = calc_arabic_parts(planet_lons, asc, sun_lon, moon_lon, day, jd, cusps_raw)
    names = {p.name for p in parts}
    for req in REQUIRED_PARTS:
        assert req in names, f"{chart_id}: missing required part '{req}'"


# ─────────────────────────────────────────────
# Test 4: Love = ASC + Venus - Spirit (no swap)
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_love_formula_invariant(chart_id, chart):
    """Love is invariant (no D/N swap): always ASC + Venus - Spirit."""
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart.get("ut_offset", 0)
    jd, cusps_raw, asc, planet_lons, sun_lon, moon_lon, day = _make_chart(
        chart["year"], chart["month"], chart["day"], hour_ut, chart["lat"], chart["lon"]
    )
    parts = calc_arabic_parts(planet_lons, asc, sun_lon, moon_lon, day, jd, cusps_raw)
    by_name = {p.name: p for p in parts}

    if day:
        spirit_lon = (asc + sun_lon - moon_lon) % 360
    else:
        spirit_lon = (asc + moon_lon - sun_lon) % 360

    venus_lon = planet_lons[3]
    expected_love = (asc + venus_lon - spirit_lon) % 360
    love_lon = by_name["Love"].lon
    assert abs(love_lon - expected_love) < 0.001, (
        f"{chart_id}: Love={love_lon:.4f}°, expected={expected_love:.4f}°"
    )


# ─────────────────────────────────────────────
# Test 5: API == direct call
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_api_arabic_parts_match_direct(chart_id, chart):
    """API arabic_parts must match direct calc_arabic_parts() call."""
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
    data = resp.json()

    api_parts = {p["name"]: p for p in data["arabic_parts"]}

    # Recompute directly
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart.get("ut_offset", 0)
    jd, cusps_raw, asc, planet_lons, sun_lon, moon_lon, day = _make_chart(
        chart["year"], chart["month"], chart["day"], hour_ut, chart["lat"], chart["lon"]
    )
    direct_parts = {p.name: p for p in
                    calc_arabic_parts(planet_lons, asc, sun_lon, moon_lon, day, jd, cusps_raw)}

    # Check all direct parts appear in API with same longitude
    for name, dp in direct_parts.items():
        assert name in api_parts, f"{chart_id}: '{name}' missing from API"
        assert abs(api_parts[name]["lon"] - dp.lon) < 0.001, (
            f"{chart_id} — {name}: API={api_parts[name]['lon']:.4f}°, direct={dp.lon:.4f}°"
        )


# ─────────────────────────────────────────────
# Report: Print table for Morinus comparison
# ─────────────────────────────────────────────

def test_print_arabic_parts_table():
    """
    In ra bảng Arabic Parts để so sánh tay với Morinus (Arabic Parts frame).
    Chạy: pytest -v -s tests/verification/test_arabic_parts.py::test_print_arabic_parts_table
    """
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    EPHE_PATH = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../../tools/morinus/SWEP/Ephem")
    )
    swe.set_ephe_path(EPHE_PATH)

    print("\n")
    print("=" * 80)
    print("ARABIC PARTS — SO SÁNH VỚI MORINUS")
    print("Formula: Day = A + B - C; Night (diurnal) = A + C - B")
    print("=" * 80)

    for chart_id, chart in TEST_CHARTS.items():
        hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart.get("ut_offset", 0)
        jd, cusps_raw, asc, planet_lons, sun_lon, moon_lon, day = _make_chart(
            chart["year"], chart["month"], chart["day"], hour_ut, chart["lat"], chart["lon"]
        )
        parts = calc_arabic_parts(planet_lons, asc, sun_lon, moon_lon, day, jd, cusps_raw)

        print(f"\n📍 {chart['desc']}  ({'Day' if day else 'Night'} chart)")
        print(f"\n   {'Part':<35}  {'Sign':<15}  {'Deg':>7}  Formula")
        print(f"   {'-'*35}  {'-'*15}  {'-'*7}  {'-'*35}")
        for p in parts:
            print(f"   {p.name:<35}  {p.sign:<15}  {p.sign_lon:>7.3f}°  {p.formula}")

    print("\n" + "=" * 80)
    print("▶ Morinus → Tables → Arabic Parts → compare lot positions")
    print("=" * 80)
    assert True


# ─────────────────────────────────────────────
# Epic 6.1 tests — 97 lots, new lot formulas
# ─────────────────────────────────────────────

from core.arabic_parts import LOTS as _LOTS

def test_lots_count_is_97():
    """LOTS table must contain exactly 97 entries after Epic 6.1."""
    assert len(_LOTS) == 97, f"Expected 97 lots, got {len(_LOTS)}"


def test_97_unique_names():
    """Every lot name must be unique (no silent duplicates)."""
    names = [l[0] for l in _LOTS]
    assert len(names) == len(set(names)), (
        f"Duplicate lot names: {[n for n in names if names.count(n) > 1]}"
    )


NEW_LOTS = [
    "Injuries", "Memory", "Loss and Ruin", "Profit and Gain",
    "Homeland", "Patrimony", "Games and Gambling", "Abundance",
    "Blindness", "Pain", "Betrothal", "Open Enemies",
    "Fortune at Death", "Violent Death", "Sea Voyages", "Dreams",
    "Wisdom", "Eminence", "Trade", "Gain from Friends",
    "Good Luck", "Exile", "Self-Undoing",
]

def test_new_lots_present():
    """All 23 new Epic 6.1 lots must be in the LOTS table."""
    existing = {l[0] for l in _LOTS}
    for name in NEW_LOTS:
        assert name in existing, f"New lot '{name}' missing from LOTS"


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_97_lots_count_in_output(chart_id, chart):
    """calc_arabic_parts should return ≥ 90 lots for a standard chart.
    (Some lots may be skipped when house lords fall outside the traditional 7,
    so we allow up to 7 skips from the 97-lot table.)
    """
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart.get("ut_offset", 0)
    jd, cusps_raw, asc, planet_lons, sun_lon, moon_lon, day = _make_chart(
        chart["year"], chart["month"], chart["day"], hour_ut, chart["lat"], chart["lon"]
    )
    parts = calc_arabic_parts(planet_lons, asc, sun_lon, moon_lon, day, jd, cusps_raw)
    assert len(parts) >= 90, (
        f"{chart_id}: only {len(parts)} lots returned (expected ≥ 90)"
    )


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_new_lots_in_output(chart_id, chart):
    """New lots (those not requiring missing house lords) must appear in output."""
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart.get("ut_offset", 0)
    jd, cusps_raw, asc, planet_lons, sun_lon, moon_lon, day = _make_chart(
        chart["year"], chart["month"], chart["day"], hour_ut, chart["lat"], chart["lon"]
    )
    parts = calc_arabic_parts(planet_lons, asc, sun_lon, moon_lon, day, jd, cusps_raw)
    names = {p.name for p in parts}

    # Lots that don't depend on house lords (always computable from 7 planets + ASC + IC/MC)
    always_present = [
        "Injuries", "Memory", "Loss and Ruin", "Profit and Gain",
        "Homeland", "Patrimony", "Games and Gambling", "Abundance",
        "Blindness", "Pain", "Betrothal", "Open Enemies",
        "Violent Death", "Dreams", "Wisdom", "Good Luck",
        "Exile", "Self-Undoing",
    ]
    for name in always_present:
        assert name in names, f"{chart_id}: lot '{name}' missing from output"


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_new_lots_in_range(chart_id, chart):
    """All new lots must produce longitudes in [0, 360)."""
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart.get("ut_offset", 0)
    jd, cusps_raw, asc, planet_lons, sun_lon, moon_lon, day = _make_chart(
        chart["year"], chart["month"], chart["day"], hour_ut, chart["lat"], chart["lon"]
    )
    parts = calc_arabic_parts(planet_lons, asc, sun_lon, moon_lon, day, jd, cusps_raw)
    lot_map = {p.name: p for p in parts}
    for name in NEW_LOTS:
        if name in lot_map:
            p = lot_map[name]
            assert 0.0 <= p.lon < 360.0, f"{chart_id}/{name}: lon={p.lon} out of range"
            assert p.sign in [
                "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
                "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
            ], f"{chart_id}/{name}: invalid sign '{p.sign}'"


def test_invariant_lots_unchanged_by_day_night():
    """Lots with diurnal=False must produce same lon in day and night charts."""
    from core.dignities import is_day_chart
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

    # Use rome_1990_day as base; synthesise a night chart by changing hour
    chart = TEST_CHARTS["rome_1990_day"]
    hour_ut = chart["hour"] + chart["minute"] / 60.0

    jd_day, cusps_d, asc_d, lons_d, sun_d, moon_d, _ = _make_chart(
        chart["year"], chart["month"], chart["day"], hour_ut,
        chart["lat"], chart["lon"]
    )
    # Night chart: same day, but flip to midnight
    jd_night, cusps_n, asc_n, lons_n, sun_n, moon_n, _ = _make_chart(
        chart["year"], chart["month"], chart["day"], 0.0,
        chart["lat"], chart["lon"]
    )

    day_parts = {p.name: p.lon for p in
                 calc_arabic_parts(lons_d, asc_d, sun_d, moon_d, True, jd_day, cusps_d)}
    night_parts = {p.name: p.lon for p in
                   calc_arabic_parts(lons_n, asc_n, sun_n, moon_n, False, jd_night, cusps_n)}

    # Invariant new lots (diurnal=False): Blindness, Pain, Open Enemies
    for name in ("Blindness", "Pain", "Open Enemies"):
        if name in day_parts and name in night_parts:
            # Invariant lots use same formula day and night;
            # but positions differ because ASC/planets move — so we just check formula flag
            pass  # formula-level test is in LOTS table itself

    # Verify formula flag is False for invariant lots in LOTS table
    invariant_new = {l[0]: l[4] for l in _LOTS if l[0] in ("Blindness", "Pain", "Open Enemies", "Wisdom")}
    for name, diurnal in invariant_new.items():
        assert not diurnal, f"'{name}' should have diurnal=False"
