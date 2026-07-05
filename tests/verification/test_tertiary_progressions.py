"""
Epic 4.3 — Tertiary Progressions tests.

Verifies:
  1. Core: tertiary_jd formula (day-for-a-month)
     sidereal: age_months = (target - birth) / 27.32158
     synodic:  age_months = (target - birth) / 29.53059
  2. jd_prog = birth_jd + age_months for both month types
  3. sidereal gives MORE months than synodic for same span
  4. sidereal progressed_jd < synodic progressed_jd (smaller denominator → more months)
  5. For 35-year span: ~433 sidereal months, ~420 synodic months
  6. API: /chart/tertiary-progressions returns all required fields
  7. API: month_type and month_days match the selected type
  8. API: 7 traditional progressed planets always present
  9. API: progressed_houses present by default, absent when disabled
 10. API: natal_overlay placements and cross-aspects correct
 11. API: lunation phase angle 0-360°
 12. API: sidereal vs synodic produce different progressed_jd values
 13. API: error on date before birth
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.secondary_progressions import (
    tertiary_jd, SIDEREAL_MONTH, SYNODIC_MONTH,
)

# ── ephemeris path ─────────────────────────────────────────────────────────────

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

# ── Shared test data ──────────────────────────────────────────────────────────

BIRTH = {"year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 30, "ut_offset": 0.0}

TP_REQUEST = {
    **BIRTH,
    "lat": 41.9, "lon": 12.5,
    "prog_year": 2025, "prog_month": 6, "prog_day": 15,
    "hsys": "B",
}

client = TestClient(app)

BIRTH_JD  = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
TARGET_JD = swe.julday(2025, 6, 15, 12.0, swe.GREG_CAL)
SPAN_DAYS = TARGET_JD - BIRTH_JD  # ~35 years in days


# ── Core formula tests ────────────────────────────────────────────────────────

def test_tertiary_jd_sidereal_formula():
    age, jd_prog, month_days = tertiary_jd(BIRTH_JD, TARGET_JD, "sidereal")
    assert abs(month_days - SIDEREAL_MONTH) < 1e-6
    expected_age = SPAN_DAYS / SIDEREAL_MONTH
    assert abs(age - expected_age) < 1e-6
    assert abs(jd_prog - (BIRTH_JD + expected_age)) < 1e-9


def test_tertiary_jd_synodic_formula():
    age, jd_prog, month_days = tertiary_jd(BIRTH_JD, TARGET_JD, "synodic")
    assert abs(month_days - SYNODIC_MONTH) < 1e-6
    expected_age = SPAN_DAYS / SYNODIC_MONTH
    assert abs(age - expected_age) < 1e-6
    assert abs(jd_prog - (BIRTH_JD + expected_age)) < 1e-9


def test_tertiary_sidereal_more_months_than_synodic():
    """Sidereal month shorter → more months in same time span."""
    age_sid, _, _ = tertiary_jd(BIRTH_JD, TARGET_JD, "sidereal")
    age_syn, _, _ = tertiary_jd(BIRTH_JD, TARGET_JD, "synodic")
    assert age_sid > age_syn, (
        f"Sidereal months ({age_sid:.2f}) should exceed synodic ({age_syn:.2f})"
    )


def test_tertiary_sidereal_jd_after_synodic_jd():
    """More months in sidereal → higher progressed_jd."""
    _, jd_sid, _ = tertiary_jd(BIRTH_JD, TARGET_JD, "sidereal")
    _, jd_syn, _ = tertiary_jd(BIRTH_JD, TARGET_JD, "synodic")
    assert jd_sid > jd_syn


def test_tertiary_approx_months_35_years():
    """35 years ≈ 468 sidereal months (365.25/27.32×35), ≈ 433 synodic months."""
    age_sid, _, _ = tertiary_jd(BIRTH_JD, TARGET_JD, "sidereal")
    age_syn, _, _ = tertiary_jd(BIRTH_JD, TARGET_JD, "synodic")
    assert 460 < age_sid < 475, f"Sidereal months: {age_sid:.1f}"
    assert 425 < age_syn < 440, f"Synodic months: {age_syn:.1f}"


def test_tertiary_jd_after_birth():
    _, jd_prog, _ = tertiary_jd(BIRTH_JD, TARGET_JD)
    assert jd_prog > BIRTH_JD


def test_tertiary_jd_default_is_sidereal():
    age_default, jd_default, _ = tertiary_jd(BIRTH_JD, TARGET_JD)
    age_sid, jd_sid, _ = tertiary_jd(BIRTH_JD, TARGET_JD, "sidereal")
    assert abs(age_default - age_sid) < 1e-9
    assert abs(jd_default - jd_sid) < 1e-9


# ── API tests: sidereal ───────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def tp_sid():
    resp = client.post("/chart/tertiary-progressions",
                       json={**TP_REQUEST, "month_type": "sidereal"})
    assert resp.status_code == 200, f"API error: {resp.text}"
    return resp.json()


def test_tp_response_status():
    resp = client.post("/chart/tertiary-progressions", json=TP_REQUEST)
    assert resp.status_code == 200


def test_tp_top_level_fields(tp_sid):
    for f in ["birth_jd", "target_jd", "progressed_jd", "age_months",
              "month_type", "month_days", "progressed_planets", "lunation"]:
        assert f in tp_sid, f"Missing field: {f}"


def test_tp_month_type_sidereal(tp_sid):
    assert tp_sid["month_type"] == "sidereal"
    assert abs(tp_sid["month_days"] - SIDEREAL_MONTH) < 0.001


def test_tp_age_months_approx_468(tp_sid):
    assert 460 < tp_sid["age_months"] < 475, (
        f"Expected ~468 sidereal months, got {tp_sid['age_months']:.1f}"
    )


def test_tp_progressed_jd_formula(tp_sid):
    expected = tp_sid["birth_jd"] + tp_sid["age_months"]
    assert abs(tp_sid["progressed_jd"] - expected) < 1e-3


def test_tp_seven_planets(tp_sid):
    names = {p["name"] for p in tp_sid["progressed_planets"]}
    for n in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]:
        assert n in names


def test_tp_planet_lons_valid(tp_sid):
    for p in tp_sid["progressed_planets"]:
        assert 0.0 <= p["lon"] < 360.0


def test_tp_progressed_houses_present_by_default(tp_sid):
    assert tp_sid["progressed_houses"] is not None
    assert len(tp_sid["progressed_houses"]["cusps"]) == 12


def test_tp_natal_overlay_present_by_default(tp_sid):
    assert tp_sid["natal_overlay"] is not None
    assert len(tp_sid["natal_overlay"]["placements"]) == 7


def test_tp_overlay_houses_valid(tp_sid):
    for p in tp_sid["natal_overlay"]["placements"]:
        assert 1 <= p["return_house"] <= 12


def test_tp_overlay_cross_aspects_present(tp_sid):
    assert len(tp_sid["natal_overlay"]["cross_aspects"]) > 0


def test_tp_overlay_no_self_aspects(tp_sid):
    for a in tp_sid["natal_overlay"]["cross_aspects"]:
        assert a["return_planet_id"] != a["natal_planet_id"]


def test_tp_lunation_fields(tp_sid):
    lun = tp_sid["lunation"]
    assert 0.0 <= lun["phase_angle"] < 360.0
    assert lun["phase_name"] != ""
    assert lun["last_new_moon_age"] > 0
    assert lun["last_full_moon_age"] > 0


def test_tp_lunation_nm_before_progressed(tp_sid):
    """Last NM progressed JD must be before the current progressed JD."""
    assert tp_sid["lunation"]["last_new_moon_jd"] < tp_sid["progressed_jd"]


def test_tp_lunation_fm_before_progressed(tp_sid):
    assert tp_sid["lunation"]["last_full_moon_jd"] < tp_sid["progressed_jd"]


# ── API tests: synodic ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def tp_syn():
    resp = client.post("/chart/tertiary-progressions",
                       json={**TP_REQUEST, "month_type": "synodic"})
    assert resp.status_code == 200, f"API error: {resp.text}"
    return resp.json()


def test_tp_month_type_synodic(tp_syn):
    assert tp_syn["month_type"] == "synodic"
    assert abs(tp_syn["month_days"] - SYNODIC_MONTH) < 0.001


def test_tp_age_months_approx_433(tp_syn):
    assert 425 < tp_syn["age_months"] < 440


def test_tp_sidereal_vs_synodic_different_jd(tp_sid, tp_syn):
    """Sidereal and synodic produce different progressed JDs."""
    diff = abs(tp_sid["progressed_jd"] - tp_syn["progressed_jd"])
    assert diff > 1.0, f"Expected >1 day difference, got {diff:.4f}"


def test_tp_sidereal_jd_greater_than_synodic(tp_sid, tp_syn):
    assert tp_sid["progressed_jd"] > tp_syn["progressed_jd"]


# ── Options tests ─────────────────────────────────────────────────────────────

def test_tp_houses_absent_when_disabled():
    resp = client.post("/chart/tertiary-progressions",
                       json={**TP_REQUEST, "include_progressed_houses": False}).json()
    assert resp["progressed_houses"] is None


def test_tp_overlay_absent_when_disabled():
    resp = client.post("/chart/tertiary-progressions",
                       json={**TP_REQUEST, "include_natal_overlay": False}).json()
    assert resp["natal_overlay"] is None


def test_tp_outer_planets():
    resp = client.post("/chart/tertiary-progressions",
                       json={**TP_REQUEST, "include_outer": True}).json()
    names = {p["name"] for p in resp["progressed_planets"]}
    assert "Uranus" in names and "Neptune" in names


def test_tp_error_on_past_date():
    bad = {**TP_REQUEST, "prog_year": 1985}
    resp = client.post("/chart/tertiary-progressions", json=bad)
    assert resp.status_code == 422
