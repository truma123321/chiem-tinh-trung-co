"""
Story 5 — Essential Dignities Verification

Test strategy:
  Layer 1: Unit tests — known planet/sign combinations (hand-verified against classical tables)
  Layer 2: Day/night detection — known charts
  Layer 3: API output == direct core.dignities call
  Layer 4: Print table for manual comparison with Morinus

Để chạy:
  cd backend && source .venv/bin/activate
  pytest ../tests/verification/test_dignities.py -v
  pytest ../tests/verification/test_dignities.py::test_print_dignity_table -v -s
"""

import pytest
import swisseph as swe
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from tests.verification.conftest import TEST_CHARTS
from core.dignities import (
    calc_dignities, is_day_chart,
    DOMICILE, EXALTATION, DETRIMENT, FALL,
    SUN, MOON, MERCURY, VENUS, MARS, JUPITER, SATURN,
    PLANET_NAMES,
)

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


# ─────────────────────────────────────────────
# Test 1: Domicile table — spot-check classical rulerships
# ─────────────────────────────────────────────

DOMICILE_CASES = [
    # (planet_id, sign_idx, midpoint_lon)
    (SUN,     4,  4 * 30 + 15),   # Sun rules Leo
    (MOON,    3,  3 * 30 + 10),   # Moon rules Cancer
    (MERCURY, 2,  2 * 30 + 5),    # Mercury rules Gemini
    (MERCURY, 5,  5 * 30 + 20),   # Mercury rules Virgo
    (VENUS,   1,  1 * 30 + 1),    # Venus rules Taurus
    (VENUS,   6,  6 * 30 + 25),   # Venus rules Libra
    (MARS,    0,  0 * 30 + 12),   # Mars rules Aries
    (MARS,    7,  7 * 30 + 8),    # Mars rules Scorpio
    (JUPITER, 8,  8 * 30 + 18),   # Jupiter rules Sagittarius
    (JUPITER, 11, 11 * 30 + 5),   # Jupiter rules Pisces
    (SATURN,  9,  9 * 30 + 22),   # Saturn rules Capricorn
    (SATURN,  10, 10 * 30 + 3),   # Saturn rules Aquarius
]

@pytest.mark.parametrize("pid,sign,lon", DOMICILE_CASES)
def test_domicile(pid, sign, lon):
    result = calc_dignities(pid, lon, daytime=True)
    assert result.domicile, (
        f"{PLANET_NAMES[pid]} at {lon:.1f}° should be in domicile ({SIGNS[sign]})"
    )
    assert result.score >= 5, f"Domicile score should be >= 5, got {result.score}"


# ─────────────────────────────────────────────
# Test 2: Exaltation — classical exaltations
# ─────────────────────────────────────────────

EXALTATION_CASES = [
    (SUN,     0,   19.0),   # Sun exalted in Aries (19° traditional)
    (MOON,    1,   33.0),   # Moon exalted in Taurus (3° = lon 33°)
    (JUPITER, 3,   95.0),   # Jupiter exalted in Cancer (15° = 95°)
    (MERCURY, 5,  165.0),   # Mercury exalted in Virgo (15° = 165°)
    (SATURN,  6,  187.0),   # Saturn exalted in Libra (21° = 187°)... wait, 6*30+21=201? let's use 186=6*30+6
    (MARS,    9,  298.0),   # Mars exalted in Capricorn (28° = 298°)
    (VENUS,   11, 357.0),   # Venus exalted in Pisces (27° = 357°)
]

@pytest.mark.parametrize("pid,sign,lon", EXALTATION_CASES)
def test_exaltation(pid, sign, lon):
    result = calc_dignities(pid, lon, daytime=True)
    assert result.exaltation, (
        f"{PLANET_NAMES[pid]} at {lon:.1f}° should be in exaltation ({SIGNS[sign]})"
    )


# ─────────────────────────────────────────────
# Test 3: Detriment — opposite of domicile
# ─────────────────────────────────────────────

