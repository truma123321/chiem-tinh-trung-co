"""
Epic 5.3 — Ingresses tests.

Verifies:
  1.  Core: Sun has exactly 12 direct ingresses in 2025
  2.  Core: Sun has 0 retrograde ingresses (never retrogrades)
  3.  Core: Mercury has 16 ingresses in 2025 (2 retrograde)
  4.  Core: Mars has 7 ingresses in 2025 (1 retrograde)
  5.  Core: Jupiter has 1 ingress in 2025 (direct into Cancer)
  6.  Core: all ingress JDs within [start_jd, end_jd]
  7.  Core: ingresses sorted chronologically
  8.  Core: sign and from_sign are valid zodiac names
  9.  Core: sign != from_sign for all events
 10.  Core: boundary_lon is a multiple of 30
 11.  Core: retrograde=True events have planet speed < 0
 12.  Core: retrograde=False events have planet speed > 0
 13.  Core: ingress_time matches HH:MM pattern
 14.  Core: at ingress_jd planet longitude ≈ boundary_lon within 0.01°
 15.  API: POST /chart/ingresses returns 200
 16.  API: response has start_jd, end_jd, ingresses
 17.  API: Moon excluded by default
 18.  API: Moon included when include_moon=True
 19.  API: outer planets excluded by default
 20.  API: outer planets included when include_outer=True
 21.  API: nodes excluded by default
 22.  API: nodes appear when include_nodes=True
 23.  API: all ingresses within date range
 24.  API: ingresses sorted by ingress_jd
 25.  API: ingress_date format YYYY-MM-DD
 26.  API: retrograde is boolean
 27.  API: boundary_lon is multiple of 30
 28.  API: invalid range (end < start) → 422
 29.  API: Jupiter ingress into Cancer on 2025-06-09
 30.  API: Moon ingresses every ~2-3 days (>100 Moon ingresses in a year)
"""

import re
import pytest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.ingresses import calc_ingresses, SIGN_NAMES, _jd_to_datetime
from core.transits import _arc

# ── Ephemeris setup ───────────────────────────────────────────────────────────

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

# ── Constants ─────────────────────────────────────────────────────────────────

START_JD = swe.julday(2025, 1, 1,   0.0, swe.GREG_CAL)
END_JD   = swe.julday(2025, 12, 31, 24.0, swe.GREG_CAL)

REQ_2025 = {
    "start_year": 2025, "start_month": 1, "start_day": 1,
    "end_year":   2025, "end_month": 12, "end_day":  31,
}

client = TestClient(app)


# ── Core unit tests ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def events_2025():
    return calc_ingresses(
        START_JD, END_JD,
        [
            (swe.SUN,     "Sun"),
            (swe.MERCURY, "Mercury"),
            (swe.MARS,    "Mars"),
            (swe.JUPITER, "Jupiter"),
        ],
    )


def test_sun_twelve_ingresses(events_2025):
    sun = [e for e in events_2025 if e.planet_name == "Sun"]
    assert len(sun) == 12, f"Expected 12 Sun ingresses, got {len(sun)}"


def test_sun_no_retrograde(events_2025):
    sun_retro = [e for e in events_2025 if e.planet_name == "Sun" and e.retrograde]
    assert sun_retro == [], "Sun should never have retrograde ingresses"


def test_mercury_sixteen_ingresses(events_2025):
    merc = [e for e in events_2025 if e.planet_name == "Mercury"]
    assert len(merc) == 16, f"Expected 16 Mercury ingresses, got {len(merc)}"


def test_mercury_two_retrograde(events_2025):
    merc_retro = [e for e in events_2025 if e.planet_name == "Mercury" and e.retrograde]
    assert len(merc_retro) == 2, f"Expected 2 Mercury retrograde ingresses, got {len(merc_retro)}"


def test_mars_seven_ingresses(events_2025):
    mars = [e for e in events_2025 if e.planet_name == "Mars"]
    assert len(mars) == 7, f"Expected 7 Mars ingresses, got {len(mars)}"


