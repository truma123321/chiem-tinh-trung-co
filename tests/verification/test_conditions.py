"""
Story 9 — Planetary Conditions Verification

Test strategy:
  Layer 1: Cazimi detection (within 0°17')
  Layer 2: Combust / Under Beams thresholds
  Layer 3: Mutual exclusion (cazimi / combust / beams / free)
  Layer 4: Oriental / occidental consistency
  Layer 5: Void of course Moon logic
  Layer 6: API output == direct core call
  Layer 7: Print table for Morinus comparison

Để chạy:
  cd backend && source .venv/bin/activate
  pytest ../tests/verification/test_conditions.py -v
  pytest ../tests/verification/test_conditions.py::test_print_conditions_table -v -s
"""

import pytest
import swisseph as swe
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from tests.verification.conftest import TEST_CHARTS
from core.conditions import (
    calc_conditions, CAZIMI_ORB, COMBUST_ORB, BEAMS_ORB,
)


def _build(chart):
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart.get("ut_offset", 0)
    jd = swe.julday(chart["year"], chart["month"], chart["day"], hour_ut, swe.GREG_CAL)
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    lons, spds = {}, {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, FLAGS)
        lons[pid], spds[pid] = r[0], r[3]
    return jd, lons, spds


# ─────────────────────────────────────────────
# Test 1: Cazimi detection
# ─────────────────────────────────────────────

def test_cazimi_planet_within_17min():
    """Planet within 0°17' of Sun is cazimi."""
    sun_lon = 100.0
    # Moon at 0°10' from Sun
    lons = {0: sun_lon, 1: sun_lon + (10/60), 2: 200.0, 3: 250.0, 4: 300.0, 5: 50.0, 6: 30.0}
    spds = {pid: 1.0 for pid in lons}
    result = calc_conditions(lons, spds)
    moon_cond = result.planet_conditions[0]  # Moon is index 0
    assert moon_cond.cazimi, f"Moon at 10' from Sun should be cazimi, dist={moon_cond.sun_distance:.4f}°"
    assert not moon_cond.combust
    assert not moon_cond.under_beams


def test_not_cazimi_at_18min():
    """Planet at 0°18' from Sun is NOT cazimi (just outside threshold)."""
    sun_lon = 100.0
    lons = {0: sun_lon, 1: sun_lon + (18/60), 2: 200.0, 3: 250.0, 4: 300.0, 5: 50.0, 6: 30.0}
    spds = {pid: 1.0 for pid in lons}
    result = calc_conditions(lons, spds)
    moon_cond = result.planet_conditions[0]
    assert not moon_cond.cazimi


def test_cazimi_threshold():
    """CAZIMI_ORB must be 0°17' = 17/60°."""
    assert abs(CAZIMI_ORB - 17/60) < 0.0001


# ─────────────────────────────────────────────
# Test 2: Combust / Beams thresholds
# ─────────────────────────────────────────────

def test_combust_at_5deg():
    """Planet 5° from Sun is combust (not cazimi, within 8°)."""
    sun_lon = 100.0
    lons = {0: sun_lon, 1: sun_lon + 5.0, 2: 200.0, 3: 250.0, 4: 300.0, 5: 50.0, 6: 30.0}
    spds = {pid: 1.0 for pid in lons}
    result = calc_conditions(lons, spds)
    moon_cond = result.planet_conditions[0]
    assert moon_cond.combust
    assert not moon_cond.cazimi
    assert not moon_cond.under_beams
    assert not moon_cond.free_from_beams


def test_under_beams_at_12deg():
    """Planet 12° from Sun is under the beams (not combust)."""
    sun_lon = 100.0
    lons = {0: sun_lon, 1: sun_lon + 12.0, 2: 200.0, 3: 250.0, 4: 300.0, 5: 50.0, 6: 30.0}
    spds = {pid: 1.0 for pid in lons}
    result = calc_conditions(lons, spds)
    moon_cond = result.planet_conditions[0]
    assert moon_cond.under_beams
    assert not moon_cond.combust
    assert not moon_cond.cazimi
    assert not moon_cond.free_from_beams


