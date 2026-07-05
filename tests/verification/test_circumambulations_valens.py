"""
Epic 10.6 — Circumambulations Full Valens Method.

Verifies:
  1.  is_loosing_of_bond field is bool on every event
  2.  bonification field is str or None on every event
  3.  maltreatment field is str or None on every event
  4.  sub_periods absent (None) by default
  5.  sub_periods present when include_sub_periods=True
  6.  sub_periods has exactly 7 items per event
  7.  sub_period durations sum ≈ MINOR_YEARS[promittor] × 365.25
  8.  MINOR_YEARS dict has correct values
  9.  MINOR_YEARS sums to 129
 10.  _build_sub_periods: first planet is promittor itself (Chaldean start)
 11.  mc_lon present in response (non-zero for non-zero-lat birth)
 12.  mc_oa present in response
 13.  sub_period start/end dates have required fields
 14.  sub_period planet_ids are in [0, 6]
 15.  loosing_of_bond count is reasonable (not all events flagged)
 16.  bonification/maltreatment string format is correct when not None
 17.  API: 200 status with include_sub_periods=True
 18.  API: event count matches without sub_periods flag
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
import pytest
from fastapi.testclient import TestClient
from main import app

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../tools/morinus/SWEP/Ephem")
)
swe.set_ephe_path(EPHE_PATH)

client = TestClient(app)

# ── Constants from circumambulations module ────────────────────────────────────

from core.circumambulations import (
    MINOR_YEARS,
    _CHALDEAN_ORDER,
    _MINOR_TOTAL,
    _build_sub_periods,
    calc_circumambulations,
)

_YEAR_DAYS = 365.25

# ── Test birth data ────────────────────────────────────────────────────────────

BASE_REQ = {
    "year": 1990, "month": 6, "day": 15,
    "hour": 10, "minute": 30,
    "lat": 41.9, "lon": 12.5,
    "hsys": "P", "ut_offset": 0.0,
}

# ── MINOR_YEARS constants ──────────────────────────────────────────────────────

def test_minor_years_sun():
    assert MINOR_YEARS[0] == 19.0

def test_minor_years_moon():
    assert MINOR_YEARS[1] == 25.0

def test_minor_years_mercury():
    assert MINOR_YEARS[2] == 20.0

def test_minor_years_venus():
    assert MINOR_YEARS[3] == 8.0

def test_minor_years_mars():
    assert MINOR_YEARS[4] == 15.0

def test_minor_years_jupiter():
    assert MINOR_YEARS[5] == 12.0

def test_minor_years_saturn():
    assert MINOR_YEARS[6] == 30.0

def test_minor_years_total_is_129():
    assert _MINOR_TOTAL == 129.0

# ── Core function: sub-period structure ───────────────────────────────────────

def test_sub_periods_count_is_7():
    # Saturn (id=6) sub-periods
    subs = _build_sub_periods(2451545.0, 6)
    assert len(subs) == 7

def test_sub_periods_first_planet_is_promittor():
    """Chaldean order starts from the promittor itself."""
    for pid in range(7):
        subs = _build_sub_periods(2451545.0, pid)
        assert subs[0].planet_id == pid, (
            f"First sub-period for promittor {pid} should be {pid}, got {subs[0].planet_id}"
        )

def test_sub_periods_duration_sums_to_major_period():
    """Sum of sub-period durations = MINOR_YEARS[promittor] × 365.25."""
    for pid in range(7):
        subs = _build_sub_periods(2451545.0, pid)
        total = sum(s.duration_days for s in subs)
        expected = MINOR_YEARS[pid] * _YEAR_DAYS
        assert abs(total - expected) < 0.1, (
            f"Promittor {pid}: expected {expected:.2f} days, got {total:.2f}"
        )

def test_sub_periods_planet_ids_in_range():
    subs = _build_sub_periods(2451545.0, 0)  # Sun
    for s in subs:
        assert 0 <= s.planet_id <= 6

def test_sub_periods_chaldean_all_7_planets_covered():
    """Each sub-period cycle covers all 7 planets exactly once."""
    subs = _build_sub_periods(2451545.0, 5)  # Jupiter
    pids = sorted(s.planet_id for s in subs)
    assert pids == list(range(7))

# ── API: default response (no sub_periods) ────────────────────────────────────

@pytest.fixture(scope="module")
def default_resp():
    return client.post("/chart/circumambulations", json=BASE_REQ).json()

@pytest.fixture(scope="module")
def sub_resp():
    return client.post("/chart/circumambulations",
                       json={**BASE_REQ, "include_sub_periods": True}).json()

def test_api_returns_200():
    r = client.post("/chart/circumambulations", json=BASE_REQ)
    assert r.status_code == 200

def test_api_with_sub_periods_returns_200():
    r = client.post("/chart/circumambulations",
                    json={**BASE_REQ, "include_sub_periods": True})
    assert r.status_code == 200

def test_is_loosing_of_bond_is_bool(default_resp):
    for e in default_resp["events"]:
        assert isinstance(e["is_loosing_of_bond"], bool)

def test_bonification_is_str_or_none(default_resp):
    for e in default_resp["events"]:
        assert e["bonification"] is None or isinstance(e["bonification"], str)

def test_maltreatment_is_str_or_none(default_resp):
    for e in default_resp["events"]:
        assert e["maltreatment"] is None or isinstance(e["maltreatment"], str)

def test_sub_periods_absent_by_default(default_resp):
    for e in default_resp["events"]:
        assert e["sub_periods"] is None

def test_sub_periods_present_when_requested(sub_resp):
    assert any(e["sub_periods"] is not None for e in sub_resp["events"])

def test_sub_periods_count_7_per_event(sub_resp):
    for e in sub_resp["events"]:
        assert e["sub_periods"] is not None
        assert len(e["sub_periods"]) == 7

def test_sub_period_fields(sub_resp):
    first_event = sub_resp["events"][0]
    for s in first_event["sub_periods"]:
        assert "planet_id" in s
        assert "planet_name" in s
        assert "start_date" in s
        assert "end_date" in s
        assert "duration_days" in s

def test_sub_period_date_fields(sub_resp):
    s = sub_resp["events"][0]["sub_periods"][0]
    for dp in (s["start_date"], s["end_date"]):
        assert "year" in dp
        assert "month" in dp
        assert "day" in dp
        assert "jd" in dp

def test_mc_lon_present_in_response(default_resp):
    assert "mc_lon" in default_resp
    assert isinstance(default_resp["mc_lon"], float)

def test_mc_oa_present_in_response(default_resp):
    assert "mc_oa" in default_resp
    assert isinstance(default_resp["mc_oa"], float)

def test_mc_lon_nonzero_for_nonzero_lat(default_resp):
    """Non-equatorial birth should have non-trivial MC longitude."""
    assert default_resp["mc_lon"] != 0.0

def test_event_count_same_with_and_without_sub_periods(default_resp, sub_resp):
    assert len(default_resp["events"]) == len(sub_resp["events"])

def test_loosing_of_bond_not_all_flagged(default_resp):
    """Not every event can be at the loosing arc — most should be False."""
    flagged = sum(1 for e in default_resp["events"] if e["is_loosing_of_bond"])
    total = len(default_resp["events"])
    assert flagged < total // 2, (
        f"Too many loosing-of-bond events: {flagged}/{total}"
    )

def test_bonification_format_when_present(default_resp):
    """Bonification strings follow 'Planet aspect' pattern."""
    for e in default_resp["events"]:
        if e["bonification"] is not None:
            assert any(e["bonification"].startswith(p) for p in ("Jupiter", "Venus")), (
                f"Unexpected bonification: {e['bonification']}"
            )
            assert any(a in e["bonification"] for a in ("trine", "sextile")), (
                f"Unexpected bonification: {e['bonification']}"
            )

def test_maltreatment_format_when_present(default_resp):
    """Maltreatment strings follow 'Planet aspect' pattern."""
    for e in default_resp["events"]:
        if e["maltreatment"] is not None:
            assert any(e["maltreatment"].startswith(p) for p in ("Mars", "Saturn")), (
                f"Unexpected maltreatment: {e['maltreatment']}"
            )
            assert any(a in e["maltreatment"] for a in ("square", "opposition")), (
                f"Unexpected maltreatment: {e['maltreatment']}"
            )
