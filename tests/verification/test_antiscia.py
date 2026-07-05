"""
Story 12 — Antiscia & Contra-antiscia Verification

Test strategy:
  Layer 1: Antiscion formula matches Lilly's table (Aries↔Virgo, Taurus↔Leo …)
  Layer 2: Contra-antiscion formula (Aries↔Pisces, Taurus↔Aquarius …)
  Layer 3: Shadow points for each sign — correctness and symmetry
  Layer 4: Antiscion aspect detection (within orb)
  Layer 5: Contra-antiscion aspect detection (within orb)
  Layer 6: No false positives beyond orb
  Layer 7: No duplicate pairs
  Layer 8: Result sorted by orb
  Layer 9: Consistency across TEST_CHARTS
  Layer 10: API output == direct core call
  Layer 11: Print table for Morinus comparison

Chay:
  cd backend && source .venv/bin/activate
  pytest ../tests/verification/test_antiscia.py -v
  pytest ../tests/verification/test_antiscia.py::test_print_antiscia_table -v -s
"""

import pytest
import swisseph as swe
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from tests.verification.conftest import TEST_CHARTS
from core.antiscia import (
    calc_antiscia, ANTISCIA_ORB, ANTISCIA_ASPECT_ORB, ANTISCIA_ASPECTS,
    _arc, _antiscion, _contra,
)


def _build(chart):
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart.get("ut_offset", 0)
    jd = swe.julday(chart["year"], chart["month"], chart["day"], hour_ut, swe.GREG_CAL)
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    lons = {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, FLAGS)
        lons[pid] = r[0]
    return jd, lons


# ─────────────────────────────────────────────
# Test 1: Antiscion formula — Lilly's sign pairs
# ─────────────────────────────────────────────

# (planet_lon, expected_antiscion_lon, description)
ANTISCION_PAIRS = [
    (1.0,   179.0, "Aries 1° → Virgo 29°"),
    (31.0,  149.0, "Taurus 1° → Leo 29°"),
    (61.0,  119.0, "Gemini 1° → Cancer 29°"),
    (91.0,   89.0, "Cancer 1° → Gemini 29°"),
    (121.0,  59.0, "Leo 1° → Taurus 29°"),
    (151.0,  29.0, "Virgo 1° → Aries 29°"),
    (181.0, 359.0, "Libra 1° → Pisces 29°"),
    (211.0, 329.0, "Scorpio 1° → Aquarius 29°"),
    (241.0, 299.0, "Sagittarius 1° → Capricorn 29°"),
    (271.0, 269.0, "Capricorn 1° → Sagittarius 29°"),
    (301.0, 239.0, "Aquarius 1° → Scorpio 29°"),
    (331.0, 209.0, "Pisces 1° → Libra 29°"),
]

@pytest.mark.parametrize("lon,expected,desc", ANTISCION_PAIRS)
def test_antiscion_formula(lon, expected, desc):
    result = _antiscion(lon)
    assert abs(result - expected) < 0.001, (
        f"{desc}: got {result:.4f}°, expected {expected}°"
    )


# ─────────────────────────────────────────────
# Test 2: Contra-antiscion formula
# ─────────────────────────────────────────────

CONTRA_PAIRS = [
    (1.0,   359.0, "Aries 1° → Pisces 29°"),
    (31.0,  329.0, "Taurus 1° → Aquarius 29°"),
    (61.0,  299.0, "Gemini 1° → Capricorn 29°"),
    (91.0,  269.0, "Cancer 1° → Sagittarius 29°"),
    (121.0, 239.0, "Leo 1° → Scorpio 29°"),
    (151.0, 209.0, "Virgo 1° → Libra 29°"),
    (181.0, 179.0, "Libra 1° → Virgo 29°"),
    (211.0, 149.0, "Scorpio 1° → Leo 29°"),
    (241.0, 119.0, "Sagittarius 1° → Cancer 29°"),
    (271.0,  89.0, "Capricorn 1° → Gemini 29°"),
    (301.0,  59.0, "Aquarius 1° → Taurus 29°"),
    (331.0,  29.0, "Pisces 1° → Aries 29°"),
]

