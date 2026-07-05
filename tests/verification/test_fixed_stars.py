"""
Story 11 — Fixed Stars Verification

Test strategy:
  Layer 1: Star catalog integrity (25 stars, valid SE names)
  Layer 2: Star positions in expected zodiac ranges (± 2° from J2000 + ~34yr precession)
  Layer 3: Conjunction detection within orb
  Layer 4: No false positives beyond orb
  Layer 5: Conjunction sorted by orb (tightest first)
  Layer 6: Known star-planet conjunctions (forced synthetic charts)
  Layer 7: Consistency across TEST_CHARTS
  Layer 8: API output == direct core call
  Layer 9: Print table for Morinus comparison

Chay:
  cd backend && source .venv/bin/activate
  pytest ../tests/verification/test_fixed_stars.py -v
  pytest ../tests/verification/test_fixed_stars.py::test_print_fixed_stars_table -v -s
"""

import pytest
import swisseph as swe
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from tests.verification.conftest import TEST_CHARTS
from core.fixed_stars import (
    calc_fixed_stars, FIXED_STARS, CONJUNCTION_ORB, _arc, StarAspect,
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
# Test 1: Star catalog integrity
# ─────────────────────────────────────────────

def test_catalog_has_110_plus_stars():
    """FIXED_STARS catalog must have at least 110 entries (expanded from 25)."""
    assert len(FIXED_STARS) >= 110, f"Catalog has only {len(FIXED_STARS)} stars"


def test_catalog_entries_are_3_tuples():
    """Each catalog entry is (display_name, se_name, nature)."""
    for entry in FIXED_STARS:
        assert len(entry) == 3, f"Entry {entry} is not a 3-tuple"
        name, se, nature = entry
        assert isinstance(name, str) and name
        assert isinstance(se, str) and "," in se, f"{name}: se_name missing comma"
        assert isinstance(nature, str) and nature


def test_behenian_15_present():
    """All 15 Behenian stars must be in the catalog."""
    names = {e[0] for e in FIXED_STARS}
    behenian = [
        "Algol", "Alcyone", "Aldebaran", "Sirius", "Procyon",
        "Regulus", "Alkaid", "Algorab", "Spica", "Arcturus",
        "Alphecca", "Antares", "Vega", "Deneb Algedi", "Fomalhaut",
    ]
    for star in behenian:
        assert star in names, f"Behenian star '{star}' missing from catalog"


def test_conjunction_orb_is_one_degree():
    """CONJUNCTION_ORB must be 1.0°."""
    assert abs(CONJUNCTION_ORB - 1.0) < 0.001


# ─────────────────────────────────────────────
# Test 2: Star positions load and are in range
# ─────────────────────────────────────────────

def test_all_stars_load():
    """Most stars must be loadable via fixstar_ut (allow a few SE name misses)."""
    jd = swe.julday(2000, 1, 1, 12.0, swe.GREG_CAL)
    lons = {pid: 0.0 for pid in range(7)}
    result = calc_fixed_stars(lons, jd)
    # Allow up to 15% failures due to SE name variations; catalog has 110+
    assert len(result.star_positions) >= 90, (
        f"Expected ≥90 star positions, got {len(result.star_positions)}"
    )


def test_star_positions_in_valid_range():
    """All star longitudes must be 0–360°."""
    jd = swe.julday(2000, 1, 1, 12.0, swe.GREG_CAL)
    lons = {pid: 0.0 for pid in range(7)}
    result = calc_fixed_stars(lons, jd)
    for name, lon, _ in result.star_positions:
        assert 0 <= lon < 360, f"{name}: lon={lon} out of range"


def test_key_star_approx_positions_j2000():
    """Key stars near expected J2000 longitudes (±2° for precession tolerance)."""
    # J2000 positions + some precession allowance
    expected = {
        "Algol":     (56.0,  2.0),   # ~26° Taurus
        "Aldebaran": (69.5,  2.0),   # ~9°  Gemini
        "Sirius":    (104.0, 2.0),   # ~14° Cancer
        "Regulus":   (149.8, 2.0),   # ~29° Leo
        "Spica":     (203.7, 2.0),   # ~23° Libra
        "Antares":   (249.7, 2.0),   # ~9°  Sagittarius
        "Vega":      (285.2, 2.0),   # ~15° Capricorn
        "Fomalhaut": (333.7, 2.0),   # ~3°  Pisces
    }
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    lons = {pid: 0.0 for pid in range(7)}
    result = calc_fixed_stars(lons, jd)
    pos_map = {name: lon for name, lon, _ in result.star_positions}

    for star, (exp_lon, tol) in expected.items():
        assert star in pos_map, f"{star} missing from star_positions"
        actual = pos_map[star]
        assert abs(actual - exp_lon) < tol, (
            f"{star}: expected ~{exp_lon}°, got {actual:.4f}°"
        )


# ─────────────────────────────────────────────
# Test 3: Conjunction detection
# ─────────────────────────────────────────────

def test_conjunction_within_orb_detected():
    """Planet at exactly 0.5° from Regulus (149.7°) → conjunction found."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    # Get Regulus position first
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    coords, _, _ = swe.fixstar_ut("Regulus,alLeo", jd, flags)
    regulus_lon = coords[0]

    # Place Sun at Regulus + 0.5°
    lons = {0: (regulus_lon + 0.5) % 360, 1: 50.0, 2: 80.0,
            3: 120.0, 4: 200.0, 5: 250.0, 6: 300.0}
    result = calc_fixed_stars(lons, jd)

    sun_regulus = [c for c in result.aspects
                   if c.star_name == "Regulus" and c.planet_id == 0 and c.aspect_angle == 0]
    assert len(sun_regulus) == 1, "Sun 0.5° from Regulus → conjunction expected"
    assert abs(sun_regulus[0].orb - 0.5) < 0.01


def test_no_conjunction_just_outside_orb():
    """Planet at 1.01° from a star → NO conjunction."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    coords, _, _ = swe.fixstar_ut("Spica,alVir", jd, flags)
    spica_lon = coords[0]

    # Place Venus at Spica + 1.01°
    lons = {0: 100.0, 1: 50.0, 2: 80.0,
            3: (spica_lon + 1.01) % 360, 4: 200.0, 5: 250.0, 6: 300.0}
    result = calc_fixed_stars(lons, jd)

    venus_spica = [c for c in result.aspects
                   if c.star_name == "Spica" and c.planet_id == 3 and c.aspect_angle == 0]
    assert len(venus_spica) == 0, "Venus 1.01° from Spica → no conjunction expected"


def test_conjunction_exact_at_orb_boundary():
    """Planet at exactly CONJUNCTION_ORB from star → conjunction included."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    coords, _, _ = swe.fixstar_ut("Antares,alSco", jd, flags)
    antares_lon = coords[0]

    lons = {0: 100.0, 1: 50.0, 2: 80.0, 3: 120.0,
            4: (antares_lon + CONJUNCTION_ORB) % 360, 5: 250.0, 6: 300.0}
    result = calc_fixed_stars(lons, jd)

    mars_antares = [c for c in result.aspects
                    if c.star_name == "Antares" and c.planet_id == 4 and c.aspect_angle == 0]
    assert len(mars_antares) == 1, "Mars at exact CONJUNCTION_ORB → should be included"


def test_multiple_planets_conjunct_same_star():
    """Two planets within orb of same star → two conjunctions."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    coords, _, _ = swe.fixstar_ut("Aldebaran,alTau", jd, flags)
    aldebaran_lon = coords[0]

    lons = {
        0: (aldebaran_lon + 0.3) % 360,  # Sun near Aldebaran
        1: (aldebaran_lon - 0.7) % 360,  # Moon near Aldebaran
        2: 80.0, 3: 120.0, 4: 200.0, 5: 250.0, 6: 300.0,
    }
    result = calc_fixed_stars(lons, jd)

    ald_conj = [c for c in result.aspects if c.star_name == "Aldebaran" and c.aspect_angle == 0]
    assert len(ald_conj) == 2, f"Expected 2 conjunctions with Aldebaran, got {len(ald_conj)}"
    planet_ids = {c.planet_id for c in ald_conj}
    assert 0 in planet_ids and 1 in planet_ids


# ─────────────────────────────────────────────
# Test 4: Result ordering
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_conjunctions_sorted_by_orb(chart_id, chart):
    """Conjunctions must be sorted by orb (smallest first)."""
    jd, lons = _build(chart)
    result = calc_fixed_stars(lons, jd)
    orbs = [c.orb for c in result.aspects]
    assert orbs == sorted(orbs), (
        f"{chart_id}: aspects not sorted by orb: {orbs}"
    )


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_conjunction_orbs_within_max(chart_id, chart):
    """All reported conjunctions must have orb <= CONJUNCTION_ORB."""
    jd, lons = _build(chart)
    result = calc_fixed_stars(lons, jd)
    for c in result.aspects:
        if c.aspect_angle == 0:
            assert c.orb <= CONJUNCTION_ORB + 0.001, (
                f"{chart_id}: {c.planet_name}-{c.star_name} orb={c.orb:.4f} > {CONJUNCTION_ORB}"
            )


# ─────────────────────────────────────────────
# Test 5: StarConjunction fields
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_conjunction_fields_valid(chart_id, chart):
    """All conjunction fields must be valid types and ranges."""
    jd, lons = _build(chart)
    result = calc_fixed_stars(lons, jd)
    for c in result.aspects:
        if c.aspect_angle == 0:
            assert isinstance(c.star_name, str) and c.star_name
            assert 0 <= c.star_lon < 360
            assert isinstance(c.star_nature, str) and c.star_nature
            assert 0 <= c.planet_id <= 6
            assert isinstance(c.planet_name, str)
            assert 0 <= c.orb <= CONJUNCTION_ORB + 0.001


# ─────────────────────────────────────────────
# Test 6: _arc helper
# ─────────────────────────────────────────────

def test_arc_zero():
    assert _arc(100.0, 100.0) < 0.001


def test_arc_max():
    assert abs(_arc(0.0, 180.0) - 180.0) < 0.001


def test_arc_wrap():
    assert abs(_arc(355.0, 5.0) - 10.0) < 0.001


def test_arc_symmetric():
    assert abs(_arc(60.0, 100.0) - _arc(100.0, 60.0)) < 0.001


# ─────────────────────────────────────────────
# Test 7: API output == direct call
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_api_fixed_stars_match_direct(chart_id, chart):
    """API fixed_stars output must match direct calc_fixed_stars() call."""
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
    api_fs = resp.json()["fixed_stars"]

    jd, lons = _build(chart)
    direct = calc_fixed_stars(lons, jd)

    api_conj = [a for a in api_fs["aspects"] if a["aspect_angle"] == 0]
    dir_conj  = [a for a in direct.aspects   if a.aspect_angle == 0]
    assert len(api_conj) == len(dir_conj), (
        f"{chart_id}: conjunction count mismatch"
    )
    for api_c, dir_c in zip(api_conj, dir_conj):
        assert api_c["star_name"] == dir_c.star_name
        assert api_c["planet_id"] == dir_c.planet_id
        assert abs(api_c["orb"] - dir_c.orb) < 0.001

    assert len(api_fs["star_positions"]) == len(direct.star_positions), (
        f"{chart_id}: star_positions count mismatch"
    )


# ─────────────────────────────────────────────
# Report: Print table for Morinus comparison
# ─────────────────────────────────────────────

def test_print_fixed_stars_table():
    """
    In ra bang fixed stars de so sanh voi Morinus.
    Morinus: Tables -> Fixed Stars -> check conjunction list
    """
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    EPHE_PATH = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../../tools/morinus/SWEP/Ephem")
    )
    swe.set_ephe_path(EPHE_PATH)

    print("\n")
    print("=" * 80)
    print("FIXED STARS — SO SANH VOI MORINUS")
    print(f"Conjunction orb: {CONJUNCTION_ORB}° | {len(FIXED_STARS)} classical stars")
    print("=" * 80)

    sign_names = ["Ari","Tau","Gem","Can","Leo","Vir","Lib","Sco","Sag","Cap","Aqu","Pis"]

    for chart_id, chart in TEST_CHARTS.items():
        jd, lons = _build(chart)
        result = calc_fixed_stars(lons, jd)

        print(f"\n  {chart['desc']}")
        conj = [c for c in result.aspects if c.aspect_angle == 0]
        if conj:
            print(f"  {'Star':<16} {'Nature':<8} {'Planet':<10} {'Orb':>5}  {'StarLon'}")
            print(f"  {'-'*16} {'-'*8} {'-'*10} {'-'*5}  {'-'*14}")
            for c in conj:
                sign_idx = int(c.star_lon / 30) % 12
                deg = c.star_lon % 30
                sign_pos = f"{sign_names[sign_idx]} {deg:.2f}"
                print(f"  {c.star_name:<16} {c.star_nature:<8} {c.planet_name:<10} "
                      f"{c.orb:>4.2f}°  {sign_pos}")
        else:
            print("  (no conjunctions within 1°)")

    print(f"\n  --- All Star Positions ({len(FIXED_STARS)} catalog, chart: rome_1990_day) ---")
    chart = TEST_CHARTS["rome_1990_day"]
    jd, lons = _build(chart)
    result = calc_fixed_stars(lons, jd)
    print(f"  {'Star':<18} {'Nature':<8} {'Longitude'}")
    print(f"  {'-'*18} {'-'*8} {'-'*20}")
    for name, lon, nature in result.star_positions:
        sign_idx = int(lon / 30) % 12
        deg = lon % 30
        print(f"  {name:<18} {nature:<8} {sign_names[sign_idx]} {deg:.2f}° ({lon:.4f})")

    print("\n" + "=" * 80)
    print("▶ Morinus → Tables → Fixed Stars → compare star positions + conjunctions")
    print("=" * 80)
    assert True
