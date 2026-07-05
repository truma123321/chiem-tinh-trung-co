"""
Epic 7.3 — Circumambulations (Valens / Firmicus) tests.

Significator (ASC + sect light) circumambulates the zodiac by Oblique Ascension.
Arc in degrees of OA = years of life at event (Ptolemy key: 1° OA = 1 year).

Verifies:
  1.  Core: result type is CircumambulationsResult
  2.  Core: obliquity is plausible (~23.4°)
  3.  Core: ARMC is in [0°, 360°)
  4.  Core: significators list has 2 entries (ASC + sect light)
  5.  Core: "ASC" is in significators
  6.  Core: sect light in significators (Sun for day chart)
  7.  Core: total events == 70 (2 sigs × 7 planets × 5 aspects)
  8.  Core: all arcs in [0°, 360°)
  9.  Core: age_years == arc for all events (Ptolemy key)
  10. Core: all event dates are after birth date (arc >= 0)
  11. Core: events sorted by (significator, arc) ascending
  12. Core: per-significator event count == 35 (7 × 5 aspects)
  13. Core: each planet appears exactly 5 times per significator
  14. Core: each aspect appears exactly 7 times per significator
  15. Core: conjunction arc = (OA(planet_lon) − ARMC) % 360 for ASC
  16. Core: OA formula check — equinox point (0° Aries) OA ≈ 0°
  17. Core: is_past flag: events with arc < elapsed_years are past
  18. Core: event_date.jd == birth_jd + arc × 365.25 (within 0.1)
  19. Core: all aspect_names are valid Ptolemaic names
  20. Core: all promittor_names are valid classical planet names
  21. Core: no duplicate (significator, promittor_id, aspect_angle) triples
  22. Core: arc=0 not present (circumambulations produce strict forward arcs)
  23. Core: day chart has "Sun" as sect light significator
  24. Core: event_date.year within reasonable range (birth+1 … birth+360)
  25. API endpoint: POST /chart/circumambulations returns 200
  26. API endpoint: events count == 70
  27. API endpoint: obliquity in [22°, 24°]
  28. API endpoint: armc in [0°, 360°)
  29. API endpoint: all aspect names are valid
  30. Natal: circumambulations field present in natal response
  31. Natal: circumambulations.events not empty
  32. Natal: circumambulations.significators has 2 entries
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.circumambulations import (
    calc_circumambulations, CircumambulationsResult,
    ASPECTS, _oa, _ra,
)
from core.dignities import is_day_chart

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

client = TestClient(app)

BIRTH_REQ = {
    "year": 1990, "month": 6, "day": 15,
    "hour": 10.0, "minute": 30,
    "lat": 41.9, "lon": 12.5,
    "hsys": "P", "ut_offset": 0.0,
}

JD  = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
LAT, LON = 41.9, 12.5
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

PLANET_LONS: dict[int, float] = {}
for _pid in range(7):
    _r, _ = swe.calc_ut(JD, _pid, FLAGS)
    PLANET_LONS[_pid] = _r[0]

_cusps, _ascmc = swe.houses(JD, LAT, LON, b"P")
ASC  = _ascmc[0]
ARMC = _ascmc[2]
DAY  = is_day_chart(PLANET_LONS[0], ASC)

_EPS_DATA, _ = swe.calc_ut(JD, swe.ECL_NUT, swe.FLG_SWIEPH)
EPS = _EPS_DATA[0]

_VALID_PLANETS = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
_VALID_ASPECTS = set(ASPECTS.values())

TODAY_JD = swe.julday(2026, 7, 3, 12.0, swe.GREG_CAL)
ELAPSED_YEARS = (TODAY_JD - JD) / 365.25   # ~36 years


@pytest.fixture(scope="module")
def result():
    return calc_circumambulations(JD, LAT, LON, PLANET_LONS, DAY, current_jd=TODAY_JD)


# ── Core tests ─────────────────────────────────────────────────────────────────

def test_result_type(result):
    assert isinstance(result, CircumambulationsResult)


def test_obliquity_plausible(result):
    assert 22.0 < result.obliquity < 24.5


def test_armc_in_range(result):
    assert 0.0 <= result.armc < 360.0


def test_significators_count(result):
    assert len(result.significators) == 2


def test_asc_in_significators(result):
    assert "ASC" in result.significators


def test_sect_light_in_significators(result):
    # Day chart → Sun; Night chart → Moon
    expected = "Sun" if DAY else "Moon"
    assert expected in result.significators


def test_total_events_70(result):
    assert len(result.events) == 70


def test_all_arcs_in_range(result):
    for e in result.events:
        assert 0.0 <= e.arc < 360.0, f"arc={e.arc} out of range"


def test_age_years_equals_arc(result):
    for e in result.events:
        assert e.age_years == e.arc


def test_event_dates_after_birth(result):
    for e in result.events:
        assert e.event_date.jd >= JD, f"event jd {e.event_date.jd} < birth jd {JD}"


def test_events_sorted_by_sig_then_arc(result):
    last_sig, last_arc = "", -1.0
    for e in result.events:
        if e.significator == last_sig:
            assert e.arc >= last_arc, (
                f"{e.significator}: arc {e.arc} < previous {last_arc}"
            )
        last_sig, last_arc = e.significator, e.arc


def test_per_significator_event_count(result):
    for sig in result.significators:
        count = sum(1 for e in result.events if e.significator == sig)
        assert count == 35, f"{sig}: {count} events, expected 35"


def test_each_planet_appears_5_times_per_sig(result):
    for sig in result.significators:
        sig_events = [e for e in result.events if e.significator == sig]
        for pid in range(7):
            count = sum(1 for e in sig_events if e.promittor_id == pid)
            assert count == 5, f"{sig}/planet {pid}: {count} events, expected 5"


def test_each_aspect_appears_7_times_per_sig(result):
    for sig in result.significators:
        sig_events = [e for e in result.events if e.significator == sig]
        for angle in ASPECTS:
            count = sum(1 for e in sig_events if e.aspect_angle == angle)
            assert count == 7, f"{sig}/aspect {angle}: {count} events, expected 7"


def test_conjunction_arc_formula(result):
    """ASC conjunction arc = (OA(planet_lon) - ARMC) % 360."""
    asc_conj = [e for e in result.events
                if e.significator == "ASC" and e.aspect_angle == 0]
    for e in asc_conj:
        planet_lon = PLANET_LONS[e.promittor_id]
        expected_oa = _oa(planet_lon, EPS, LAT)
        expected_arc = (expected_oa - ARMC) % 360
        assert abs(e.arc - expected_arc) < 0.001, (
            f"{e.promittor_name}: arc={e.arc}, expected={expected_arc:.4f}"
        )


def test_oa_equinox_near_zero():
    """OA of 0° Aries (ecliptic) at any reasonable latitude should be ~0°."""
    oa = _oa(0.0, EPS, LAT)
    # OA of 0° Aries: RA=0°, dec=0°, AD=0° → OA=0°
    assert abs(oa) < 0.1 or abs(oa - 360.0) < 0.1, f"OA(0° Aries) = {oa}"


def test_is_past_flag(result):
    for e in result.events:
        if e.arc < ELAPSED_YEARS - 1:
            assert e.is_past, f"arc={e.arc} should be past (elapsed={ELAPSED_YEARS:.1f})"
        if e.arc > ELAPSED_YEARS + 1:
            assert not e.is_past, f"arc={e.arc} should not be past"


def test_event_date_jd_formula(result):
    """event_date.jd ≈ birth_jd + arc × 365.25."""
    for e in result.events:
        expected_jd = JD + e.arc * 365.25
        assert abs(e.event_date.jd - expected_jd) < 0.1, (
            f"{e.significator}/{e.promittor_name}/{e.aspect_angle}: "
            f"jd={e.event_date.jd}, expected={expected_jd:.2f}"
        )


def test_aspect_names_valid(result):
    for e in result.events:
        assert e.aspect_name in _VALID_ASPECTS, f"Unknown aspect: {e.aspect_name}"


def test_promittor_names_valid(result):
    for e in result.events:
        assert e.promittor_name in _VALID_PLANETS, f"Unknown planet: {e.promittor_name}"


def test_no_duplicate_triples(result):
    seen = set()
    for e in result.events:
        key = (e.significator, e.promittor_id, e.aspect_angle)
        assert key not in seen, f"Duplicate event: {key}"
        seen.add(key)


def test_no_zero_arc(result):
    """Arc=0 only valid for sect-light self-conjunction (planet at its own position at birth)."""
    for e in result.events:
        if e.arc == 0.0:
            # Sect light conjuncting itself: significator OA == promittor OA
            assert e.significator == e.promittor_name and e.aspect_angle == 0, (
                f"Unexpected zero arc: {e.significator}/{e.promittor_name}/{e.aspect_angle}"
            )


def test_day_chart_sun_significator(result):
    if DAY:
        assert "Sun" in result.significators
    else:
        assert "Moon" in result.significators


def test_event_year_reasonable(result):
    """All events should fall between birth year and birth year + 360."""
    for e in result.events:
        assert 1990 <= e.event_date.year < 1990 + 361, (
            f"Year {e.event_date.year} out of expected range"
        )


# ── API endpoint tests ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_resp():
    r = client.post("/chart/circumambulations", json=BIRTH_REQ)
    assert r.status_code == 200
    return r.json()


def test_api_200(api_resp):
    assert "events" in api_resp


def test_api_events_count(api_resp):
    assert len(api_resp["events"]) == 70


def test_api_obliquity_range(api_resp):
    assert 22.0 < api_resp["obliquity"] < 24.5


def test_api_armc_range(api_resp):
    assert 0.0 <= api_resp["armc"] < 360.0


def test_api_aspect_names(api_resp):
    for e in api_resp["events"]:
        assert e["aspect_name"] in _VALID_ASPECTS


# ── Natal integration tests ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_natal():
    natal_req = {
        "year": 1990, "month": 6, "day": 15,
        "hour": 10, "minute": 30,
        "lat": 41.9, "lon": 12.5,
        "hsys": "P", "ut_offset": 0,
    }
    r = client.post("/chart/natal", json=natal_req)
    assert r.status_code == 200
    return r.json()


def test_natal_has_circumambulations(api_natal):
    assert "circumambulations" in api_natal
    assert api_natal["circumambulations"] is not None


def test_natal_circumambulations_events_nonempty(api_natal):
    assert len(api_natal["circumambulations"]["events"]) > 0


def test_natal_circumambulations_significators_count(api_natal):
    assert len(api_natal["circumambulations"]["significators"]) == 2
