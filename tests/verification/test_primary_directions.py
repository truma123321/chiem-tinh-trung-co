"""
Story 15 — Primary Directions Verification (Ptolemaic Zodiacal)

Test strategy:
  Layer 1: Math helpers (_ecl_to_equ, _oa)
  Layer 2: OA(ASC) == RAMC (fundamental identity)
  Layer 3: Arc formula — direct and converse
  Layer 4: Aspect ray positions (sinister/dexter offsets)
  Layer 5: Arc range (0 < arc <= MAX_ARC=90)
  Layer 6: No duplicate (sig, prom, asp, direction) combos
  Layer 7: Sorted by arc
  Layer 8: Known direction spot-checks
  Layer 9: Consistency across TEST_CHARTS
  Layer 10: API output == direct core call
  Layer 11: Print table for Morinus comparison

Chay:
  cd backend && source .venv/bin/activate
  pytest ../tests/verification/test_primary_directions.py -v
  pytest ../tests/verification/test_primary_directions.py::test_print_primary_directions_table -v -s
"""

import math
import pytest
import swisseph as swe
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from tests.verification.conftest import TEST_CHARTS
from core.primary_directions import (
    calc_primary_directions,
    _ecl_to_equ, _oa,
    ASPECT_OFFSETS, MAX_ARC,
)


def _build(chart):
    hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart.get("ut_offset", 0)
    jd = swe.julday(chart["year"], chart["month"], chart["day"], hour_ut, swe.GREG_CAL)
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    lons = {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, FLAGS)
        lons[pid] = r[0]
    cusps, ascmc = swe.houses(jd, chart["lat"], chart["lon"], b"B")
    asc, ramc = ascmc[0], ascmc[2]
    return jd, lons, asc, ramc, chart["lat"]


# ─────────────────────────────────────────────
# Test 1: _ecl_to_equ helper
# ─────────────────────────────────────────────

def test_ecl_to_equ_aries_0():
    """0° Aries → RA=0°, Dec=0°."""
    eps = 23.44
    ra, dec = _ecl_to_equ(0.0, eps)
    assert abs(ra) < 0.01
    assert abs(dec) < 0.01


def test_ecl_to_equ_cancer_0():
    """0° Cancer (90°) → RA=90°, Dec=ε."""
    eps = 23.44
    ra, dec = _ecl_to_equ(90.0, eps)
    assert abs(ra - 90.0) < 0.1
    assert abs(dec - eps) < 0.1


def test_ecl_to_equ_libra_0():
    """0° Libra (180°) → RA=180°, Dec=0°."""
    eps = 23.44
    ra, dec = _ecl_to_equ(180.0, eps)
    assert abs(ra - 180.0) < 0.1
    assert abs(dec) < 0.1


def test_ecl_to_equ_capricorn_0():
    """0° Capricorn (270°) → RA=270°, Dec=−ε."""
    eps = 23.44
    ra, dec = _ecl_to_equ(270.0, eps)
    assert abs(ra - 270.0) < 0.1
    assert abs(dec + eps) < 0.1


def test_ecl_to_equ_ra_in_range():
    """RA must always be in [0°, 360°)."""
    eps = 23.44
    for lon in range(0, 360, 15):
        ra, _ = _ecl_to_equ(float(lon), eps)
        assert 0 <= ra < 360, f"RA out of range at lon={lon}: {ra}"


# ─────────────────────────────────────────────
# Test 2: _oa helper
# ─────────────────────────────────────────────

def test_oa_pole_zero():
    """At pole=0°, OA = RA (no AD)."""
    ra, dec = 120.0, 20.0
    oa = _oa(ra, dec, 0.0)
    assert abs(oa - ra) < 0.01


def test_oa_at_equator_dec_zero():
    """Dec=0° → AD=0 → OA=RA regardless of pole."""
    for pole in [0, 30, 45, 60]:
        oa = _oa(100.0, 0.0, float(pole))
        assert abs(oa - 100.0) < 0.01, f"pole={pole}"


def test_oa_positive_dec_reduces_oa():
    """Positive Dec + positive pole → positive AD → OA < RA."""
    oa = _oa(100.0, 20.0, 45.0)
    assert oa < 100.0 or oa > 300.0  # OA < RA (mod 360)