def test_free_at_20deg():
    """Planet 20° from Sun is free from beams."""
    sun_lon = 100.0
    lons = {0: sun_lon, 1: sun_lon + 20.0, 2: 200.0, 3: 250.0, 4: 300.0, 5: 50.0, 6: 30.0}
    spds = {pid: 1.0 for pid in lons}
    result = calc_conditions(lons, spds)
    moon_cond = result.planet_conditions[0]
    assert moon_cond.free_from_beams
    assert not moon_cond.combust
    assert not moon_cond.cazimi
    assert not moon_cond.under_beams


# ─────────────────────────────────────────────
# Test 3: Mutual exclusion
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_conditions_mutually_exclusive(chart_id, chart):
    """Exactly one of cazimi/combust/under_beams/free must be True for each planet."""
    _, lons, spds = _build(chart)
    result = calc_conditions(lons, spds)
    for c in result.planet_conditions:
        flags = [c.cazimi, c.combust, c.under_beams, c.free_from_beams]
        assert sum(flags) == 1, (
            f"{chart_id} — {c.planet_name}: "
            f"cazimi={c.cazimi} combust={c.combust} beams={c.under_beams} free={c.free_from_beams}"
        )


# ─────────────────────────────────────────────
# Test 4: Oriental / occidental mutual exclusion
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_oriental_occidental_exclusive(chart_id, chart):
    """Exactly one of oriental/occidental must be True."""
    _, lons, spds = _build(chart)
    result = calc_conditions(lons, spds)
    for c in result.planet_conditions:
        assert c.oriental != c.occidental, (
            f"{chart_id} — {c.planet_name}: oriental={c.oriental}, occidental={c.occidental}"
        )


def test_oriental_definition():
    """Oriental: elongation < 180°."""
    sun_lon = 100.0
    # Planet ahead of Sun in zodiac (oriental): planet at 150° → elongation = 50°
    lons = {0: sun_lon, 1: 150.0, 2: 200.0, 3: 250.0, 4: 300.0, 5: 50.0, 6: 30.0}
    spds = {pid: 1.0 for pid in lons}
    result = calc_conditions(lons, spds)
    moon = result.planet_conditions[0]
    assert moon.oriental
    assert not moon.occidental
    assert abs(moon.elongation - 50.0) < 0.01


def test_occidental_definition():
    """Occidental: elongation >= 180°."""
    sun_lon = 100.0
    # Planet behind Sun in zodiac: planet at 50° → elongation = (50-100)%360 = 310°
    lons = {0: sun_lon, 1: 50.0, 2: 200.0, 3: 250.0, 4: 300.0, 5: 320.0, 6: 30.0}
    spds = {pid: 1.0 for pid in lons}
    result = calc_conditions(lons, spds)
    moon = result.planet_conditions[0]
    assert moon.occidental
    assert not moon.oriental
    assert abs(moon.elongation - 310.0) < 0.01


# ─────────────────────────────────────────────
# Test 5: Sun distance matches arc
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_sun_distance_in_range(chart_id, chart):
    """sun_distance must be in [0°, 180°]."""
    _, lons, spds = _build(chart)
    result = calc_conditions(lons, spds)
    for c in result.planet_conditions:
        assert 0 <= c.sun_distance <= 180, (
            f"{chart_id} — {c.planet_name}: sun_distance={c.sun_distance}"
        )


# ─────────────────────────────────────────────
# Test 6: VOC Moon — forced test
# ─────────────────────────────────────────────

def test_voc_moon_no_aspects():
    """Moon with no aspects within combined orb → VOC."""
    # Moon at 29° Aries (almost leaving sign), all planets far away
    moon_lon = 29.5   # 29°30' Aries, 0.5° left in sign
    sun_lon  = 200.0  # Leo area — far from Moon
    lons = {0: sun_lon, 1: moon_lon, 2: 210.0, 3: 220.0, 4: 230.0, 5: 240.0, 6: 250.0}
    spds = {pid: 0.1 for pid in lons}
    spds[1] = 13.0   # Moon fast
    result = calc_conditions(lons, spds)
    assert result.moon.void_of_course, "Moon with 0.5° left and all planets far → VOC"