DETRIMENT_CASES = [
    (SATURN, 4,  4 * 30 + 15),   # Saturn in detriment in Leo
    (SATURN, 3,  3 * 30 + 10),   # Saturn in detriment in Cancer
    (SUN,    10, 10 * 30 + 10),  # Sun in detriment in Aquarius
    (MOON,   9,  9 * 30 + 15),   # Moon in detriment in Capricorn
    (MARS,   6,  6 * 30 + 20),   # Mars in detriment in Libra
    (MARS,   1,  1 * 30 + 5),    # Mars in detriment in Taurus
    (VENUS,  0,  0 * 30 + 25),   # Venus in detriment in Aries
    (VENUS,  7,  7 * 30 + 12),   # Venus in detriment in Scorpio
    (JUPITER,2,  2 * 30 + 8),    # Jupiter in detriment in Gemini
    (JUPITER,5,  5 * 30 + 3),    # Jupiter in detriment in Virgo
    (MERCURY,8,  8 * 30 + 22),   # Mercury in detriment in Sagittarius
    (MERCURY,11, 11 * 30 + 7),   # Mercury in detriment in Pisces
]

@pytest.mark.parametrize("pid,sign,lon", DETRIMENT_CASES)
def test_detriment(pid, sign, lon):
    result = calc_dignities(pid, lon, daytime=True)
    assert result.detriment, (
        f"{PLANET_NAMES[pid]} at {lon:.1f}° should be in detriment ({SIGNS[sign]})"
    )
    # Net score may still be > -5 if planet also has other dignities (e.g. triplicity)
    assert result.score < 0, f"Planet in detriment should have negative score, got {result.score}"


# ─────────────────────────────────────────────
# Test 4: Fall — opposite of exaltation
# ─────────────────────────────────────────────

FALL_CASES = [
    (SUN,     6,  6 * 30 + 15),  # Sun in fall in Libra
    (MOON,    7,  7 * 30 + 5),   # Moon in fall in Scorpio
    (JUPITER, 9,  9 * 30 + 20),  # Jupiter in fall in Capricorn
    (MERCURY, 11, 11 * 30 + 10), # Mercury in fall in Pisces
    (SATURN,  0,  0 * 30 + 15),  # Saturn in fall in Aries
    (MARS,    3,  3 * 30 + 10),  # Mars in fall in Cancer
    (VENUS,   5,  5 * 30 + 20),  # Venus in fall in Virgo
]

@pytest.mark.parametrize("pid,sign,lon", FALL_CASES)
def test_fall(pid, sign, lon):
    result = calc_dignities(pid, lon, daytime=True)
    assert result.fall, (
        f"{PLANET_NAMES[pid]} at {lon:.1f}° should be in fall ({SIGNS[sign]})"
    )


# ─────────────────────────────────────────────
# Test 5: Peregrine — no dignity at all
# ─────────────────────────────────────────────

def test_peregrine_saturn_in_aries():
    """Saturn in early Aries (fall + no other dignity) → peregrine=False (has fall)"""
    # Actually Saturn at 1° Aries: detriment? No. Fall? Yes (Saturn falls in Aries).
    # Peregrine = no POSITIVE dignity. Fall is a debility, not a dignity.
    result = calc_dignities(SATURN, 1.0, daytime=True)
    assert result.fall, "Saturn should be in fall in Aries"
    assert result.peregrine, "Saturn has no positive dignity in early Aries"


def test_not_peregrine_when_term():
    """Jupiter in Aries 0-6° → Jupiter is term ruler → NOT peregrine"""
    result = calc_dignities(JUPITER, 3.0, daytime=True)
    assert result.term, "Jupiter should rule first term of Aries (0-6°)"
    assert not result.peregrine, "Jupiter with term should not be peregrine"


# ─────────────────────────────────────────────
# Test 6: Egyptian Terms — boundary checks
# ─────────────────────────────────────────────