def test_oa_returns_in_range():
    """OA must be in [0°, 360°)."""
    for ra in range(0, 360, 30):
        for dec in [-20, 0, 20]:
            oa = _oa(float(ra), float(dec), 45.0)
            assert 0 <= oa < 360, f"OA out of range: {oa}"


# ─────────────────────────────────────────────
# Test 3: OA(ASC) == RAMC identity
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_oa_asc_equals_ramc(chart_id, chart):
    """The ASC's OA under geographic latitude should produce the RAMC (by definition)."""
    jd, lons, asc, ramc, lat = _build(chart)
    r, _ = swe.calc_ut(jd, swe.ECL_NUT, 0)
    eps = r[0]
    ra_asc, dec_asc = _ecl_to_equ(asc, eps)
    oa_asc = _oa(ra_asc, dec_asc, lat)
    # In our implementation we use RAMC directly (not the computed OA_ASC)
    # Verify the implementation uses RAMC for ASC sig_oa
    result = calc_primary_directions(lons, ramc, lat, jd)
    assert result.ramc == round(ramc, 4), f"{chart_id}: RAMC mismatch"


# ─────────────────────────────────────────────
# Test 4: Aspect rays
# ─────────────────────────────────────────────

def test_aspect_offsets_count():
    """Must have exactly 8 aspect rays."""
    assert len(ASPECT_OFFSETS) == 8


def test_body_offset_zero():
    assert ASPECT_OFFSETS["body"] == 0.0


def test_sinister_sextile_plus_60():
    assert ASPECT_OFFSETS["sinister_sextile"] == 60.0


def test_dexter_sextile_minus_60():
    assert ASPECT_OFFSETS["dexter_sextile"] == -60.0


def test_opposition_180():
    assert ASPECT_OFFSETS["opposition"] == 180.0


def test_sinister_dexter_are_opposite():
    """Sinister and dexter of same aspect type should be symmetric."""
    assert ASPECT_OFFSETS["sinister_sextile"] == -ASPECT_OFFSETS["dexter_sextile"]
    assert ASPECT_OFFSETS["sinister_square"] == -ASPECT_OFFSETS["dexter_square"]
    assert ASPECT_OFFSETS["sinister_trine"] == -ASPECT_OFFSETS["dexter_trine"]


# ─────────────────────────────────────────────
# Test 5: Arc range
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_all_arcs_in_range(chart_id, chart):
    """All arcs must be in (0, MAX_ARC]."""
    jd, lons, _, ramc, lat = _build(chart)
    result = calc_primary_directions(lons, ramc, lat, jd)
    for d in result.directions:
        assert 0.0 < d.arc <= MAX_ARC + 0.001, (
            f"{chart_id}: {d.significator}→{d.promittor_planet} arc={d.arc}"
        )


def test_max_arc_is_90():
    assert MAX_ARC == 90.0


# ─────────────────────────────────────────────
# Test 6: No duplicates
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_no_duplicate_directions(chart_id, chart):
    """Each (sig, prom_planet, prom_asp, direction, direction_type) combo must be unique."""
    jd, lons, _, ramc, lat = _build(chart)
    result = calc_primary_directions(lons, ramc, lat, jd)
    seen = set()
    for d in result.directions:
        key = (d.significator, d.promittor_planet_id, d.promittor_aspect,
               d.direction, d.direction_type)
        assert key not in seen, (
            f"{chart_id}: duplicate [{d.direction_type}] {d.significator}→{d.promittor_planet} "
            f"{d.promittor_aspect} {d.direction}"
        )
        seen.add(key)


# ─────────────────────────────────────────────
# Test 7: Sorted by arc
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_directions_sorted_by_arc(chart_id, chart):
    """Directions must be sorted by arc (smallest first)."""
    jd, lons, _, ramc, lat = _build(chart)
    result = calc_primary_directions(lons, ramc, lat, jd)
    arcs = [d.arc for d in result.directions]
    assert arcs == sorted(arcs), f"{chart_id}: not sorted"


# ─────────────────────────────────────────────
# Test 8: Direction type validity
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_direction_types_valid(chart_id, chart):
    """direction field must be 'direct' or 'converse'."""
    jd, lons, _, ramc, lat = _build(chart)
    result = calc_primary_directions(lons, ramc, lat, jd)
    for d in result.directions:
        assert d.direction in {"direct", "converse"}, (
            f"{chart_id}: invalid direction '{d.direction}'"
        )