def test_not_voc_moon_with_imminent_aspect():
    """Moon about to perfect a conjunction within remaining sign degrees → NOT VOC."""
    # Moon at 25° Aries, Mercury at 28° Aries — conjunction within 3°, both in Aries
    moon_lon    = 25.0
    mercury_lon = 28.0
    sun_lon     = 200.0
    lons = {0: sun_lon, 1: moon_lon, 2: mercury_lon, 3: 220.0, 4: 230.0, 5: 240.0, 6: 250.0}
    spds = {pid: 0.1 for pid in lons}
    spds[1] = 13.0   # Moon fast
    result = calc_conditions(lons, spds)
    assert not result.moon.void_of_course, (
        "Moon 3° from Mercury conjunction in same sign → NOT VOC"
    )
    assert result.moon.next_aspect_planet == 2  # Mercury


# ─────────────────────────────────────────────
# Test 7: API output == direct call
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_api_conditions_match_direct(chart_id, chart):
    """API conditions output must match direct calc_conditions() call."""
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
    api = resp.json()["conditions"]

    _, lons, spds = _build(chart)
    direct = calc_conditions(lons, spds)

    assert api["moon"]["void_of_course"] == direct.moon.void_of_course, (
        f"{chart_id}: VOC mismatch"
    )
    for api_c, dir_c in zip(api["planet_conditions"], direct.planet_conditions):
        assert api_c["planet_id"] == dir_c.planet_id
        assert api_c["cazimi"] == dir_c.cazimi
        assert api_c["combust"] == dir_c.combust
        assert api_c["under_beams"] == dir_c.under_beams
        assert api_c["oriental"] == dir_c.oriental
        assert abs(api_c["sun_distance"] - dir_c.sun_distance) < 0.001, (
            f"{chart_id} — {dir_c.planet_name}: sun_distance mismatch"
        )


# ─────────────────────────────────────────────
# Report: Print table for Morinus comparison
# ─────────────────────────────────────────────

def test_print_conditions_table():
    """
    In ra bảng conditions để so sánh với Morinus.
    Morinus: Tables → Misc → check combust/oriental entries
    """
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    EPHE_PATH = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../../tools/morinus/SWEP/Ephem")
    )
    swe.set_ephe_path(EPHE_PATH)

    print("\n")
    print("=" * 80)
    print("PLANETARY CONDITIONS — SO SÁNH VỚI MORINUS")
    print(f"Thresholds: Cazimi=0°17', Combust=8°, Beams=15°")
    print("=" * 80)

    for chart_id, chart in TEST_CHARTS.items():
        _, lons, spds = _build(chart)
        result = calc_conditions(lons, spds)

        print(f"\n📍 {chart['desc']}")
        print(f"   {'Planet':<10} {'☉Dist':>7}  {'Solar':>10}  {'Dir':>4}  {'Elong':>7}")
        print(f"   {'-'*10} {'-'*7}  {'-'*10}  {'-'*4}  {'-'*7}")
        for c in result.planet_conditions:
            solar = ("CAZIMI" if c.cazimi else
                     "COMBUST" if c.combust else
                     "BEAMS"   if c.under_beams else
                     "free")
            dir_ = "Ori" if c.oriental else "Occ"
            print(f"   {c.planet_name:<10} {c.sun_distance:>6.2f}°  {solar:>10}  {dir_:>4}  {c.elongation:>7.2f}°")

        voc_str = "VOC" if result.moon.void_of_course else "not VOC"
        if not result.moon.void_of_course and result.moon.next_aspect_planet_name:
            asp_names = ["Cnj","Sxt","Sqr","Tri","Opp"]
            nxt = (f" → next: {result.moon.next_aspect_planet_name} "
                   f"{asp_names[result.moon.next_aspect_type]} "
                   f"orb={result.moon.next_aspect_orb:.2f}°")
        else:
            nxt = ""
        print(f"\n   Moon: {voc_str}{nxt}")

    print("\n" + "=" * 80)
    print("▶ Morinus → Tables → Misc → check oriental/combust columns")
    print("=" * 80)
    assert True