def test_mars_one_retrograde(events_2025):
    mars_retro = [e for e in events_2025 if e.planet_name == "Mars" and e.retrograde]
    assert len(mars_retro) == 1, f"Expected 1 Mars retrograde ingress, got {len(mars_retro)}"
    assert mars_retro[0].sign == "Cancer"
    assert mars_retro[0].from_sign == "Leo"


def test_jupiter_one_ingress(events_2025):
    jup = [e for e in events_2025 if e.planet_name == "Jupiter"]
    assert len(jup) == 1, f"Expected 1 Jupiter ingress, got {len(jup)}"
    assert jup[0].sign == "Cancer"
    assert not jup[0].retrograde


def test_all_within_range(events_2025):
    for e in events_2025:
        assert START_JD <= e.ingress_jd <= END_JD, (
            f"{e.planet_name} ingress at {e.ingress_jd} outside [{START_JD}, {END_JD}]"
        )


def test_sorted_chronologically(events_2025):
    jds = [e.ingress_jd for e in events_2025]
    assert jds == sorted(jds)


def test_sign_names_valid(events_2025):
    for e in events_2025:
        assert e.sign in SIGN_NAMES, f"Unknown sign: {e.sign}"
        assert e.from_sign in SIGN_NAMES, f"Unknown from_sign: {e.from_sign}"


def test_sign_different_from_from_sign(events_2025):
    for e in events_2025:
        assert e.sign != e.from_sign, (
            f"{e.planet_name} has same sign and from_sign: {e.sign}"
        )


def test_boundary_lon_multiple_of_30(events_2025):
    for e in events_2025:
        assert e.boundary_lon % 30.0 < 1e-9 or (360.0 - e.boundary_lon % 30.0) < 1e-9, (
            f"boundary_lon {e.boundary_lon} is not a multiple of 30"
        )


def test_retrograde_speed_negative(events_2025):
    for e in events_2025:
        r, _ = swe.calc_ut(e.ingress_jd, e.planet_id, FLAGS)
        if e.retrograde:
            assert r[3] < 0, (
                f"{e.planet_name} on {e.ingress_date}: retrograde=True but speed={r[3]:.6f}"
            )


def test_direct_speed_positive(events_2025):
    for e in events_2025:
        r, _ = swe.calc_ut(e.ingress_jd, e.planet_id, FLAGS)
        if not e.retrograde:
            assert r[3] > 0, (
                f"{e.planet_name} on {e.ingress_date}: retrograde=False but speed={r[3]:.6f}"
            )


def test_ingress_time_format(events_2025):
    for e in events_2025:
        assert re.match(r"^\d{2}:\d{2}$", e.ingress_time), (
            f"Bad ingress_time: {e.ingress_time}"
        )


def test_ingress_accuracy(events_2025):
    """At ingress_jd, planet lon should be within 0.01° of boundary_lon."""
    for e in events_2025:
        r, _ = swe.calc_ut(e.ingress_jd, e.planet_id, FLAGS)
        diff = _arc(r[0], e.boundary_lon)
        assert diff < 0.01, (
            f"{e.planet_name} {e.ingress_date}: diff={diff:.5f}° from boundary {e.boundary_lon}"
        )


def test_jd_to_datetime_basic():
    d, t = _jd_to_datetime(START_JD)
    assert d == "2025-01-01"
    assert re.match(r"^\d{2}:\d{2}$", t)


# ── API tests ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_2025():
    resp = client.post("/chart/ingresses", json=REQ_2025)
    assert resp.status_code == 200, f"API error: {resp.text}"
    return resp.json()


def test_api_status_200():
    assert client.post("/chart/ingresses", json=REQ_2025).status_code == 200


def test_api_top_level_fields(api_2025):
    for f in ["start_jd", "end_jd", "ingresses"]:
        assert f in api_2025


def test_api_jd_bounds(api_2025):
    assert abs(api_2025["start_jd"] - START_JD) < 0.1
    assert abs(api_2025["end_jd"] - END_JD) < 0.1


def test_api_sorted(api_2025):
    jds = [e["ingress_jd"] for e in api_2025["ingresses"]]
    assert jds == sorted(jds)