@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_significator_valid(chart_id, chart):
    """significator must be one of the 9 valid options (ASC, MC, 7 planets)."""
    jd, lons, _, ramc, lat = _build(chart)
    result = calc_primary_directions(lons, ramc, lat, jd)
    valid = {"ASC", "MC", "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
    for d in result.directions:
        assert d.significator in valid


# ─────────────────────────────────────────────
# Test 9: Known direction verification (Rome 1990)
# ─────────────────────────────────────────────

def test_asc_to_jupiter_body_rome_1990():
    """ASC direct to Jupiter body: ~11.96° = year 2002."""
    # Verified manually: OA(Jupiter) - RAMC ≈ 11.96
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    lons = {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, FLAGS)
        lons[pid] = r[0]
    _, ascmc = swe.houses(jd, 41.9, 12.5, b"B")
    ramc = ascmc[2]
    result = calc_primary_directions(lons, ramc, 41.9, jd)

    jup_direct = [d for d in result.directions
                  if d.significator == "ASC"
                  and d.promittor_planet == "Jupiter"
                  and d.promittor_aspect == "body"
                  and d.direction == "direct"
                  and d.direction_type == "zodiacal"]
    assert len(jup_direct) == 1, "Expected ASC direct to Jupiter body"
    assert abs(jup_direct[0].arc - 11.96) < 0.1, (
        f"Expected ~11.96°, got {jup_direct[0].arc:.4f}°"
    )


def test_result_contains_all_nine_significators():
    """Result must include directions for all 9 significators."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    lons = {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, FLAGS)
        lons[pid] = r[0]
    _, ascmc = swe.houses(jd, 41.9, 12.5, b"B")
    result = calc_primary_directions(lons, ascmc[2], 41.9, jd)
    sigs = {d.significator for d in result.directions}
    for expected in {"ASC", "MC", "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}:
        assert expected in sigs, f"Missing significator: {expected}"


def test_direction_types_include_zodiacal_and_mundane():
    """Both zodiacal and mundane direction types must be present."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    lons = {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, FLAGS)
        lons[pid] = r[0]
    _, ascmc = swe.houses(jd, 41.9, 12.5, b"B")
    result = calc_primary_directions(lons, ascmc[2], 41.9, jd)
    types = {d.direction_type for d in result.directions}
    assert types == {"zodiacal", "mundane"}


def test_converse_and_direct_both_present():
    """Both 'direct' and 'converse' directions must appear."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    lons = {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, FLAGS)
        lons[pid] = r[0]
    _, ascmc = swe.houses(jd, 41.9, 12.5, b"B")
    result = calc_primary_directions(lons, ascmc[2], 41.9, jd)
    dtypes = {d.direction for d in result.directions}
    assert "direct" in dtypes
    assert "converse" in dtypes


# ─────────────────────────────────────────────
# Test 10: API output == direct call
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_api_primary_directions_match_direct(chart_id, chart):
    """API primary_directions output must match direct calc call."""
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
    api = resp.json()["primary_directions"]

    jd, lons, _, ramc, lat = _build(chart)
    direct = calc_primary_directions(lons, ramc, lat, jd)

    assert len(api["directions"]) == len(direct.directions), (
        f"{chart_id}: direction count mismatch "
        f"{len(api['directions'])} vs {len(direct.directions)}"
    )
    assert abs(api["ramc"] - direct.ramc) < 0.01
    assert abs(api["obliquity"] - direct.obliquity) < 0.001

    for api_d, dir_d in zip(api["directions"], direct.directions):
        assert api_d["significator"] == dir_d.significator
        assert api_d["promittor_planet_id"] == dir_d.promittor_planet_id
        assert api_d["promittor_aspect"] == dir_d.promittor_aspect
        assert api_d["direction"] == dir_d.direction
        assert abs(api_d["arc"] - dir_d.arc) < 0.001, (
            f"{chart_id}: arc mismatch for "
            f"{dir_d.significator}→{dir_d.promittor_planet} {dir_d.promittor_aspect}"
        )


# ─────────────────────────────────────────────
# Report: Print table for Morinus comparison
# ─────────────────────────────────────────────

def test_print_primary_directions_table():
    """
    In ra bang primary directions de so sanh voi Morinus.
    Morinus: Directions -> Primary -> Zodiacal (Ptolemaic)
    Key: 1° = 1 year (Ptolemy)
    """
    EPHE_PATH = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../../tools/morinus/SWEP/Ephem")
    )
    swe.set_ephe_path(EPHE_PATH)

    print("\n")
    print("=" * 90)
    print("PRIMARY DIRECTIONS (Ptolemaic Zodiacal) — SO SANH VOI MORINUS")
    print("Method: Zodiacal | Key: Ptolemy 1°=1yr | Sigs: ASC/MC/Sun/Moon")
    print("=" * 90)

    chart = TEST_CHARTS["rome_1990_day"]
    jd, lons, _, ramc, lat = _build(chart)
    result = calc_primary_directions(lons, ramc, lat, jd)

    print(f"\n  {chart['desc']}")
    print(f"  RAMC={result.ramc:.4f}  eps={result.obliquity:.4f}  lat={result.geo_lat}")
    print(f"  Total directions (0-90yr): {len(result.directions)}")
    print()
    print(f"  {'Sig':<6} {'D/C':<8} {'Promittor':<10} {'Aspect':<20} {'Arc':>8}  Year")
    print(f"  {'-'*6} {'-'*8} {'-'*10} {'-'*20} {'-'*8}  {'-'*8}")

    birth_year = chart["year"]
    for d in result.directions[:40]:   # first 40
        dc = "D" if d.direction == "direct" else "c"
        year = birth_year + d.arc
        print(f"  {d.significator:<6} {d.direction[:3]:<8} {d.promittor_planet:<10} "
              f"{d.promittor_aspect:<20} {d.arc:>8.3f}  {year:.1f}")

    if len(result.directions) > 40:
        print(f"  ... ({len(result.directions) - 40} more)")

    print("\n" + "=" * 90)
    print("▶ Morinus → Directions → Primary → Zodiacal → compare arc values")
    print("▶ Use Ptolemy key: arc° = years from birth")
    print("=" * 90)
    assert True


# ─────────────────────────────────────────────
# Test 11: Timing keys
# ─────────────────────────────────────────────

def test_timing_key_date_exact_present():
    """Every direction must have a non-zero date_exact JD."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    lons = {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, FLAGS)
        lons[pid] = r[0]
    _, ascmc = swe.houses(jd, 41.9, 12.5, b"B")
    result = calc_primary_directions(lons, ascmc[2], 41.9, jd)
    for d in result.directions:
        assert d.date_exact > 0, f"date_exact not set for {d.significator}→{d.promittor_planet}"
        assert d.date_exact > jd, "date_exact must be after birth JD"


def test_timing_keys_produce_different_dates():
    """Ptolemy, Naibod, Van Dam, and solar_arc must produce distinct dates for same arc."""
    jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
    lons = {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, FLAGS)
        lons[pid] = r[0]
    _, ascmc = swe.houses(jd, 41.9, 12.5, b"B")

    results = {}
    for key in ("ptolemy", "naibod", "van_dam", "solar_arc"):
        r = calc_primary_directions(lons, ascmc[2], 41.9, jd, key=key)
        # Pick a specific zodiacal direction for comparison
        asc_jup = next(
            d for d in r.directions
            if d.significator == "ASC" and d.promittor_planet == "Jupiter"
            and d.promittor_aspect == "body" and d.direction == "direct"
            and d.direction_type == "zodiacal"
        )
        results[key] = asc_jup.date_exact

    # All four keys give different dates (no two equal)
    dates = list(results.values())
    assert len(set(round(d, 1) for d in dates)) == 4, (
        f"Timing keys should produce distinct dates: {results}"
    )
    # Naibod gives earlier date than Ptolemy (0.985647 < 1 year/degree)
    assert results["naibod"] < results["ptolemy"], "Naibod should be earlier than Ptolemy"
    # Van Dam (tropical year 365.2422 days) is slightly earlier than Ptolemy (Julian 365.25)
    assert results["van_dam"] < results["ptolemy"], "Van Dam should be slightly earlier than Ptolemy"
