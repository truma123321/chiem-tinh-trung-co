"""
Story 10 — Sect Verification

Test strategy:
  Layer 1: Planet sect constants (solar/lunar/common)
  Layer 2: Hemisphere detection (above/below horizon)
  Layer 3: Sign polarity (masculine/feminine)
  Layer 4: In-sect status (planet sect matches chart sect)
  Layer 5: Hayz (fully in sect — planet + hemisphere + sign)
  Layer 6: Mercury orient/occident → sect assignment
  Layer 7: Mutual exclusion and consistency across TEST_CHARTS
  Layer 8: API output == direct core call
  Layer 9: Print table for Morinus comparison

Chạy:
  cd backend && source .venv/bin/activate
  pytest ../tests/verification/test_sect.py -v
  pytest ../tests/verification/test_sect.py::test_print_sect_table -v -s
"""

import pytest
import swisseph as swe
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from tests.verification.conftest import TEST_CHARTS
from core.sect import (
    calc_sect, SOLAR_SECT, LUNAR_SECT,
    _above_horizon, _is_masculine_sign, _planet_sect,
)
from core.dignities import is_day_chart


def _build(chart):
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart.get("ut_offset", 0)
    jd = swe.julday(chart["year"], chart["month"], chart["day"], hour_ut, swe.GREG_CAL)
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    lons = {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, FLAGS)
        lons[pid] = r[0]
    hsys = b"B"
    cusps_raw, ascmc = swe.houses(jd, chart["lat"], chart["lon"], hsys)
    asc = ascmc[0]
    day = is_day_chart(lons[0], asc)
    return jd, lons, asc, day


# ─────────────────────────────────────────────
# Test 1: Solar / Lunar sect constants
# ─────────────────────────────────────────────

def test_solar_sect_planets():
    """Sun(0), Jupiter(5), Saturn(6) are diurnal."""
    assert 0 in SOLAR_SECT
    assert 5 in SOLAR_SECT
    assert 6 in SOLAR_SECT
    assert 1 not in SOLAR_SECT
    assert 3 not in SOLAR_SECT
    assert 4 not in SOLAR_SECT


def test_lunar_sect_planets():
    """Moon(1), Venus(3), Mars(4) are nocturnal."""
    assert 1 in LUNAR_SECT
    assert 3 in LUNAR_SECT
    assert 4 in LUNAR_SECT
    assert 0 not in LUNAR_SECT
    assert 5 not in LUNAR_SECT
    assert 6 not in LUNAR_SECT


def test_mercury_not_in_either_sect():
    """Mercury(2) is common — not in SOLAR_SECT or LUNAR_SECT."""
    assert 2 not in SOLAR_SECT
    assert 2 not in LUNAR_SECT


# ─────────────────────────────────────────────
# Test 2: _planet_sect() output
# ─────────────────────────────────────────────

def test_sun_is_diurnal():
    assert _planet_sect(0, 100.0, 100.0) == "diurnal"


def test_jupiter_is_diurnal():
    assert _planet_sect(5, 200.0, 100.0) == "diurnal"


def test_saturn_is_diurnal():
    assert _planet_sect(6, 300.0, 100.0) == "diurnal"


def test_moon_is_nocturnal():
    assert _planet_sect(1, 50.0, 100.0) == "nocturnal"


def test_venus_is_nocturnal():
    assert _planet_sect(3, 50.0, 100.0) == "nocturnal"


def test_mars_is_nocturnal():
    assert _planet_sect(4, 50.0, 100.0) == "nocturnal"


def test_mercury_oriental_is_diurnal():
    """Mercury ahead of Sun (elongation < 180°) → diurnal."""
    sun_lon = 100.0
    merc_lon = 150.0  # 50° ahead → oriental
    assert _planet_sect(2, merc_lon, sun_lon) == "diurnal"


def test_mercury_occidental_is_nocturnal():
    """Mercury behind Sun (elongation >= 180°) → nocturnal."""
    sun_lon = 100.0
    merc_lon = 50.0  # (50-100)%360=310° → occidental
    assert _planet_sect(2, merc_lon, sun_lon) == "nocturnal"


# ─────────────────────────────────────────────
# Test 3: Hemisphere detection
# ─────────────────────────────────────────────