TERM_CASES = [
    # (planet, lon, expected_term_lord)
    (JUPITER,  0.0,  True),   # Aries 0°: Jupiter 0-6
    (JUPITER,  5.9,  True),   # Aries 5.9°: still Jupiter
    (VENUS,    6.0,  True),   # Aries 6°: Venus 6-12
    (VENUS,   11.9,  True),   # Aries 11.9°: still Venus
    (MERCURY, 12.0,  True),   # Aries 12°: Mercury 12-20
    (MARS,    20.0,  True),   # Aries 20°: Mars 20-25
    (SATURN,  25.0,  True),   # Aries 25°: Saturn 25-30
    (VENUS,   30.0,  True),   # Taurus 0°: Venus rules first 8°
    (VENUS,   37.9,  True),   # Taurus 7.9°
]

@pytest.mark.parametrize("pid,lon,expected", TERM_CASES)
def test_term_boundaries(pid, lon, expected):
    result = calc_dignities(pid, lon, daytime=True)
    assert result.term == expected, (
        f"{PLANET_NAMES[pid]} at {lon:.1f}°: term={result.term}, expected {expected}"
    )


# ─────────────────────────────────────────────
# Test 7: Triplicity — day vs night
# ─────────────────────────────────────────────

def test_triplicity_fire_day():
    """Sun is day ruler of Fire triplicity → Sun at 15° Leo (Fire) daytime"""
    result = calc_dignities(SUN, 4 * 30 + 15, daytime=True)
    assert result.triplicity, "Sun should be triplicity lord of Leo (Fire) by day"


def test_triplicity_fire_night():
    """Jupiter is night ruler of Fire → Sun at 15° Leo nighttime → no trip for Sun"""
    result_sun = calc_dignities(SUN, 4 * 30 + 15, daytime=False)
    result_jup = calc_dignities(JUPITER, 4 * 30 + 15, daytime=False)
    assert not result_sun.triplicity, "Sun should NOT be triplicity lord of Leo by night"
    assert result_jup.triplicity, "Jupiter should be triplicity lord of Leo by night"


def test_triplicity_earth_day():
    """Venus is day ruler of Earth triplicity → Venus at 15° Taurus (Earth) daytime"""
    result = calc_dignities(VENUS, 1 * 30 + 15, daytime=True)
    assert result.triplicity, "Venus should be triplicity lord of Taurus (Earth) by day"


def test_triplicity_water_night():
    """Mars is night ruler of Water triplicity → Mars at 15° Cancer (Water) nighttime"""
    result = calc_dignities(MARS, 3 * 30 + 15, daytime=False)
    assert result.triplicity, "Mars should be triplicity lord of Cancer (Water) by night"


# ─────────────────────────────────────────────
# Test 8: is_day_chart
# ─────────────────────────────────────────────

def test_day_chart_sun_at_mc():
    """Sun at MC (ASC+270°) → above horizon → day chart.
    With ASC=0°: MC=270°, IC=90°, DSC=180°."""
    assert is_day_chart(270.0, 0.0)    # Sun at MC, ASC=0°
    assert is_day_chart(180.0, 270.0)  # Sun at MC, ASC=270°


def test_night_chart_sun_at_ic():
    """Sun at IC (ASC+90°) → below horizon → night chart."""
    assert not is_day_chart(90.0, 0.0)    # Sun at IC, ASC=0°
    assert not is_day_chart(0.0, 270.0)   # Sun at IC, ASC=270°


def test_day_chart_sun_in_upper_hemisphere():
    """Sun between DSC and ASC (upper arc) → day chart."""
    # ASC=167°, DSC=347°. Upper arc: 347°→0°→167°. Sun at 84° is in [0°,167°].
    assert is_day_chart(84.0, 167.0)   # Rome 1990 case — should be day chart


def test_night_chart_sun_in_lower_hemisphere():
    """Sun between ASC and DSC (lower arc) → night chart."""
    # ASC=167°. Lower arc: 167°→347°. Sun at 250° is in that arc.
    assert not is_day_chart(250.0, 167.0)


# ─────────────────────────────────────────────
# Test 9: API output == direct core.dignities
# ─────────────────────────────────────────────