@pytest.mark.parametrize("lon,expected,desc", CONTRA_PAIRS)
def test_contra_antiscion_formula(lon, expected, desc):
    result = _contra(lon)
    assert abs(result - expected) < 0.001, (
        f"{desc}: got {result:.4f}°, expected {expected}°"
    )


# ─────────────────────────────────────────────
# Test 3: Antiscion is symmetric
# ─────────────────────────────────────────────

def test_antiscion_is_symmetric():
    """antiscion(antiscion(L)) == L for all L."""
    for lon in range(0, 360, 15):
        shadow = _antiscion(float(lon))
        back = _antiscion(shadow)
        assert abs(back - lon) < 0.001, f"antiscion not symmetric at {lon}°: {back}"


def test_contra_is_symmetric():
    """contra(contra(L)) == L for all L."""
    for lon in range(0, 360, 15):
        shadow = _contra(float(lon))
        back = _contra(shadow)
        assert abs(back - lon) < 0.001, f"contra not symmetric at {lon}°: {back}"


def test_contra_equals_antiscion_plus_180():
    """contra(L) == (antiscion(L) + 180) % 360."""
    for lon in range(0, 360, 10):
        a = _antiscion(float(lon))
        c = _contra(float(lon))
        expected = (a + 180.0) % 360.0
        assert abs(c - expected) < 0.001, (
            f"contra({lon}) = {c}, expected antiscion+180 = {expected}"
        )


# ─────────────────────────────────────────────
# Test 4: Shadow point output from calc_antiscia
# ─────────────────────────────────────────────

def test_calc_antiscia_returns_7_points():
    """calc_antiscia always returns exactly 7 points (one per planet)."""
    lons = {pid: float(pid * 30) for pid in range(7)}
    result = calc_antiscia(lons)
    assert len(result.points) == 7


def test_points_ids_sequential():
    """Planet IDs in points must be 0-6 in order."""
    lons = {pid: float(pid * 30) for pid in range(7)}
    result = calc_antiscia(lons)
    ids = [p.planet_id for p in result.points]
    assert ids == list(range(7))


def test_points_antiscion_formula():
    """Each point's antiscion field matches _antiscion(lon)."""
    lons = {pid: float(pid * 40 + 5) for pid in range(7)}
    result = calc_antiscia(lons)
    for p in result.points:
        expected = _antiscion(p.lon)
        assert abs(p.antiscion - expected) < 0.001, (
            f"{p.planet_name}: antiscion={p.antiscion}, expected={expected}"
        )


def test_points_contra_formula():
    """Each point's contra_antiscion field matches _contra(lon)."""
    lons = {pid: float(pid * 40 + 5) for pid in range(7)}
    result = calc_antiscia(lons)
    for p in result.points:
        expected = _contra(p.lon)
        assert abs(p.contra_antiscion - expected) < 0.001, (
            f"{p.planet_name}: contra={p.contra_antiscion}, expected={expected}"
        )


def test_all_lons_in_range():
    """All longitude fields must be 0–360°."""
    lons = {pid: float(pid * 50) for pid in range(7)}
    result = calc_antiscia(lons)
    for p in result.points:
        assert 0 <= p.lon < 360
        assert 0 <= p.antiscion < 360
        assert 0 <= p.contra_antiscion < 360


# ─────────────────────────────────────────────
# Test 5: Antiscion aspect detection
# ─────────────────────────────────────────────

def test_antiscion_aspect_within_orb():
    """Sun's antiscion 0.5° from Moon → antiscion aspect detected."""
    # Sun at 10° (antiscion = 170°). Place Moon at 170.5° (0.5° from Sun's antiscion).
    lons = {0: 10.0, 1: 170.5, 2: 50.0, 3: 80.0, 4: 200.0, 5: 250.0, 6: 300.0}
    result = calc_antiscia(lons)
    sun_moon = [a for a in result.aspects
                if {a.planet_a, a.planet_b} == {0, 1}
                and a.aspect_type == "antiscion" and a.aspect_angle == 0]
    assert len(sun_moon) == 1, "Sun antiscion 0.5° from Moon → conjunction expected"
    assert abs(sun_moon[0].orb - 0.5) < 0.01