def test_above_horizon_at_mc():
    """Planet at MC (ASC+270 mod 360) → above horizon."""
    asc = 0.0
    mc = 270.0   # MC is typically ~ASC+90 from Asc going up; wait...
    # Actually: above horizon = (planet_lon - asc) % 360 >= 180
    # At the exact MC for ASC=0: MC could be at 270° (nadir) or 90° depending on chart
    # Use simple case: ASC=0°, planet at 200° → (200-0)%360=200 >= 180 → above
    assert _above_horizon(200.0, 0.0)
    assert _above_horizon(180.0, 0.0)   # DSC — on the horizon, treated as above


def test_below_horizon():
    """Planet at IC-ish longitude → below horizon."""
    asc = 0.0
    assert not _above_horizon(90.0, 0.0)   # (90-0)%360=90 < 180
    assert not _above_horizon(0.0, 0.0)    # (0-0)%360=0  < 180 — at ASC, below


def test_above_horizon_wrap():
    """Horizon detection wraps correctly across 0°/360°."""
    asc = 350.0
    # planet at 180°: (180-350)%360 = (-170)%360 = 190 >= 180 → above
    assert _above_horizon(180.0, 350.0)
    # planet at 10°: (10-350)%360=20 < 180 → below
    assert not _above_horizon(10.0, 350.0)


# ─────────────────────────────────────────────
# Test 4: Sign polarity
# ─────────────────────────────────────────────

def test_aries_is_masculine():
    assert _is_masculine_sign(15.0)   # 15° Aries, sign_idx=0


def test_taurus_is_feminine():
    assert not _is_masculine_sign(45.0)  # 15° Taurus, sign_idx=1


def test_gemini_is_masculine():
    assert _is_masculine_sign(65.0)   # 5° Gemini, sign_idx=2


def test_cancer_is_feminine():
    assert not _is_masculine_sign(100.0)  # 10° Cancer, sign_idx=3


def test_leo_is_masculine():
    assert _is_masculine_sign(130.0)  # 10° Leo, sign_idx=4


def test_virgo_is_feminine():
    assert not _is_masculine_sign(170.0)  # 20° Virgo, sign_idx=5


def test_libra_is_masculine():
    assert _is_masculine_sign(195.0)  # 15° Libra, sign_idx=6


def test_scorpio_is_feminine():
    assert not _is_masculine_sign(225.0)  # 15° Scorpio, sign_idx=7


def test_sagittarius_is_masculine():
    assert _is_masculine_sign(255.0)  # 15° Sagittarius, sign_idx=8


def test_capricorn_is_feminine():
    assert not _is_masculine_sign(285.0)  # 15° Capricorn, sign_idx=9


def test_aquarius_is_masculine():
    assert _is_masculine_sign(315.0)  # 15° Aquarius, sign_idx=10


def test_pisces_is_feminine():
    assert not _is_masculine_sign(345.0)  # 15° Pisces, sign_idx=11


# ─────────────────────────────────────────────
# Test 5: calc_sect — in_sect day chart
# ─────────────────────────────────────────────

def test_solar_sect_in_sect_day():
    """Sun/Jupiter/Saturn → in_sect=True in a day chart."""
    # ASC=0, Sun at 200° → (200-0)%360=200 >= 180 → day chart
    asc = 0.0
    lons = {0: 200.0, 1: 50.0, 2: 150.0, 3: 80.0, 4: 310.0, 5: 230.0, 6: 250.0}
    result = calc_sect(lons, asc, day_chart=True)
    sun   = result.planet_sects[0]
    jup   = result.planet_sects[5]
    sat   = result.planet_sects[6]
    assert sun.in_sect
    assert jup.in_sect
    assert sat.in_sect


def test_lunar_sect_out_of_sect_day():
    """Moon/Venus/Mars → in_sect=False in a day chart."""
    asc = 0.0
    lons = {0: 200.0, 1: 50.0, 2: 150.0, 3: 80.0, 4: 310.0, 5: 230.0, 6: 250.0}
    result = calc_sect(lons, asc, day_chart=True)
    moon  = result.planet_sects[1]
    venus = result.planet_sects[3]
    mars  = result.planet_sects[4]
    assert not moon.in_sect
    assert not venus.in_sect
    assert not mars.in_sect


def test_lunar_sect_in_sect_night():
    """Moon/Venus/Mars → in_sect=True in a night chart."""
    asc = 0.0
    lons = {0: 50.0, 1: 200.0, 2: 150.0, 3: 80.0, 4: 310.0, 5: 230.0, 6: 250.0}
    result = calc_sect(lons, asc, day_chart=False)
    moon  = result.planet_sects[1]
    venus = result.planet_sects[3]
    mars  = result.planet_sects[4]
    assert moon.in_sect
    assert venus.in_sect
    assert mars.in_sect


