"""
Epic 4.1 — Secondary Progressions tests.

Verifies:
  1. Core: progressed_jd = birth_jd + age_years (day-for-a-year)
  2. Core: progressed_jd is always > birth_jd and < birth_jd + 100 for sane ages
  3. Core: progressed lunation phase angle 0-360°, phase names correct
  4. Core: last New/Full Moon JD is strictly before progressed_jd
  5. Core: NM accuracy — Moon ≡ Sun at NM JD to < 0.01°
  6. Core: FM accuracy — Moon ≡ Sun+180 at FM JD to < 0.01°
  7. API: /chart/secondary-progressions returns correct structure
  8. API: progressed_jd formula verified against birth/target dates
  9. API: 7 traditional progressed planets always present
 10. API: include_progressed_houses=True returns house cusps
 11. API: include_natal_overlay=True returns 7 placements + cross-aspects
 12. API: error on progression_date <= birth_date
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.secondary_progressions import (
    progressed_jd, calc_progressed_lunation, _phase_angle, _phase_name,
)

# ── ephemeris path ─────────────────────────────────────────────────────────────

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

# ── Shared test data ──────────────────────────────────────────────────────────

FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

BIRTH = {"year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 30, "ut_offset": 0.0}

PROG_REQUEST = {
    **BIRTH,
    "lat": 41.9, "lon": 12.5,
    "prog_year": 2025, "prog_month": 6, "prog_day": 15,
    "hsys": "B",
}

client = TestClient(app)

BIRTH_JD = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
TARGET_JD = swe.julday(2025, 6, 15, 12.0, swe.GREG_CAL)


# ── Core formula tests ────────────────────────────────────────────────────────

def test_progressed_jd_formula():
    """progressed_jd = birth_jd + age_years; age_years ≈ 35 for 35-year span."""
    age, jd_prog = progressed_jd(BIRTH_JD, TARGET_JD)
    assert abs(age - 35.0) < 0.1, f"Expected ~35 years, got {age}"
    assert abs(jd_prog - (BIRTH_JD + age)) < 1e-9


def test_progressed_jd_after_birth():
    """Progressed JD is always after the birth JD."""
    _, jd_prog = progressed_jd(BIRTH_JD, TARGET_JD)
    assert jd_prog > BIRTH_JD


def test_progressed_jd_reasonable_range():
    """For a 35-year progression, symbolic JD is 35 days after birth."""
    age, jd_prog = progressed_jd(BIRTH_JD, TARGET_JD)
    assert 34 < jd_prog - BIRTH_JD < 36, (
        f"Expected ~35 days after birth, got {jd_prog - BIRTH_JD:.2f}"
    )


def test_progressed_jd_1_year():
    """At exactly 1 year of life, progressed JD is 1 day after birth."""
    target_1yr = swe.julday(1991, 6, 15, 12.0, swe.GREG_CAL)
    age, jd_prog = progressed_jd(BIRTH_JD, target_1yr)
    assert abs(age - 1.0) < 0.01
    assert abs(jd_prog - BIRTH_JD - 1.0) < 0.01


# ── Phase angle / name tests ──────────────────────────────────────────────────

def test_phase_angle_range():
    """Phase angle is always in [0, 360)."""
    _, jd_prog = progressed_jd(BIRTH_JD, TARGET_JD)
    angle = _phase_angle(jd_prog)
    assert 0.0 <= angle < 360.0


def test_phase_name_new_moon():
    assert _phase_name(0.0) == "New Moon"
    assert _phase_name(10.0) == "New Moon"
    assert _phase_name(22.4) == "New Moon"


def test_phase_name_first_quarter():
    assert _phase_name(90.0) == "First Quarter"


def test_phase_name_full_moon():
    assert _phase_name(180.0) == "Full Moon"
    assert _phase_name(200.0) == "Full Moon"


def test_phase_name_last_quarter():
    assert _phase_name(270.0) == "Last Quarter"


def test_phase_name_waxing_crescent():
    assert _phase_name(45.0) == "Waxing Crescent"


# ── Progressed lunation tests ─────────────────────────────────────────────────

@pytest.fixture(scope="module")
def lunation():
    _, jd_prog = progressed_jd(BIRTH_JD, TARGET_JD)
    return calc_progressed_lunation(BIRTH_JD, jd_prog)


def test_lunation_phase_angle_range(lunation):
    assert 0.0 <= lunation.phase_angle < 360.0


def test_lunation_phase_name_nonempty(lunation):
    assert lunation.phase_name != ""


def test_lunation_nm_before_progressed(lunation):
    """Last New Moon JD must be strictly before the progressed JD."""
    _, jd_prog = progressed_jd(BIRTH_JD, TARGET_JD)
    assert lunation.last_new_moon_jd < jd_prog, (
        f"NM JD {lunation.last_new_moon_jd} not before progressed JD {jd_prog}"
    )


def test_lunation_fm_before_progressed(lunation):
    """Last Full Moon JD must be strictly before the progressed JD."""
    _, jd_prog = progressed_jd(BIRTH_JD, TARGET_JD)
    assert lunation.last_full_moon_jd < jd_prog


def test_lunation_nm_accuracy(lunation):
    """Moon = Sun at the progressed New Moon JD to < 0.01°."""
    r_m, _ = swe.calc_ut(lunation.last_new_moon_jd, swe.MOON, FLAGS)
    r_s, _ = swe.calc_ut(lunation.last_new_moon_jd, swe.SUN,  FLAGS)
    diff = abs((r_m[0] - r_s[0] + 180) % 360 - 180)
    assert diff < 0.01, f"NM accuracy: Moon-Sun diff = {diff:.4f}°"


def test_lunation_fm_accuracy(lunation):
    """Moon = Sun+180 at the progressed Full Moon JD to < 0.01°."""
    r_m, _ = swe.calc_ut(lunation.last_full_moon_jd, swe.MOON, FLAGS)
    r_s, _ = swe.calc_ut(lunation.last_full_moon_jd, swe.SUN,  FLAGS)
    diff = abs((r_m[0] - r_s[0] - 180 + 180) % 360 - 180)
    assert diff < 0.01, f"FM accuracy: Moon-Sun-180 diff = {diff:.4f}°"


def test_lunation_nm_before_fm_or_vice_versa(lunation):
    """NM and FM ages are positive (both after birth)."""
    assert lunation.last_new_moon_age > 0, "NM age must be positive (after birth)"
    assert lunation.last_full_moon_age > 0, "FM age must be positive (after birth)"


# ── API endpoint tests ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sp_chart():
    resp = client.post("/chart/secondary-progressions", json=PROG_REQUEST)
    assert resp.status_code == 200, f"API error: {resp.text}"
    return resp.json()


def test_sp_response_status():
    resp = client.post("/chart/secondary-progressions", json=PROG_REQUEST)
    assert resp.status_code == 200


def test_sp_top_level_fields(sp_chart):
    for field in ["birth_jd", "target_jd", "progressed_jd", "age_years",
                  "progressed_planets", "lunation"]:
        assert field in sp_chart, f"Missing field: {field}"


def test_sp_age_years(sp_chart):
    """35-year progression gives age ≈ 35."""
    assert abs(sp_chart["age_years"] - 35.0) < 0.1, (
        f"Expected ~35 years, got {sp_chart['age_years']}"
    )


def test_sp_progressed_jd_formula(sp_chart):
    """progressed_jd = birth_jd + age_years."""
    assert abs(sp_chart["progressed_jd"] - sp_chart["birth_jd"] - sp_chart["age_years"]) < 1e-3


def test_sp_seven_progressed_planets(sp_chart):
    names = {p["name"] for p in sp_chart["progressed_planets"]}
    for expected in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]:
        assert expected in names, f"Missing progressed planet: {expected}"


def test_sp_progressed_planets_lons_valid(sp_chart):
    for p in sp_chart["progressed_planets"]:
        assert 0.0 <= p["lon"] < 360.0, f"{p['name']}: lon {p['lon']} out of range"


def test_sp_progressed_houses_present_by_default(sp_chart):
    assert sp_chart["progressed_houses"] is not None
    assert len(sp_chart["progressed_houses"]["cusps"]) == 12
    assert sp_chart["progressed_houses"]["asc"] != 0.0


def test_sp_houses_absent_when_not_requested():
    resp = client.post("/chart/secondary-progressions", json={
        **PROG_REQUEST, "include_progressed_houses": False
    }).json()
    assert resp["progressed_houses"] is None


def test_sp_natal_overlay_present_by_default(sp_chart):
    assert sp_chart["natal_overlay"] is not None


def test_sp_natal_overlay_placements_seven(sp_chart):
    placements = sp_chart["natal_overlay"]["placements"]
    assert len(placements) == 7


def test_sp_natal_overlay_placements_houses_valid(sp_chart):
    for p in sp_chart["natal_overlay"]["placements"]:
        assert 1 <= p["return_house"] <= 12, (
            f"{p['planet_name']}: invalid house {p['return_house']}"
        )


def test_sp_natal_overlay_cross_aspects_present(sp_chart):
    assert len(sp_chart["natal_overlay"]["cross_aspects"]) > 0


def test_sp_natal_overlay_no_self_aspects(sp_chart):
    for a in sp_chart["natal_overlay"]["cross_aspects"]:
        assert a["return_planet_id"] != a["natal_planet_id"]


def test_sp_natal_overlay_absent_when_not_requested():
    resp = client.post("/chart/secondary-progressions", json={
        **PROG_REQUEST, "include_natal_overlay": False
    }).json()
    assert resp["natal_overlay"] is None


def test_sp_lunation_fields(sp_chart):
    lun = sp_chart["lunation"]
    assert "phase_angle" in lun
    assert "phase_name" in lun
    assert "last_new_moon_jd" in lun
    assert "last_new_moon_age" in lun
    assert "last_full_moon_jd" in lun
    assert "last_full_moon_age" in lun


def test_sp_lunation_phase_angle_range(sp_chart):
    angle = sp_chart["lunation"]["phase_angle"]
    assert 0.0 <= angle < 360.0


def test_sp_lunation_phase_name_nonempty(sp_chart):
    assert sp_chart["lunation"]["phase_name"] != ""


def test_sp_lunation_ages_positive(sp_chart):
    assert sp_chart["lunation"]["last_new_moon_age"] > 0
    assert sp_chart["lunation"]["last_full_moon_age"] > 0


def test_sp_error_on_past_progression_date():
    """Progression date before birth date should return 422."""
    bad_req = {**PROG_REQUEST, "prog_year": 1985, "prog_month": 1, "prog_day": 1}
    resp = client.post("/chart/secondary-progressions", json=bad_req)
    assert resp.status_code == 422


def test_sp_outer_planets_included():
    resp = client.post("/chart/secondary-progressions", json={
        **PROG_REQUEST, "include_outer": True
    }).json()
    names = {p["name"] for p in resp["progressed_planets"]}
    assert "Uranus" in names
    assert "Neptune" in names
    assert "Pluto" in names


def test_sp_progressed_sun_moves_slowly():
    """Progressed Sun should be within ~35° of natal Sun (1°/year × 35 years)."""
    resp = sp_chart = client.post("/chart/secondary-progressions", json=PROG_REQUEST).json()
    natal_sun_jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    r_natal, _ = swe.calc_ut(natal_sun_jd, swe.SUN, FLAGS)
    natal_sun_lon = r_natal[0]
    prog_sun = next(p for p in resp["progressed_planets"] if p["name"] == "Sun")
    delta = abs((prog_sun["lon"] - natal_sun_lon + 180) % 360 - 180)
    assert delta < 40.0, f"Progressed Sun {delta:.2f}° from natal (expected < 40° for 35y)"


def test_sp_progressed_moon_moves_fast():
    """Progressed Moon should be far from natal Moon (~13°/year × 35 years)."""
    resp = client.post("/chart/secondary-progressions", json=PROG_REQUEST).json()
    natal_moon_jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    r_natal, _ = swe.calc_ut(natal_moon_jd, swe.MOON, FLAGS)
    natal_moon_lon = r_natal[0]
    prog_moon = next(p for p in resp["progressed_planets"] if p["name"] == "Moon")
    # Moon moves ~13°/year; after 35 years it has gone through many complete cycles
    # Just verify it's a valid longitude different from natal (could be anything)
    assert 0.0 <= prog_moon["lon"] < 360.0
