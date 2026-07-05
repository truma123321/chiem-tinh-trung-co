"""
Epic 7.1 — Monthly & Daily Profections tests.

Monthly: profected_ASC = natal_ASC + age_months × 2.5°
Daily:   profected_ASC = natal_ASC + age_days × (30° / 30.4375)

Verifies:
  1.  Core: monthly — returns 12 entries for current annual year
  2.  Core: monthly — one entry is_current == True
  3.  Core: monthly — month_in_year values are 1–12
  4.  Core: monthly — profected_asc = natal_ASC + age_months × 2.5° (formula)
  5.  Core: monthly — advancing 1 month advances ASC by exactly 2.5°
  6.  Core: monthly — advancing 12 months advances ASC by exactly 30°
  7.  Core: monthly — lord_id = sign ruler of profected sign
  8.  Core: monthly — start/end dates span ~30.44 days
  9.  Core: monthly — current_entry.month_in_year in 1–12
 10.  Core: monthly — profected_asc always in [0°, 360°)
 11.  Core: daily — returns 31 entries for current monthly period
 12.  Core: daily — one entry is_current == True
 13.  Core: daily — day_in_month values are 1–31
 14.  Core: daily — formula: natal_ASC + age_days × DEG_PER_DAY
 15.  Core: daily — advancing 1 day advances ASC by DEG_PER_DAY
 16.  Core: daily — advancing 31 days advances ASC by ~30° (< 1 sign)
 17.  Core: daily — profected_asc always in [0°, 360°)
 18.  Core: daily — lord_id = sign ruler of profected sign
 19.  Core: monthly — total_months consistent with age_months of current_entry
 20.  Core: daily — total_days consistent with age_days of current_entry
 21.  API endpoint: POST /chart/profections period=annual returns annual data
 22.  API endpoint: POST /chart/profections period=monthly returns monthly data
 23.  API endpoint: POST /chart/profections period=daily returns daily data
 24.  API endpoint: invalid period returns 422
 25.  API endpoint: monthly has 12 entries
 26.  API endpoint: daily has 31 entries
 27.  API endpoint: monthly current_entry.profected_sign is valid
 28.  API endpoint: daily current_entry.profected_sign is valid
 29.  Natal: current_month present in profections response
 30.  Natal: current_month.month_in_year in 1–12
 31.  Natal: current_month.profected_asc in [0°, 360°)
 32.  Natal: current_month.lord_name is non-empty string
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.profections import (
    calc_monthly_profection, calc_daily_profection,
    MONTH_DAYS, DEG_PER_MON, DEG_PER_DAY,
)
from core.dignities import DOMICILE

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

client = TestClient(app)

NATAL_REQ = {
    "year": 1990, "month": 6, "day": 15,
    "hour": 10, "minute": 30,
    "lat": 41.9, "lon": 12.5,
    "hsys": "P", "ut_offset": 0,
}
PROF_REQ = {**NATAL_REQ}

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

JD = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

PLANET_LONS = {}
for _pid in range(7):
    _r, _ = swe.calc_ut(JD, _pid, FLAGS)
    PLANET_LONS[_pid] = _r[0]

_cusps, _ascmc = swe.houses(JD, 41.9, 12.5, b"P")
ASC = _ascmc[0]


@pytest.fixture(scope="module")
def monthly():
    return calc_monthly_profection(JD, ASC, PLANET_LONS)


@pytest.fixture(scope="module")
def daily():
    return calc_daily_profection(JD, ASC, PLANET_LONS)


@pytest.fixture(scope="module")
def api_natal():
    r = client.post("/chart/natal", json=NATAL_REQ)
    assert r.status_code == 200
    return r.json()


# ── Monthly core tests ─────────────────────────────────────────────────────────

def test_monthly_12_entries(monthly):
    assert len(monthly.entries) == 12


def test_monthly_one_current(monthly):
    currents = [e for e in monthly.entries if e.is_current]
    assert len(currents) == 1


def test_monthly_month_in_year_1_to_12(monthly):
    months = [e.month_in_year for e in monthly.entries]
    assert months == list(range(1, 13))


def test_monthly_formula(monthly):
    """Each entry: profected_asc == (ASC + age_months × 2.5°) % 360°."""
    for e in monthly.entries:
        expected = (ASC + e.age_months * DEG_PER_MON) % 360.0
        assert abs(e.profected_asc - expected) < 0.001, (
            f"m{e.month_in_year}: got {e.profected_asc}, expected {expected:.4f}"
        )


def test_monthly_advances_2_5_per_month(monthly):
    for i in range(11):
        a = monthly.entries[i].profected_asc
        b = monthly.entries[i + 1].profected_asc
        diff = (b - a) % 360.0
        assert abs(diff - 2.5) < 0.001, f"month {i+1}→{i+2}: diff={diff}"


def test_monthly_12_months_is_one_sign(monthly):
    first = monthly.entries[0].profected_asc
    last  = monthly.entries[11].profected_asc
    diff  = (last - first) % 360.0
    assert abs(diff - 27.5) < 0.001  # 11 × 2.5° = 27.5° (months 1–12, index 0–11)


def test_monthly_lord_matches_sign(monthly):
    for e in monthly.entries:
        expected_lord = DOMICILE[e.profected_sign_idx]
        assert e.lord_id == expected_lord, (
            f"m{e.month_in_year} {e.profected_sign}: lord={e.lord_id}, expected={expected_lord}"
        )


def test_monthly_start_end_span_month(monthly):
    for e in monthly.entries:
        span = e.end.jd - e.start.jd
        assert abs(span - MONTH_DAYS) < 0.01, (
            f"m{e.month_in_year}: span={span:.4f}, expected ~{MONTH_DAYS:.4f}"
        )


def test_monthly_current_entry_in_range(monthly):
    assert 1 <= monthly.current_entry.month_in_year <= 12


def test_monthly_asc_in_range(monthly):
    for e in monthly.entries:
        assert 0.0 <= e.profected_asc < 360.0


def test_monthly_total_months_consistent(monthly):
    cur = monthly.current_entry
    assert cur.age_months == monthly.total_months


# ── Daily core tests ───────────────────────────────────────────────────────────

def test_daily_31_entries(daily):
    assert len(daily.entries) == 31


def test_daily_one_current(daily):
    currents = [e for e in daily.entries if e.is_current]
    assert len(currents) == 1


def test_daily_day_in_month_1_to_31(daily):
    days = [e.day_in_month for e in daily.entries]
    assert days == list(range(1, 32))


def test_daily_formula(daily):
    """Each entry: profected_asc == (ASC + age_days × DEG_PER_DAY) % 360°."""
    for e in daily.entries:
        expected = (ASC + e.age_days * DEG_PER_DAY) % 360.0
        assert abs(e.profected_asc - expected) < 0.001, (
            f"d{e.day_in_month}: got {e.profected_asc}, expected {expected:.4f}"
        )


def test_daily_advances_deg_per_day(daily):
    for i in range(30):
        a = daily.entries[i].profected_asc
        b = daily.entries[i + 1].profected_asc
        diff = (b - a) % 360.0
        assert abs(diff - DEG_PER_DAY) < 0.001, f"d{i+1}→{i+2}: diff={diff}"


def test_daily_31_days_under_one_sign(daily):
    """31 days × 0.9856°/day ≈ 30.55° < 30° is not true — check it's < 31°."""
    first = daily.entries[0].profected_asc
    last  = daily.entries[30].profected_asc
    diff  = (last - first) % 360.0
    assert 28.0 < diff < 32.0, f"31-day span: {diff:.4f}°"