# ─────────────────────────────────────────────
# Test 6: Hayz detection
# ─────────────────────────────────────────────

def test_jupiter_in_hayz_day():
    """Jupiter (diurnal) above horizon in masculine sign → hayz in day chart."""
    # ASC = 0, Jupiter at 255° (Sagittarius, masculine) → above horizon (255>=180)
    asc = 0.0
    lons = {0: 200.0, 1: 50.0, 2: 150.0, 3: 80.0, 4: 310.0, 5: 255.0, 6: 30.0}
    result = calc_sect(lons, asc, day_chart=True)
    jup = result.planet_sects[5]
    assert jup.sect == "diurnal"
    assert jup.above_horizon
    assert jup.sign_masculine   # Sagittarius (sign_idx=8, 8%2=0)
    assert jup.in_hayz


def test_mars_in_hayz_night():
    """Mars (nocturnal) below horizon in feminine sign → hayz in night chart."""
    # ASC = 0, Mars at 100° (Cancer, feminine) → below horizon (100 < 180)
    asc = 0.0
    lons = {0: 50.0, 1: 200.0, 2: 150.0, 3: 80.0, 4: 100.0, 5: 230.0, 6: 250.0}
    result = calc_sect(lons, asc, day_chart=False)
    mars = result.planet_sects[4]
    assert mars.sect == "nocturnal"
    assert not mars.above_horizon
    assert not mars.sign_masculine  # Cancer is feminine
    assert mars.in_hayz


def test_saturn_not_in_hayz_wrong_hemisphere():
    """Saturn (diurnal) below horizon → NOT in hayz even in day chart."""
    asc = 0.0
    # Saturn at 50° (Taurus, feminine, below horizon)
    lons = {0: 200.0, 1: 50.0, 2: 150.0, 3: 80.0, 4: 310.0, 5: 230.0, 6: 50.0}
    result = calc_sect(lons, asc, day_chart=True)
    sat = result.planet_sects[6]
    assert sat.sect == "diurnal"
    assert not sat.above_horizon   # 50° < 180° → below
    assert not sat.in_hayz


def test_venus_not_in_hayz_wrong_sign():
    """Venus (nocturnal) below horizon but in masculine sign → NOT in hayz."""
    asc = 0.0
    # Venus at 65° (Gemini, masculine, below horizon)
    lons = {0: 50.0, 1: 200.0, 2: 150.0, 3: 65.0, 4: 310.0, 5: 230.0, 6: 250.0}
    result = calc_sect(lons, asc, day_chart=False)
    venus = result.planet_sects[3]
    assert venus.sect == "nocturnal"
    assert not venus.above_horizon
    assert venus.sign_masculine    # Gemini = masculine
    assert not venus.in_hayz       # masculine sign breaks hayz for nocturnal planet


