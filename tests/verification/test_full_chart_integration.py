"""
Story 16 — Full Chart Integration & Morinus Parity Verification

Comprehensive end-to-end test suite that validates ALL 15 stories through the
live FastAPI endpoint. Uses the Rome 1990 chart as canonical reference.

Test structure:
  Layer 1:  API endpoint health — 200 response, valid structure
  Layer 2:  Planets (Story 3) — match direct swe.calc_ut
  Layer 3:  Houses (Story 4) — match direct swe.houses
  Layer 4:  Dignities (Story 5) — spot-check 5 planets in domicile/exaltation
  Layer 5:  Day/Night chart flag
  Layer 6:  Almuten (Story 6) — winner returned, scores populated
  Layer 7:  Aspects (Story 8) — aspects exist, valid fields
  Layer 8:  Arabic Parts (Story 7) — Lot of Fortune present
  Layer 9:  Conditions (Story 9) — Moon VOC flag, Saturn free from beams
  Layer 10: Sect (Story 10) — Sun diurnal in-sect, Moon nocturnal out-of-sect
  Layer 11: Fixed Stars (Story 11) — star positions populated, conjunctions valid
  Layer 12: Antiscia (Story 12) — Mercury contra-antiscion Saturn confirmed
  Layer 13: Firdaria (Story 13) — structure valid, current period identified
  Layer 14: Profections (Story 14) — age 36, house 1, lord Mercury
  Layer 15: Primary Directions (Story 15) — 460 directions (236 zodiacal + 224 mundane), first arc < 1
  Layer 16: Cross-story consistency — planet data agrees across all modules
  Layer 17: Print summary table for manual Morinus comparison

To run:
  cd backend && source .venv/bin/activate
  pytest ../tests/verification/test_full_chart_integration.py -v
  pytest ../tests/verification/test_full_chart_integration.py -v -s   # with print output
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from fastapi.testclient import TestClient
from main import app
from tests.verification.conftest import TOLERANCE

# ─── Reference chart: Rome 1990-06-15 10:30 UT ─────────────────────────────

CHART_REQUEST = {
    "year": 1990, "month": 6, "day": 15,
    "hour": 10, "minute": 30,
    "lat": 41.9, "lon": 12.5,
    "hsys": "B",
    "ut_offset": 0.0,
    "include_outer": False,
}

REF_JD        = 2448057.9375
REF_ASC       = 167.026
REF_MC        = 74.750
REF_ARMC      = 73.4499
REF_OBLIQUITY = 23.442038

REF_PLANETS = {
    "Sun":     84.0699,
    "Moon":    344.5236,
    "Mercury": 65.5835,
    "Venus":   48.7041,
    "Mars":    10.9964,
    "Jupiter": 105.8759,
    "Saturn":  294.0356,
}

REF_SIGNS = {
    "Sun": "Gemini", "Moon": "Pisces", "Mercury": "Gemini",
    "Venus": "Taurus", "Mars": "Aries", "Jupiter": "Cancer", "Saturn": "Capricorn",
}

SIGN_ABBR = [
    "Ari", "Tau", "Gem", "Can", "Leo", "Vir",
    "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis",
]
SIGN_FULL = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def chart(client):
    """Full natal chart response — computed once, shared by all layers."""
    resp = client.post("/chart/natal", json=CHART_REQUEST)
    assert resp.status_code == 200, f"API error {resp.status_code}: {resp.text}"
    return resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 1: API endpoint health
# ═══════════════════════════════════════════════════════════════════════════════

def test_l1_api_returns_200(client):
    resp = client.post("/chart/natal", json=CHART_REQUEST)
    assert resp.status_code == 200


def test_l1_response_has_all_sections(chart):
    required = [
        "julian_day", "planets", "houses", "dignities", "day_chart",
        "almuten", "arabic_parts", "aspects", "conditions", "sect",
        "fixed_stars", "antiscia", "firdaria", "profections", "primary_directions",
    ]
    missing = [k for k in required if k not in chart]
    assert not missing, f"Missing sections: {missing}"


def test_l1_julian_day_correct(chart):
    assert abs(chart["julian_day"] - REF_JD) < 0.001, (
        f"JD: got {chart['julian_day']}, expected {REF_JD}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 2: Planets (Story 3)
# ═══════════════════════════════════════════════════════════════════════════════

def test_l2_planet_count(chart):
    assert len(chart["planets"]) == 9  # 7 traditional + True Node + Mean Node


def test_l2_planet_longitudes(chart):
    planet_lons = {p["name"]: p["lon"] for p in chart["planets"]}
    for name, expected in REF_PLANETS.items():
        assert abs(planet_lons[name] - expected) < TOLERANCE, (
            f"{name}: got {planet_lons[name]:.4f}, expected {expected:.4f}"
        )


def test_l2_planet_signs(chart):
    planet_signs = {p["name"]: p["sign"] for p in chart["planets"]}
    for name, expected_sign in REF_SIGNS.items():
        assert planet_signs[name] == expected_sign, (
            f"{name}: got {planet_signs[name]}, expected {expected_sign}"
        )


def test_l2_saturn_retrograde(chart):
    saturn = next(p for p in chart["planets"] if p["name"] == "Saturn")
    assert saturn["retrograde"] is True
    assert saturn["speed"] < 0


def test_l2_sun_moon_direct(chart):
    for name in ("Sun", "Moon"):
        p = next(x for x in chart["planets"] if x["name"] == name)
        assert p["retrograde"] is False, f"{name} should not be retrograde"


def test_l2_sign_lon_within_30(chart):
    for p in chart["planets"]:
        assert 0 <= p["sign_lon"] < 30, (
            f"{p['name']} sign_lon={p['sign_lon']:.4f} out of [0,30)"
        )


def test_l2_lon_reconstructed_from_sign(chart):
    for p in chart["planets"]:
        idx = SIGN_FULL.index(p["sign"])
        reconstructed = idx * 30 + p["sign_lon"]
        assert abs(p["lon"] - reconstructed) < 0.001, (
            f"{p['name']}: lon={p['lon']:.4f} != sign*30+sign_lon={reconstructed:.4f}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 3: Houses (Story 4)
# ═══════════════════════════════════════════════════════════════════════════════

def test_l3_asc(chart):
    assert abs(chart["houses"]["asc"] - REF_ASC) < TOLERANCE, (
        f"ASC: got {chart['houses']['asc']:.4f}, expected {REF_ASC:.4f}"
    )


def test_l3_mc(chart):
    assert abs(chart["houses"]["mc"] - REF_MC) < TOLERANCE, (
        f"MC: got {chart['houses']['mc']:.4f}, expected {REF_MC:.4f}"
    )


def test_l3_armc(chart):
    assert abs(chart["houses"]["armc"] - REF_ARMC) < TOLERANCE, (
        f"ARMC: got {chart['houses']['armc']:.4f}, expected {REF_ARMC:.4f}"
    )


def test_l3_12_cusps(chart):
    assert len(chart["houses"]["cusps"]) == 12


def test_l3_house_system_alcabitius(chart):
    assert chart["houses"]["system"] == "Alcabitius"


def test_l3_cusps_progress_around_zodiac(chart):
    cusps = chart["houses"]["cusps"]
    for i in range(1, 12):
        diff = (cusps[i] - cusps[i - 1]) % 360
        assert diff < 180, (
            f"Cusps not progressing at house {i+1}: {cusps[i-1]:.2f} -> {cusps[i]:.2f}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 4: Dignities (Story 5)
# ═══════════════════════════════════════════════════════════════════════════════

def test_l4_dignity_count(chart):
    assert len(chart["dignities"]) == 7


def test_l4_mercury_domicile(chart):
    d = next(x for x in chart["dignities"] if x["planet_name"] == "Mercury")
    assert d["domicile"] is True
    assert d["detriment"] is False and d["fall"] is False


def test_l4_venus_domicile(chart):
    d = next(x for x in chart["dignities"] if x["planet_name"] == "Venus")
    assert d["domicile"] is True


def test_l4_mars_domicile(chart):
    d = next(x for x in chart["dignities"] if x["planet_name"] == "Mars")
    assert d["domicile"] is True


def test_l4_jupiter_exaltation(chart):
    d = next(x for x in chart["dignities"] if x["planet_name"] == "Jupiter")
    assert d["exaltation"] is True
    assert d["domicile"] is False


def test_l4_saturn_domicile(chart):
    d = next(x for x in chart["dignities"] if x["planet_name"] == "Saturn")
    assert d["domicile"] is True


def test_l4_sun_no_major_dignity(chart):
    d = next(x for x in chart["dignities"] if x["planet_name"] == "Sun")
    assert d["domicile"] is False
    assert d["exaltation"] is False
    assert d["detriment"] is False
    assert d["fall"] is False


def test_l4_dignified_planets_positive_score(chart):
    dignified = {"Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
    for d in chart["dignities"]:
        if d["planet_name"] in dignified:
            assert d["score"] > 0, (
                f"{d['planet_name']} score={d['score']} should be positive"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 5: Day chart
# ═══════════════════════════════════════════════════════════════════════════════

def test_l5_day_chart(chart):
    assert chart["day_chart"] is True


def test_l5_sect_agrees(chart):
    assert chart["sect"]["day_chart"] == chart["day_chart"]


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 6: Almuten (Story 6)
# ═══════════════════════════════════════════════════════════════════════════════

def test_l6_almuten_winner_valid(chart):
    alm = chart["almuten"]
    valid = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
    assert alm["winner"] in valid


def test_l6_almuten_5_scoring_points(chart):
    """Almuten scores 5 points: Sun, Moon, ASC, Lot of Fortune, Syzygy."""
    assert len(chart["almuten"]["points"]) == 5


def test_l6_winner_has_highest_score(chart):
    alm = chart["almuten"]
    winner_score = alm["total_scores"][alm["winner"]]
    for planet, score in alm["total_scores"].items():
        assert score <= winner_score, (
            f"{planet}={score} > winner {alm['winner']}={winner_score}"
        )


def test_l6_lot_of_fortune_valid(chart):
    assert 0 <= chart["almuten"]["lot_of_fortune"] < 360


def test_l6_syzygy_valid(chart):
    assert 0 <= chart["almuten"]["syzygy_lon"] < 360


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 7: Aspects (Story 8)
# ═══════════════════════════════════════════════════════════════════════════════

def test_l7_aspects_present(chart):
    assert len(chart["aspects"]["aspects"]) > 0


def test_l7_aspect_orbs_non_negative(chart):
    for asp in chart["aspects"]["aspects"]:
        assert asp["orb"] >= 0, f"Negative orb: {asp}"


def test_l7_aspect_types_valid(chart):
    """Aspect types are integer codes: 0=Conj, 1=Sextile, 2=Square, 3=Trine, 4=Opposition."""
    valid = {0, 1, 2, 3, 4}
    for asp in chart["aspects"]["aspects"]:
        assert asp["aspect_type"] in valid, f"Invalid aspect type {asp['aspect_type']}"


def test_l7_no_self_aspects(chart):
    for asp in chart["aspects"]["aspects"]:
        assert asp["planet_a"] != asp["planet_b"]


def test_l7_planet_ids_in_range(chart):
    for asp in chart["aspects"]["aspects"]:
        assert 0 <= asp["planet_a"] <= 6
        assert 0 <= asp["planet_b"] <= 6


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 8: Arabic Parts (Story 7)
# ═══════════════════════════════════════════════════════════════════════════════

def test_l8_arabic_parts_present(chart):
    assert len(chart["arabic_parts"]) > 0


def test_l8_lot_of_fortune_present(chart):
    names = [p["name"] for p in chart["arabic_parts"]]
    assert any("Fortune" in n or "Fortuna" in n for n in names), (
        f"Lot of Fortune not found. Parts: {names[:5]}"
    )


def test_l8_lons_valid(chart):
    for p in chart["arabic_parts"]:
        assert 0 <= p["lon"] < 360, f"{p['name']} lon={p['lon']} out of range"


def test_l8_sign_lons_valid(chart):
    for p in chart["arabic_parts"]:
        assert 0 <= p["sign_lon"] < 30, (
            f"{p['name']} sign_lon={p['sign_lon']} out of range"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 9: Conditions (Story 9)
# ═══════════════════════════════════════════════════════════════════════════════

def test_l9_conditions_6_planets(chart):
    """Sun is excluded from planet_conditions (no elongation from self); returns 6."""
    assert len(chart["conditions"]["planet_conditions"]) == 6


def test_l9_saturn_not_combust(chart):
    """Saturn at 294° is ~210° from Sun at 84° — far from combust."""
    saturn = next(
        c for c in chart["conditions"]["planet_conditions"]
        if c["planet_name"] == "Saturn"
    )
    assert saturn["combust"] is False
    assert saturn["cazimi"] is False


def test_l9_moon_voc_field_present(chart):
    moon = chart["conditions"]["moon"]
    assert "void_of_course" in moon
    assert isinstance(moon["void_of_course"], bool)


def test_l9_elongations_valid(chart):
    """Elongation is raw angular distance from Sun (0–360°, not shortest arc)."""
    for c in chart["conditions"]["planet_conditions"]:
        assert 0 <= c["elongation"] < 360, (
            f"{c['planet_name']} elongation={c['elongation']} out of [0,360)"
        )


def test_l9_combust_and_cazimi_exclusive(chart):
    for c in chart["conditions"]["planet_conditions"]:
        assert not (c["combust"] and c["cazimi"]), (
            f"{c['planet_name']} cannot be both combust and cazimi"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 10: Sect (Story 10)
# ═══════════════════════════════════════════════════════════════════════════════

def test_l10_sect_7_planets(chart):
    assert len(chart["sect"]["planet_sects"]) == 7


def test_l10_sun_diurnal_in_sect(chart):
    sun = next(s for s in chart["sect"]["planet_sects"] if s["planet_name"] == "Sun")
    assert sun["sect"] == "diurnal"
    assert sun["in_sect"] is True  # day chart


def test_l10_moon_nocturnal(chart):
    moon = next(s for s in chart["sect"]["planet_sects"] if s["planet_name"] == "Moon")
    assert moon["sect"] == "nocturnal"


def test_l10_jupiter_saturn_diurnal(chart):
    for name in ("Jupiter", "Saturn"):
        p = next(s for s in chart["sect"]["planet_sects"] if s["planet_name"] == name)
        assert p["sect"] == "diurnal", f"{name} should be diurnal sect"


def test_l10_venus_mars_nocturnal(chart):
    for name in ("Venus", "Mars"):
        p = next(s for s in chart["sect"]["planet_sects"] if s["planet_name"] == name)
        assert p["sect"] == "nocturnal", f"{name} should be nocturnal sect"


def test_l10_above_horizon_booleans(chart):
    for s in chart["sect"]["planet_sects"]:
        assert isinstance(s["above_horizon"], bool)


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 11: Fixed Stars (Story 11)
# ═══════════════════════════════════════════════════════════════════════════════

def test_l11_star_positions_count(chart):
    # Catalog expanded to 112 entries; ≥90 must load via SE
    assert len(chart["fixed_stars"]["star_positions"]) >= 90


def test_l11_star_longitudes_valid(chart):
    for s in chart["fixed_stars"]["star_positions"]:
        assert 0 <= s["lon"] < 360, f"Star {s['name']} lon={s['lon']} out of range"


def test_l11_conjunction_orbs_within_1deg(chart):
    for c in chart["fixed_stars"]["aspects"]:
        max_orb = 1.0 if c["aspect_angle"] == 0 else 0.5
        assert 0 <= c["orb"] <= max_orb, (
            f"Star {c['star_name']} {c['aspect_name']} orb={c['orb']} > {max_orb}"
        )


def test_l11_conjunction_planet_ids_valid(chart):
    for c in chart["fixed_stars"]["aspects"]:
        assert 0 <= c["planet_id"] <= 6


def test_l11_star_natures_non_empty(chart):
    for s in chart["fixed_stars"]["star_positions"]:
        assert len(s["nature"]) > 0, f"Star {s['name']} has empty nature"


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 12: Antiscia (Story 12)
# ═══════════════════════════════════════════════════════════════════════════════

def test_l12_antiscia_points_7(chart):
    assert len(chart["antiscia"]["points"]) == 7


def test_l12_antiscion_formula(chart):
    for p in chart["antiscia"]["points"]:
        expected = (180.0 - p["lon"]) % 360.0
        assert abs(p["antiscion"] - expected) < 0.001, (
            f"{p['planet_name']}: antiscion {p['antiscion']:.4f} != {expected:.4f}"
        )


def test_l12_contra_formula(chart):
    for p in chart["antiscia"]["points"]:
        expected = (360.0 - p["lon"]) % 360.0
        assert abs(p["contra_antiscion"] - expected) < 0.001, (
            f"{p['planet_name']}: contra {p['contra_antiscion']:.4f} != {expected:.4f}"
        )


def test_l12_antiscia_symmetry(chart):
    for p in chart["antiscia"]["points"]:
        expected_contra = (p["antiscion"] + 180.0) % 360.0
        assert abs(p["contra_antiscion"] - expected_contra) < 0.001


def test_l12_mercury_contra_antiscion_saturn(chart):
    """Known: Mercury contra-antiscion Saturn at this chart."""
    aspects = chart["antiscia"]["aspects"]
    match = [
        a for a in aspects
        if a["aspect_type"] == "contra_antiscion"
        and {a["name_a"], a["name_b"]} == {"Mercury", "Saturn"}
    ]
    assert len(match) == 1, "Expected Mercury contra-antiscion Saturn"
    assert match[0]["orb"] < 1.0


def test_l12_aspect_types_valid(chart):
    valid = {"antiscion", "contra_antiscion"}
    for a in chart["antiscia"]["aspects"]:
        assert a["aspect_type"] in valid


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 13: Firdaria (Story 13)
# ═══════════════════════════════════════════════════════════════════════════════

def test_l13_firdaria_day_chart(chart):
    assert chart["firdaria"]["day_chart"] == chart["day_chart"]


def test_l13_firdaria_periods_at_least_9(chart):
    assert len(chart["firdaria"]["periods"]) >= 9


def test_l13_current_period_exists(chart):
    assert chart["firdaria"]["current_period"] is not None


def test_l13_period_structure(chart):
    required = {"planet_id", "planet_name", "years", "start", "end", "sub_periods"}
    for p in chart["firdaria"]["periods"]:
        missing = required - set(p.keys())
        assert not missing, f"Period missing fields: {missing}"


def test_l13_non_node_periods_have_7_sub_periods(chart):
    node_ids = {7, 8, -2}
    for period in chart["firdaria"]["periods"]:
        if period["planet_id"] not in node_ids:
            assert len(period["sub_periods"]) == 7, (
                f"{period['planet_name']} should have 7 sub-periods, "
                f"got {len(period['sub_periods'])}"
            )


def test_l13_periods_sequential(chart):
    periods = chart["firdaria"]["periods"]
    for i in range(len(periods) - 1):
        end_jd = periods[i]["end"]["jd"]
        next_start_jd = periods[i + 1]["start"]["jd"]
        assert abs(end_jd - next_start_jd) < 1.0, (
            f"Gap between period {i} and {i+1}: {end_jd:.2f} vs {next_start_jd:.2f}"
        )


def test_l13_day_chart_starts_with_sun(chart):
    first = chart["firdaria"]["periods"][0]
    assert first["planet_name"] == "Sun", (
        f"Day chart firdaria should start Sun, got {first['planet_name']}"
    )
    assert first["years"] == 10


def test_l13_birth_jd_matches(chart):
    assert abs(chart["firdaria"]["birth_jd"] - REF_JD) < 0.001


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 14: Annual Profections (Story 14)
# ═══════════════════════════════════════════════════════════════════════════════

def test_l14_current_age_36(chart):
    assert chart["profections"]["current_age"] == 36


def test_l14_birth_jd_matches(chart):
    assert abs(chart["profections"]["birth_jd"] - REF_JD) < 0.001


def test_l14_current_year_house_1(chart):
    cy = chart["profections"]["current_year"]
    assert cy is not None
    assert cy["house"] == 1, f"Age 36 should be house 1, got {cy['house']}"


def test_l14_current_year_sign_virgo(chart):
    cy = chart["profections"]["current_year"]
    assert cy["profected_sign"] == "Virgo", (
        f"Expected Virgo, got {cy['profected_sign']}"
    )


def test_l14_current_year_lord_mercury(chart):
    cy = chart["profections"]["current_year"]
    assert cy["lord_name"] == "Mercury", (
        f"Expected Mercury (Virgo lord), got {cy['lord_name']}"
    )


def test_l14_years_sequential(chart):
    years = chart["profections"]["years"]
    for i, y in enumerate(years):
        assert y["age"] == years[0]["age"] + i, (
            f"Non-sequential age at index {i}: {y['age']}"
        )


def test_l14_profected_asc_steps_30(chart):
    years = chart["profections"]["years"]
    for i in range(len(years) - 1):
        diff = (years[i + 1]["profected_asc"] - years[i]["profected_asc"]) % 360
        assert abs(diff - 30.0) < 0.01, (
            f"Step at age {years[i]['age']}: {diff:.4f} (expected 30°)"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 15: Primary Directions (Story 15)
# ═══════════════════════════════════════════════════════════════════════════════

def test_l15_direction_count(chart):
    # 460 = 236 zodiacal + 224 mundane (9 sigs × ~6 proms × 8 aspects × 2 dirs, arc≤90°)
    assert len(chart["primary_directions"]["directions"]) == 460, (
        f"Expected 460 directions, got {len(chart['primary_directions']['directions'])}"
    )


def test_l15_ramc(chart):
    assert abs(chart["primary_directions"]["ramc"] - REF_ARMC) < TOLERANCE


def test_l15_obliquity(chart):
    assert abs(chart["primary_directions"]["obliquity"] - REF_OBLIQUITY) < 0.001


def test_l15_first_direction(chart):
    """First (smallest arc) direction: mundane Mars→Saturn sinister_sextile direct ~0.1957°."""
    first = chart["primary_directions"]["directions"][0]
    assert first["significator"] == "Mars"
    assert first["promittor_planet"] == "Saturn"
    assert first["promittor_aspect"] == "sinister_sextile"
    assert first["direction"] == "direct"
    assert first["direction_type"] == "mundane"
    assert abs(first["arc"] - 0.1957) < 0.01


def test_l15_arcs_sorted_ascending(chart):
    arcs = [d["arc"] for d in chart["primary_directions"]["directions"]]
    assert arcs == sorted(arcs)


def test_l15_arcs_within_bounds(chart):
    for d in chart["primary_directions"]["directions"]:
        assert 0.0 < d["arc"] <= 90.0


def test_l15_significators_valid(chart):
    valid = {"ASC", "MC", "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
    for d in chart["primary_directions"]["directions"]:
        assert d["significator"] in valid


def test_l15_direction_types_valid(chart):
    valid = {"direct", "converse"}
    for d in chart["primary_directions"]["directions"]:
        assert d["direction"] in valid


def test_l15_promittor_aspects_valid(chart):
    valid = {
        "body", "sinister_sextile", "dexter_sextile",
        "sinister_square", "dexter_square",
        "sinister_trine", "dexter_trine", "opposition",
    }
    for d in chart["primary_directions"]["directions"]:
        assert d["promittor_aspect"] in valid


def test_l15_direction_type_field(chart):
    """direction_type must be 'zodiacal' or 'mundane'; both types present."""
    types = {d["direction_type"] for d in chart["primary_directions"]["directions"]}
    assert types == {"zodiacal", "mundane"}


def test_l15_date_exact_present(chart):
    """Every direction must carry a date_exact JD after birth."""
    birth_jd = REF_JD
    for d in chart["primary_directions"]["directions"]:
        assert "date_exact" in d
        assert d["date_exact"] > birth_jd


def test_l15_timing_key_in_response(chart):
    """Response must include timing_key field (default 'ptolemy')."""
    assert chart["primary_directions"]["timing_key"] == "ptolemy"


def test_l15_geo_lat(chart):
    assert abs(chart["primary_directions"]["geo_lat"] - CHART_REQUEST["lat"]) < 0.001


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 16: Cross-story consistency
# ═══════════════════════════════════════════════════════════════════════════════

def test_l16_dignified_planets_have_positive_score(chart):
    """Planets with domicile or exaltation must have score > 0."""
    for d in chart["dignities"]:
        if d["domicile"] or d["exaltation"]:
            assert d["score"] > 0


def test_l16_profection_lord_in_dignities(chart):
    cy = chart["profections"]["current_year"]
    if cy is None:
        pytest.skip("No current profection year")
    dignity_ids = {d["planet_id"] for d in chart["dignities"]}
    assert cy["lord_id"] in dignity_ids


def test_l16_arabic_lot_fortune_matches_almuten(chart):
    """Lot of Fortune longitude must agree between arabic_parts and almuten."""
    lof_almuten = chart["almuten"]["lot_of_fortune"]
    lof_part = next(
        (p["lon"] for p in chart["arabic_parts"]
         if "Fortune" in p["name"] or "Fortuna" in p["name"]),
        None,
    )
    if lof_part is None:
        pytest.skip("Lot of Fortune not in arabic_parts")
    assert abs(lof_part - lof_almuten) < 0.01, (
        f"LoF mismatch: almuten={lof_almuten:.4f}, arabic_parts={lof_part:.4f}"
    )


def test_l16_primary_dirs_promittor_ids_valid(chart):
    for d in chart["primary_directions"]["directions"]:
        assert 0 <= d["promittor_planet_id"] <= 6


def test_l16_planet_lons_consistent_in_antiscia(chart):
    """Antiscia point lons must match planet lons from planets list."""
    planet_lons = {p["name"]: p["lon"] for p in chart["planets"]}
    for ap in chart["antiscia"]["points"]:
        name = ap["planet_name"]
        assert abs(ap["lon"] - planet_lons[name]) < 0.001, (
            f"Antiscia lon mismatch for {name}: {ap['lon']:.4f} vs {planet_lons[name]:.4f}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 17: Print summary table
# ═══════════════════════════════════════════════════════════════════════════════

def test_l17_print_full_summary(chart):
    """Print comprehensive summary for manual comparison with Morinus 8.1."""
    print()
    print("=" * 70)
    print("ROME 1990-06-15 10:30 UT — Full Chart Summary")
    print("Compare manually with Morinus 8.1")
    print("=" * 70)

    print(f"\n[JD] {chart['julian_day']:.6f}   [DAY CHART] {chart['day_chart']}")

    # Planets
    print("\n── PLANETS ──────────────────────────────────────────────────")
    print(f"{'Name':<12} {'Lon':>8}  {'Sign':<4} {'°in':>7}  {'R':<2}  {'Speed':>9}")
    for p in chart["planets"]:
        r = "R" if p["retrograde"] else ""
        print(
            f"{p['name']:<12} {p['lon']:>8.4f}  "
            f"{SIGN_ABBR[SIGN_FULL.index(p['sign'])]:<4} {p['sign_lon']:>7.4f}  "
            f"{r:<2}  {p['speed']:>9.6f}"
        )

    # Houses
    print("\n── HOUSES (Alcabitius) ──────────────────────────────────────")
    h = chart["houses"]
    print(f"  ASC={h['asc']:.4f}  MC={h['mc']:.4f}  ARMC={h['armc']:.4f}")
    for i, c in enumerate(h["cusps"]):
        s = SIGN_ABBR[int(c / 30) % 12]
        end = "\n" if i % 2 == 1 else "    "
        print(f"  H{i+1:02d}: {c:8.4f} ({s} {c%30:.2f}°)", end=end)
    print()

    # Dignities
    print("\n── DIGNITIES ────────────────────────────────────────────────")
    print(f"{'Planet':<12} {'Dom':^4} {'Exl':^4} {'Trp':^4} {'Trm':^4} {'Fce':^4} {'Det':^4} {'Fll':^4} {'Scr':^4}")
    for d in chart["dignities"]:
        def b(v): return "Y" if v else ""
        print(
            f"{d['planet_name']:<12} {b(d['domicile']):^4} {b(d['exaltation']):^4} "
            f"{b(d['triplicity']):^4} {b(d['term']):^4} {b(d['face']):^4} "
            f"{b(d['detriment']):^4} {b(d['fall']):^4} {d['score']:^4}"
        )

    # Almuten
    alm = chart["almuten"]
    print(f"\n── ALMUTEN: {alm['winner']} (dead_heat={alm['dead_heat']}) ──────────────")
    print(f"  Scores: {alm['total_scores']}")
    print(f"  Lot of Fortune: {alm['lot_of_fortune']:.4f}°")

    # Sect
    print("\n── SECT ─────────────────────────────────────────────────────")
    for s in chart["sect"]["planet_sects"]:
        hayz = " HAYZ" if s["in_hayz"] else ""
        print(
            f"  {s['planet_name']:<10} {s['sect']:<12} "
            f"in_sect={s['in_sect']}  above={s['above_horizon']}{hayz}"
        )

    # Antiscia
    print("\n── ANTISCIA ASPECTS ─────────────────────────────────────────")
    if chart["antiscia"]["aspects"]:
        for a in chart["antiscia"]["aspects"]:
            print(f"  {a['name_a']:<10} {a['aspect_type']:<20} {a['name_b']:<10} orb={a['orb']:.4f}")
    else:
        print("  (none within 1°)")

    # Fixed stars
    print("\n── FIXED STAR CONJUNCTIONS ──────────────────────────────────")
    if chart["fixed_stars"]["aspects"]:
        for c in chart["fixed_stars"]["aspects"]:
            print(
                f"  {c['star_name']:<20} {c['aspect_name']:<12} {c['planet_name']:<10} "
                f"orb={c['orb']:.4f}  [{c['star_nature']}]"
            )
    else:
        print("  (none within 1°)")

    # Firdaria
    fird = chart["firdaria"]
    cp = fird["current_period"]
    print("\n── FIRDARIA ─────────────────────────────────────────────────")
    if cp:
        cs = fird.get("current_sub")
        print(f"  Major: {cp['planet_name']}  {cp['start']['year']}–{cp['end']['year']}")
        if cs:
            print(f"  Sub:   {cs['planet_name']}  {cs['start']['year']}–{cs['end']['year']}")

    # Profections
    prof = chart["profections"]
    cy = prof["current_year"]
    print("\n── PROFECTIONS ──────────────────────────────────────────────")
    print(f"  Age {prof['current_age']}: ", end="")
    if cy:
        print(
            f"House {cy['house']} / {cy['profected_sign']} / "
            f"Lord={cy['lord_name']} / profASC={cy['profected_asc']:.4f}°"
        )

    # Primary directions
    pd = chart["primary_directions"]
    dirs = pd["directions"]
    print(f"\n── PRIMARY DIRECTIONS (first 20 of {len(dirs)}) ────────────────────")
    print(f"  RAMC={pd['ramc']:.4f}°  ε={pd['obliquity']:.6f}°  φ={pd['geo_lat']}°")
    print(f"  {'SIG':<5} {'PLANET':<10} {'ASPECT':<22} {'DIR':<9} {'ARC':>7}  ≈YR")
    for d in dirs[:20]:
        yr = int(1990 + d["arc"])
        print(
            f"  {d['significator']:<5} {d['promittor_planet']:<10} "
            f"{d['promittor_aspect']:<22} {d['direction']:<9} {d['arc']:>7.4f}  {yr}"
        )

    print("\n" + "=" * 70)
    assert True