def test_api_within_range(api_2025):
    for e in api_2025["ingresses"]:
        assert api_2025["start_jd"] <= e["ingress_jd"] <= api_2025["end_jd"]


def test_api_retrograde_is_bool(api_2025):
    for e in api_2025["ingresses"]:
        assert isinstance(e["retrograde"], bool)


def test_api_ingress_date_format(api_2025):
    for e in api_2025["ingresses"]:
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", e["ingress_date"])


def test_api_ingress_time_format(api_2025):
    for e in api_2025["ingresses"]:
        assert re.match(r"^\d{2}:\d{2}$", e["ingress_time"])


def test_api_boundary_lon_multiple_of_30(api_2025):
    for e in api_2025["ingresses"]:
        assert e["boundary_lon"] % 30.0 < 1e-6


def test_api_sign_names_valid(api_2025):
    for e in api_2025["ingresses"]:
        assert e["sign"] in SIGN_NAMES
        assert e["from_sign"] in SIGN_NAMES


def test_api_moon_absent_by_default(api_2025):
    names = {e["planet_name"] for e in api_2025["ingresses"]}
    assert "Moon" not in names


def test_api_moon_present_when_included():
    resp = client.post("/chart/ingresses", json={**REQ_2025, "include_moon": True}).json()
    moon = [e for e in resp["ingresses"] if e["planet_name"] == "Moon"]
    # Moon transits each sign in ~2.3 days → ~157 ingresses/year
    assert len(moon) > 100, f"Expected >100 Moon ingresses, got {len(moon)}"


def test_api_outer_absent_by_default(api_2025):
    names = {e["planet_name"] for e in api_2025["ingresses"]}
    assert "Uranus" not in names
    assert "Neptune" not in names
    assert "Pluto" not in names


def test_api_outer_present_when_included():
    resp = client.post("/chart/ingresses", json={**REQ_2025, "include_outer": True}).json()
    names = {e["planet_name"] for e in resp["ingresses"]}
    # Uranus, Neptune, Pluto all move slowly but at least one should ingress in 2025
    # (or at worst the set is not empty from a different year; check Chiron at minimum)
    assert "Chiron" in names or "Uranus" in names or "Neptune" in names or "Pluto" in names


def test_api_nodes_absent_by_default(api_2025):
    names = {e["planet_name"] for e in api_2025["ingresses"]}
    assert "True Node" not in names
    assert "Mean Node" not in names


def test_api_nodes_present_when_included():
    resp = client.post("/chart/ingresses", json={**REQ_2025, "include_nodes": True}).json()
    names = {e["planet_name"] for e in resp["ingresses"]}
    assert "True Node" in names or "Mean Node" in names


def test_api_jupiter_cancer_ingress(api_2025):
    """Jupiter should enter Cancer on 2025-06-09."""
    jup = [e for e in api_2025["ingresses"] if e["planet_name"] == "Jupiter"]
    assert len(jup) == 1
    assert jup[0]["sign"] == "Cancer"
    assert jup[0]["ingress_date"] == "2025-06-09"
    assert not jup[0]["retrograde"]


def test_api_sun_twelve_direct(api_2025):
    sun = [e for e in api_2025["ingresses"] if e["planet_name"] == "Sun"]
    assert len(sun) == 12
    assert all(not e["retrograde"] for e in sun)


def test_api_invalid_range_422():
    bad = {
        "start_year": 2025, "start_month": 12, "start_day": 31,
        "end_year":   2025, "end_month":  1,  "end_day":   1,
    }
    assert client.post("/chart/ingresses", json=bad).status_code == 422


def test_api_wider_range_more_ingresses():
    """3-year range should yield more ingresses than 1-year range."""
    one_year = client.post("/chart/ingresses", json=REQ_2025).json()
    three_yr  = client.post("/chart/ingresses", json={
        "start_year": 2025, "start_month": 1, "start_day": 1,
        "end_year":   2027, "end_month": 12, "end_day": 31,
    }).json()
    assert len(three_yr["ingresses"]) > len(one_year["ingresses"])