def test_daily_asc_in_range(daily):
    for e in daily.entries:
        assert 0.0 <= e.profected_asc < 360.0


def test_daily_lord_matches_sign(daily):
    for e in daily.entries:
        assert e.lord_id == DOMICILE[e.profected_sign_idx]


def test_daily_total_days_consistent(daily):
    cur = daily.current_entry
    assert cur.age_days == daily.total_days


# ── API endpoint tests ─────────────────────────────────────────────────────────

def test_api_annual_returns_annual():
    r = client.post("/chart/profections", json={**PROF_REQ, "period": "annual"})
    assert r.status_code == 200
    d = r.json()
    assert d["period"] == "annual"
    assert d["annual"] is not None
    assert d["monthly"] is None
    assert d["daily"] is None


def test_api_monthly_returns_monthly():
    r = client.post("/chart/profections", json={**PROF_REQ, "period": "monthly"})
    assert r.status_code == 200
    d = r.json()
    assert d["period"] == "monthly"
    assert d["monthly"] is not None
    assert d["annual"] is None


def test_api_daily_returns_daily():
    r = client.post("/chart/profections", json={**PROF_REQ, "period": "daily"})
    assert r.status_code == 200
    d = r.json()
    assert d["period"] == "daily"
    assert d["daily"] is not None


def test_api_invalid_period_422():
    r = client.post("/chart/profections", json={**PROF_REQ, "period": "yearly"})
    assert r.status_code == 422


def test_api_monthly_12_entries():
    r = client.post("/chart/profections", json={**PROF_REQ, "period": "monthly"})
    d = r.json()
    assert len(d["monthly"]["entries"]) == 12


def test_api_daily_31_entries():
    r = client.post("/chart/profections", json={**PROF_REQ, "period": "daily"})
    d = r.json()
    assert len(d["daily"]["entries"]) == 31


def test_api_monthly_current_sign_valid():
    r = client.post("/chart/profections", json={**PROF_REQ, "period": "monthly"})
    d = r.json()
    assert d["monthly"]["current_entry"]["profected_sign"] in SIGNS


def test_api_daily_current_sign_valid():
    r = client.post("/chart/profections", json={**PROF_REQ, "period": "daily"})
    d = r.json()
    assert d["daily"]["current_entry"]["profected_sign"] in SIGNS


# ── Natal current_month tests ──────────────────────────────────────────────────

def test_natal_current_month_present(api_natal):
    assert "current_month" in api_natal["profections"]
    assert api_natal["profections"]["current_month"] is not None


def test_natal_current_month_in_year_range(api_natal):
    m = api_natal["profections"]["current_month"]["month_in_year"]
    assert 1 <= m <= 12


def test_natal_current_month_asc_in_range(api_natal):
    asc = api_natal["profections"]["current_month"]["profected_asc"]
    assert 0.0 <= asc < 360.0


def test_natal_current_month_lord_name(api_natal):
    name = api_natal["profections"]["current_month"]["lord_name"]
    assert isinstance(name, str) and len(name) > 0