# ─────────────────────────────────────────────
# Test 7: Consistency across TEST_CHARTS
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_sect_output_has_7_planets(chart_id, chart):
    """calc_sect returns exactly 7 planet entries."""
    _, lons, asc, day = _build(chart)
    result = calc_sect(lons, asc, day)
    assert len(result.planet_sects) == 7, f"{chart_id}: expected 7 planets"


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_planet_ids_sequential(chart_id, chart):
    """Planet IDs must be 0-6 in order."""
    _, lons, asc, day = _build(chart)
    result = calc_sect(lons, asc, day)
    ids = [s.planet_id for s in result.planet_sects]
    assert ids == list(range(7)), f"{chart_id}: wrong planet id sequence {ids}"


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_sect_field_valid_values(chart_id, chart):
    """sect field must be one of 'diurnal' | 'nocturnal' | 'common'."""
    _, lons, asc, day = _build(chart)
    result = calc_sect(lons, asc, day)
    valid = {"diurnal", "nocturnal", "common"}
    for s in result.planet_sects:
        assert s.sect in valid, f"{chart_id} {s.planet_name}: invalid sect '{s.sect}'"


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_solar_sect_always_diurnal(chart_id, chart):
    """Sun, Jupiter, Saturn must always have sect='diurnal'."""
    _, lons, asc, day = _build(chart)
    result = calc_sect(lons, asc, day)
    for pid in [0, 5, 6]:
        s = result.planet_sects[pid]
        assert s.sect == "diurnal", (
            f"{chart_id} {s.planet_name}: expected diurnal, got {s.sect}"
        )


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_lunar_sect_always_nocturnal(chart_id, chart):
    """Moon, Venus, Mars must always have sect='nocturnal'."""
    _, lons, asc, day = _build(chart)
    result = calc_sect(lons, asc, day)
    for pid in [1, 3, 4]:
        s = result.planet_sects[pid]
        assert s.sect == "nocturnal", (
            f"{chart_id} {s.planet_name}: expected nocturnal, got {s.sect}"
        )


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_mercury_sect_is_diurnal_or_nocturnal(chart_id, chart):
    """Mercury must be 'diurnal' or 'nocturnal' (determined by orientation)."""
    _, lons, asc, day = _build(chart)
    result = calc_sect(lons, asc, day)
    merc = result.planet_sects[2]
    assert merc.sect in {"diurnal", "nocturnal"}, (
        f"{chart_id} Mercury: unexpected sect '{merc.sect}'"
    )


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_day_chart_field_matches_is_day_chart(chart_id, chart):
    """SectResult.day_chart must agree with is_day_chart()."""
    _, lons, asc, day = _build(chart)
    result = calc_sect(lons, asc, day)
    assert result.day_chart == day, (
        f"{chart_id}: SectResult.day_chart={result.day_chart} != is_day_chart={day}"
    )


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_hayz_subset_of_in_sect(chart_id, chart):
    """in_hayz=True implies in_sect=True."""
    _, lons, asc, day = _build(chart)
    result = calc_sect(lons, asc, day)
    for s in result.planet_sects:
        if s.in_hayz:
            assert s.in_sect, (
                f"{chart_id} {s.planet_name}: in_hayz=True but in_sect=False"
            )


# ─────────────────────────────────────────────
# Test 8: API output == direct call
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_api_sect_match_direct(chart_id, chart):
    """API sect output must match direct calc_sect() call."""
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
    api = resp.json()["sect"]

    _, lons, asc, day = _build(chart)
    direct = calc_sect(lons, asc, day)

    assert api["day_chart"] == direct.day_chart, f"{chart_id}: day_chart mismatch"
    assert len(api["planet_sects"]) == len(direct.planet_sects)

    for api_s, dir_s in zip(api["planet_sects"], direct.planet_sects):
        assert api_s["planet_id"] == dir_s.planet_id
        assert api_s["sect"] == dir_s.sect, (
            f"{chart_id} {dir_s.planet_name}: sect mismatch"
        )
        assert api_s["in_sect"] == dir_s.in_sect
        assert api_s["above_horizon"] == dir_s.above_horizon
        assert api_s["sign_masculine"] == dir_s.sign_masculine
        assert api_s["in_hayz"] == dir_s.in_hayz


# ─────────────────────────────────────────────
# Report: Print table for Morinus comparison
# ─────────────────────────────────────────────

def test_print_sect_table():
    """
    In ra bảng sect để so sánh với Morinus.
    Morinus: Tables → Planets → check sect/hayz columns
    """
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    EPHE_PATH = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../../tools/morinus/SWEP/Ephem")
    )
    swe.set_ephe_path(EPHE_PATH)

    print("\n")
    print("=" * 80)
    print("SECT (HAYRESIS) — SO SANH VOI MORINUS")
    print("Diurnal: Sun, Jupiter, Saturn | Nocturnal: Moon, Venus, Mars | Mercury: Common")
    print("=" * 80)

    for chart_id, chart in TEST_CHARTS.items():
        _, lons, asc, day = _build(chart)
        result = calc_sect(lons, asc, day)

        chart_type = "DAY" if result.day_chart else "NIGHT"
        print(f"\n  {chart['desc']} [{chart_type} CHART]")
        print(f"  {'Planet':<10} {'Sect':<10} {'InSect':<8} {'AboveHz':<9} {'MascSign':<10} {'Hayz'}")
        print(f"  {'-'*10} {'-'*10} {'-'*8} {'-'*9} {'-'*10} {'-'*5}")
        for s in result.planet_sects:
            insect = "YES" if s.in_sect else "no"
            above  = "YES" if s.above_horizon else "no"
            masc   = "YES" if s.sign_masculine else "no"
            hayz   = "HAYZ" if s.in_hayz else ""
            print(f"  {s.planet_name:<10} {s.sect:<10} {insect:<8} {above:<9} {masc:<10} {hayz}")

    print("\n" + "=" * 80)
    print("▶ Morinus → Tables → Planets → check sect/hayz status")
    print("=" * 80)
    assert True