def test_contra_antiscion_aspect_within_orb():
    """Sun's contra-antiscion 0.3° from Venus → contra-antiscion aspect detected."""
    # Sun at 45° (contra = 315°). Place Venus at 315.3°.
    lons = {0: 45.0, 1: 200.0, 2: 80.0, 3: 315.3, 4: 100.0, 5: 250.0, 6: 30.0}
    result = calc_antiscia(lons)
    sun_venus = [a for a in result.aspects
                 if {a.planet_a, a.planet_b} == {0, 3}
                 and a.aspect_type == "contra_antiscion" and a.aspect_angle == 0]
    assert len(sun_venus) == 1, "Sun contra-antiscion 0.3° from Venus → conjunction expected"
    assert abs(sun_venus[0].orb - 0.3) < 0.01


def test_no_antiscion_aspect_outside_orb():
    """Planet 1.5° from another's antiscion → NO aspect."""
    lons = {0: 10.0, 1: 171.6, 2: 50.0, 3: 80.0, 4: 200.0, 5: 250.0, 6: 300.0}
    result = calc_antiscia(lons)
    sun_moon = [a for a in result.aspects
                if {a.planet_a, a.planet_b} == {0, 1}
                and a.aspect_type == "antiscion" and a.aspect_angle == 0]
    assert len(sun_moon) == 0, "1.5° outside orb → no antiscion conjunction"


def test_antiscion_aspect_at_orb_boundary():
    """Planet at exactly ANTISCIA_ORB from antiscion → included."""
    lons = {0: 10.0, 1: 170.0 + ANTISCIA_ORB, 2: 50.0,
            3: 80.0, 4: 200.0, 5: 250.0, 6: 300.0}
    result = calc_antiscia(lons)
    sun_moon = [a for a in result.aspects
                if {a.planet_a, a.planet_b} == {0, 1}
                and a.aspect_type == "antiscion" and a.aspect_angle == 0]
    assert len(sun_moon) == 1, "At exact conjunction orb boundary → aspect included"


def test_antiscion_orb_default_one_degree():
    """ANTISCIA_ORB must be 1.0°."""
    assert abs(ANTISCIA_ORB - 1.0) < 0.001


# ─────────────────────────────────────────────
# Test 6: No duplicate pairs
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_no_duplicate_aspects(chart_id, chart):
    """Each (A,B,type) pair may appear at most once."""
    _, lons = _build(chart)
    result = calc_antiscia(lons)
    seen = set()
    for a in result.aspects:
        key = (a.planet_a, a.planet_b, a.aspect_type, a.aspect_angle)
        assert key not in seen, (
            f"{chart_id}: duplicate antiscia aspect {a.name_a}-{a.name_b} {a.aspect_type} {a.aspect_angle}°"
        )
        seen.add(key)


# ─────────────────────────────────────────────
# Test 7: Aspects sorted by orb
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_aspects_sorted_by_orb(chart_id, chart):
    """Aspects must be sorted by orb (smallest first)."""
    _, lons = _build(chart)
    result = calc_antiscia(lons)
    orbs = [a.orb for a in result.aspects]
    assert orbs == sorted(orbs), f"{chart_id}: aspects not sorted by orb"


# ─────────────────────────────────────────────
# Test 8: Aspect type values
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_aspect_type_valid(chart_id, chart):
    """aspect_type must be 'antiscion' or 'contra_antiscion'."""
    _, lons = _build(chart)
    result = calc_antiscia(lons)
    valid = {"antiscion", "contra_antiscion"}
    for a in result.aspects:
        assert a.aspect_type in valid, (
            f"{chart_id}: invalid aspect_type '{a.aspect_type}'"
        )