@pytest.mark.parametrize("chart_id,chart", TEST_CHARTS.items())
def test_api_dignities_match_direct(chart_id, chart):
    """API dignity values must match direct calc_dignities() calls."""
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

    api_digs = {d["planet_id"]: d for d in data["dignities"]}
    day = data["day_chart"]

    for planet_id in range(7):
        planet_lon = next(p["lon"] for p in data["planets"] if p["id"] == planet_id)
        direct = calc_dignities(planet_id, planet_lon, day)
        api    = api_digs[planet_id]

        for field in ("domicile", "exaltation", "triplicity", "term", "face",
                      "peregrine", "detriment", "fall", "score"):
            assert getattr(direct, field) == api[field], (
                f"{chart_id} {PLANET_NAMES[planet_id]} {field}: "
                f"direct={getattr(direct, field)}, api={api[field]}"
            )


# ─────────────────────────────────────────────
# Report: Print table for Morinus comparison
# ─────────────────────────────────────────────

def test_print_dignity_table():
    """
    In ra bảng để so sánh tay với Morinus.
    Chạy: pytest -v -s tests/verification/test_dignities.py::test_print_dignity_table
    """
    FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

    EPHE_PATH = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../../tools/morinus/SWEP/Ephem")
    )
    swe.set_ephe_path(EPHE_PATH)

    print("\n")
    print("=" * 80)
    print("ESSENTIAL DIGNITIES — SO SÁNH VỚI MORINUS")
    print("Dom=5 Exal=4 Trip=3 Term=2 Face=1 | Det=-5 Fall=-4")
    print("=" * 80)

    for chart_id, chart in TEST_CHARTS.items():
        hour_ut = chart["hour"] + chart["minute"] / 60.0 - chart["ut_offset"]
        jd = swe.julday(chart["year"], chart["month"], chart["day"], hour_ut, swe.GREG_CAL)
        cusps, ascmc = swe.houses(jd, chart["lat"], chart["lon"], b"B")
        asc = ascmc[0]

        sun_res, _ = swe.calc_ut(jd, swe.SUN, FLAGS)
        sun_lon = sun_res[0]
        day = is_day_chart(sun_lon, asc)

        print(f"\n📍 {chart['desc']}  ({'Day' if day else 'Night'} chart)")
        print(f"   {chart['year']}-{chart['month']:02d}-{chart['day']:02d} "
              f"{chart['hour']:02d}:{chart['minute']:02d} UT | "
              f"ASC={asc:.2f}° Sun={sun_lon:.2f}°")
        print(f"   {'Planet':<10} {'Sign':<14} {'Dom':>4}{'Exl':>4}{'Trp':>4}"
              f"{'Trm':>4}{'Fce':>4} | {'Det':>4}{'Fal':>4}{'Per':>4} | {'Score':>6}")
        print(f"   {'-'*10} {'-'*14} {'-'*4}{'-'*4}{'-'*4}{'-'*4}{'-'*4}"
              f"   {'-'*4}{'-'*4}{'-'*4}   {'-'*6}")

        for pid in range(7):
            res, _ = swe.calc_ut(jd, pid, FLAGS)
            lon = res[0]
            d = calc_dignities(pid, lon, day)
            sign_name = SIGNS[d.sign_idx]
            deg = lon % 30

            def flag(b): return "Y" if b else "."

            print(f"   {PLANET_NAMES[pid]:<10} {deg:5.1f}°{sign_name:<9}"
                  f" {flag(d.domicile):>4}{flag(d.exaltation):>4}"
                  f"{flag(d.triplicity):>4}{flag(d.term):>4}{flag(d.face):>4}"
                  f" | {flag(d.detriment):>4}{flag(d.fall):>4}{flag(d.peregrine):>4}"
                  f" | {d.score:>6}")

    print("\n" + "=" * 80)
    print("▶ Mở Morinus → nhập chart → Tables → Dignities → so sánh")
    print("=" * 80)
    assert True