# ─────────────────────────────────────────────
# Test 9: Aspect orbs within maximum
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_aspect_orbs_within_max(chart_id, chart):
    """All reported aspect orbs must be ≤ ANTISCIA_ORB."""
    _, lons = _build(chart)
    result = calc_antiscia(lons)
    for a in result.aspects:
        _, max_orb = ANTISCIA_ASPECTS[a.aspect_angle]
        assert a.orb <= max_orb + 0.001, (
            f"{chart_id}: {a.name_a}-{a.name_b} {a.aspect_name} orb={a.orb:.4f} > {max_orb}"
        )


# ─────────────────────────────────────────────
# Test 10: API output == direct call
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_api_antiscia_match_direct(chart_id, chart):
    """API antiscia output must match direct calc_antiscia() call."""
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
    api = resp.json()["antiscia"]

    _, lons = _build(chart)
    direct = calc_antiscia(lons)

    # Check shadow points
    assert len(api["points"]) == len(direct.points)
    for api_p, dir_p in zip(api["points"], direct.points):
        assert api_p["planet_id"] == dir_p.planet_id
        assert abs(api_p["antiscion"] - dir_p.antiscion) < 0.001, (
            f"{chart_id} {dir_p.planet_name}: antiscion mismatch"
        )
        assert abs(api_p["contra_antiscion"] - dir_p.contra_antiscion) < 0.001

    # Check aspects
    assert len(api["aspects"]) == len(direct.aspects), (
        f"{chart_id}: aspect count mismatch"
    )
    for api_a, dir_a in zip(api["aspects"], direct.aspects):
        assert api_a["planet_a"] == dir_a.planet_a
        assert api_a["planet_b"] == dir_a.planet_b
        assert api_a["aspect_type"] == dir_a.aspect_type
        assert api_a["aspect_angle"] == dir_a.aspect_angle
        assert api_a["aspect_name"] == dir_a.aspect_name
        assert abs(api_a["orb"] - dir_a.orb) < 0.001


# ─────────────────────────────────────────────
# Report: Print table for Morinus comparison
# ─────────────────────────────────────────────

def test_print_antiscia_table():
    """
    In ra bang antiscia de so sanh voi Morinus.
    Morinus: Tables -> Antiscia -> check shadow points + aspects
    """
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    EPHE_PATH = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../../tools/morinus/SWEP/Ephem")
    )
    swe.set_ephe_path(EPHE_PATH)
    sign_names = ["Ari","Tau","Gem","Can","Leo","Vir","Lib","Sco","Sag","Cap","Aqu","Pis"]

    def fmt(lon):
        s = sign_names[int(lon/30)%12]
        d = lon % 30
        return f"{s} {d:.2f}"

    print("\n")
    print("=" * 80)
    print("ANTISCIA & CONTRA-ANTISCIA — SO SANH VOI MORINUS")
    print(f"Orb: {ANTISCIA_ORB}° | Axis: Cancer/Cap (antiscia) & Aries/Lib (contra)")
    print("=" * 80)

    for chart_id, chart in TEST_CHARTS.items():
        _, lons = _build(chart)
        result = calc_antiscia(lons)

        print(f"\n  {chart['desc']}")
        print(f"  {'Planet':<10} {'Position':<14} {'Antiscion':<14} {'Contra-Anti'}")
        print(f"  {'-'*10} {'-'*14} {'-'*14} {'-'*14}")
        for p in result.points:
            print(f"  {p.planet_name:<10} {fmt(p.lon):<14} {fmt(p.antiscion):<14} {fmt(p.contra_antiscion)}")

        if result.aspects:
            print(f"\n  Antiscia Aspects:")
            for a in result.aspects:
                typ = "Antiscion" if a.aspect_type == "antiscion" else "Contra-Anti"
                print(f"    {a.name_a:<8} {typ:<12} {a.aspect_name:<12} {a.name_b:<8} orb={a.orb:.3f}°")
        else:
            print(f"\n  (no antiscia aspects found)")

    print("\n" + "=" * 80)
    print("▶ Morinus → Tables → Antiscia → compare shadow points + aspect list")
    print("=" * 80)
    assert True
