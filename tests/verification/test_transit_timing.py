"""
Epic 5.2 — Transit Timing tests.

Verifies:
  1. Core: Moon hits correct target longitude within 0.001°
  2. Core: hits are sorted chronologically
  3. Core: all hits are within the requested date range
  4. Core: hit_number ≤ total_hits
  5. Core: total_hits ≥ 1 for every hit object
  6. Core: station type is "SR" or "SD"
  7. Core: station lon is within 0.05° of actual planet longitude
  8. Core: station planet speed is near zero at station JD
  9. API: POST /chart/transit-timing returns 200
 10. API: response has natal_jd, start_jd, end_jd, exact_hits, stations
 11. API: exact_hits sorted by exact_jd
 12. API: all aspect_type in 0–4
 13. API: hit_number / total_hits contract
 14. API: retrograde_at_exact is boolean
 15. API: no Moon hits when include_moon=False
 16. API: no stations when include_stations=False
 17. API: station_type is "SR" or "SD"
 18. API: outer planets absent by default, present with include_outer=True
 19. API: exact_date matches YYYY-MM-DD format
 20. API: hit accuracy — at exact_jd, arc to natal ≈ aspect_angle < 0.01°
 21. API: start_jd / end_jd match requested dates
 22. API: wider range yields more hits than narrow range
 23. API: invalid date range (end < start) returns 422
 24. API: include_nodes=False removes node entries from hits
 25. API: station_orb=0.1 returns fewer stations than station_orb=5.0
"""

import re
import time
import pytest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.transit_timing import (
    calc_transit_timing, _find_hits_for_target, _find_stations,
    _jd_to_date, _g,
)
from models.chart import PlanetPosition

# ── Ephemeris path ────────────────────────────────────────────────────────────

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

# ── Shared data ───────────────────────────────────────────────────────────────

BIRTH = {"year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 30, "ut_offset": 0.0}

# 3-month window (faster tests, still exercises multi-hit patterns)
REQ_3M = {
    **BIRTH,
    "start_year": 2025, "start_month": 1, "start_day": 1,
    "end_year":   2025, "end_month":   3, "end_day":  31,
    "include_moon": True,
    "include_nodes": True,
    "include_outer": False,
    "include_stations": True,
    "station_orb": 5.0,   # wide so we always get some stations
}

REQ_1Y = {
    **BIRTH,
    "start_year": 2025, "start_month": 1, "start_day": 1,
    "end_year":   2025, "end_month":  12, "end_day":  31,
    "include_moon": True,
}

BIRTH_JD  = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
START_JD  = swe.julday(2025, 1, 1,   0.0, swe.GREG_CAL)
END_JD_3M = swe.julday(2025, 3, 31, 24.0, swe.GREG_CAL)
END_JD_1Y = swe.julday(2025, 12, 31, 24.0, swe.GREG_CAL)

_SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces",
]
_TRAD = [
    (swe.SUN, "Sun"), (swe.MOON, "Moon"), (swe.MERCURY, "Mercury"),
    (swe.VENUS, "Venus"), (swe.MARS, "Mars"), (swe.JUPITER, "Jupiter"),
    (swe.SATURN, "Saturn"),
]


def _planet(pid, name, jd) -> PlanetPosition:
    r, _ = swe.calc_ut(jd, pid, FLAGS)
    sign = _SIGNS[int(r[0] / 30) % 12]
    return PlanetPosition(
        id=pid, name=name, lon=round(r[0], 4), lat=round(r[1], 4),
        speed=round(r[3], 6), retrograde=r[3] < 0,
        sign=sign, sign_lon=round(r[0] % 30, 4),
    )


def _natal_planets(jd):
    return [_planet(pid, name, jd) for pid, name in _TRAD]


client = TestClient(app)


# ── Core unit tests ───────────────────────────────────────────────────────────

def test_hit_accuracy_moon():
    """At each returned JD, Moon should be at target_lon within 0.001°."""
    natal = _natal_planets(BIRTH_JD)
    target = natal[0].lon   # natal Sun longitude
    hits = _find_hits_for_target(START_JD, END_JD_3M, swe.MOON, target, step=0.5)
    assert hits, "Moon should cross natal Sun lon at least once in 3 months"
    for jd in hits:
        r, _ = swe.calc_ut(jd, swe.MOON, FLAGS)
        diff = abs(_g(r[0], target))
        assert diff < 0.001, f"Moon off by {diff:.6f}° at JD {jd}"


def test_hits_sorted():
    """Returned JDs must be in ascending order."""
    natal = _natal_planets(BIRTH_JD)
    target = natal[1].lon   # natal Moon
    hits = _find_hits_for_target(START_JD, END_JD_1Y, swe.MOON, target, step=0.5)
    assert hits == sorted(hits)


def test_hits_within_range():
    """Every hit JD must be within the requested range."""
    natal = _natal_planets(BIRTH_JD)
    target = natal[0].lon
    hits = _find_hits_for_target(START_JD, END_JD_3M, swe.MOON, target, step=0.5)
    for jd in hits:
        assert START_JD <= jd <= END_JD_3M


def test_station_type_sr_sd():
    """Station type must be 'SR' or 'SD'."""
    stations = _find_stations(START_JD, END_JD_1Y, swe.MARS, step=2.0)
    # Mars stations in 2025: it has a retrograde period
    for _, stype, _ in stations:
        assert stype in {"SR", "SD"}


def test_station_lon_accuracy():
    """At station JD, planet longitude should match reported station_lon within 0.05°."""
    stations = _find_stations(START_JD, END_JD_1Y, swe.MARS, step=2.0)
    for jd_stat, _, stat_lon in stations:
        r, _ = swe.calc_ut(jd_stat, swe.MARS, FLAGS)
        diff = abs(_g(r[0], stat_lon))
        assert diff < 0.05, f"Station lon off by {diff:.4f}°"


def test_station_speed_near_zero():
    """At station JD, planet speed should be near zero."""
    stations = _find_stations(START_JD, END_JD_1Y, swe.SATURN, step=5.0)
    for jd_stat, _, _ in stations:
        r, _ = swe.calc_ut(jd_stat, swe.SATURN, FLAGS)
        assert abs(r[3]) < 0.05, f"Saturn speed at station: {r[3]:.6f}°/day"


def test_jd_to_date_format():
    """_jd_to_date should return YYYY-MM-DD string."""
    d = _jd_to_date(START_JD)
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", d)
    assert d.startswith("2025")


# ── Core calc_transit_timing tests ────────────────────────────────────────────

@pytest.fixture(scope="module")
def timing_result_3m():
    natal = _natal_planets(BIRTH_JD)
    planet_ids = [(pid, name) for pid, name in _TRAD]
    return calc_transit_timing(
        start_jd=START_JD,
        end_jd=END_JD_3M,
        transit_planet_ids=planet_ids,
        natal_planets=natal,
        station_orb=5.0,
        include_stations=True,
    )


def test_core_hits_sorted(timing_result_3m):
    jds = [h.exact_jd for h in timing_result_3m.exact_hits]
    assert jds == sorted(jds)


def test_core_hits_positive(timing_result_3m):
    """Should find at least some exact hits in 3 months."""
    assert len(timing_result_3m.exact_hits) > 0


def test_core_hit_number_contract(timing_result_3m):
    for h in timing_result_3m.exact_hits:
        assert 1 <= h.hit_number <= h.total_hits


def test_core_total_hits_positive(timing_result_3m):
    for h in timing_result_3m.exact_hits:
        assert h.total_hits >= 1


def test_core_aspect_types_valid(timing_result_3m):
    for h in timing_result_3m.exact_hits:
        assert 0 <= h.aspect_type <= 4


def test_core_retrograde_is_bool(timing_result_3m):
    for h in timing_result_3m.exact_hits:
        assert isinstance(h.retrograde_at_exact, bool)


def test_core_station_types_valid(timing_result_3m):
    for s in timing_result_3m.stations:
        assert s.station_type in {"SR", "SD"}


def test_core_station_orb_respected(timing_result_3m):
    for s in timing_result_3m.stations:
        assert s.orb_to_nearest is not None
        assert s.orb_to_nearest <= 5.0 + 1e-6


# ── API tests ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def tr_timing():
    resp = client.post("/chart/transit-timing", json=REQ_3M)
    assert resp.status_code == 200, f"API error: {resp.text}"
    return resp.json()


def test_api_status_200():
    resp = client.post("/chart/transit-timing", json=REQ_3M)
    assert resp.status_code == 200


def test_api_top_level_fields(tr_timing):
    for f in ["natal_jd", "start_jd", "end_jd", "exact_hits", "stations"]:
        assert f in tr_timing, f"Missing field: {f}"


def test_api_jd_bounds(tr_timing):
    assert abs(tr_timing["natal_jd"] - BIRTH_JD) < 1.0
    assert abs(tr_timing["start_jd"] - START_JD) < 0.1
    assert abs(tr_timing["end_jd"] - END_JD_3M) < 0.1


def test_api_hits_sorted(tr_timing):
    jds = [h["exact_jd"] for h in tr_timing["exact_hits"]]
    assert jds == sorted(jds)


def test_api_hits_within_range(tr_timing):
    for h in tr_timing["exact_hits"]:
        assert tr_timing["start_jd"] <= h["exact_jd"] <= tr_timing["end_jd"]


def test_api_aspect_types_valid(tr_timing):
    for h in tr_timing["exact_hits"]:
        assert 0 <= h["aspect_type"] <= 4


def test_api_hit_number_contract(tr_timing):
    for h in tr_timing["exact_hits"]:
        assert 1 <= h["hit_number"] <= h["total_hits"]


def test_api_retrograde_is_bool(tr_timing):
    for h in tr_timing["exact_hits"]:
        assert isinstance(h["retrograde_at_exact"], bool)


def test_api_exact_date_format(tr_timing):
    for h in tr_timing["exact_hits"]:
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", h["exact_date"]), (
            f"Bad date format: {h['exact_date']}"
        )


def test_api_exact_date_in_range(tr_timing):
    for h in tr_timing["exact_hits"]:
        assert h["exact_date"] >= "2025-01-01"
        assert h["exact_date"] <= "2025-04-01"   # allow 1 day past end for rounding


def test_api_hit_accuracy(tr_timing):
    """At exact_jd, arc(transit_lon, natal_lon) should equal aspect_angle within 0.01°."""
    from core.transits import ASPECT_ANGLES, _arc
    for h in tr_timing["exact_hits"][:50]:   # check first 50 for speed
        r, _ = swe.calc_ut(h["exact_jd"], h["transit_planet_id"], FLAGS)
        arc = _arc(r[0], h["natal_lon"])
        expected = ASPECT_ANGLES[h["aspect_type"]]
        residual = abs(arc - expected)
        assert residual < 0.01, (
            f"{h['transit_planet_name']}→{h['natal_planet_name']} "
            f"{h['aspect_name']}: residual={residual:.4f}°"
        )


def test_api_no_moon_when_excluded():
    resp = client.post("/chart/transit-timing", json={
        **REQ_3M, "include_moon": False
    }).json()
    names = {h["transit_planet_name"] for h in resp["exact_hits"]}
    assert "Moon" not in names


def test_api_no_stations_when_disabled():
    resp = client.post("/chart/transit-timing", json={
        **REQ_3M, "include_stations": False
    }).json()
    assert resp["stations"] == []


def test_api_station_types_valid(tr_timing):
    for s in tr_timing["stations"]:
        assert s["station_type"] in ("SR", "SD")


def test_api_outer_absent_by_default(tr_timing):
    names = {h["transit_planet_name"] for h in tr_timing["exact_hits"]}
    assert "Uranus" not in names
    assert "Neptune" not in names
    assert "Pluto" not in names


def test_api_outer_present_when_requested():
    resp = client.post("/chart/transit-timing", json={
        **REQ_3M, "include_outer": True
    }).json()
    names = {h["transit_planet_name"] for h in resp["exact_hits"]}
    assert "Uranus" in names or "Neptune" in names or "Pluto" in names


def test_api_no_nodes_when_excluded():
    resp = client.post("/chart/transit-timing", json={
        **REQ_3M, "include_nodes": False
    }).json()
    names = {h["transit_planet_name"] for h in resp["exact_hits"]}
    assert "True Node" not in names
    assert "Mean Node" not in names


def test_api_station_orb_filters():
    """Narrow station_orb should return fewer stations than wide orb."""
    narrow = client.post("/chart/transit-timing", json={
        **REQ_3M, "station_orb": 0.5
    }).json()
    wide = client.post("/chart/transit-timing", json={
        **REQ_3M, "station_orb": 10.0
    }).json()
    assert len(narrow["stations"]) <= len(wide["stations"])


def test_api_wider_range_more_hits():
    """1-year range should produce more hits than 3-month range."""
    resp_1y = client.post("/chart/transit-timing", json=REQ_1Y).json()
    resp_3m = client.post("/chart/transit-timing", json=REQ_3M).json()
    assert len(resp_1y["exact_hits"]) > len(resp_3m["exact_hits"])


def test_api_invalid_date_range():
    """end before start → 422."""
    bad = {
        **BIRTH,
        "start_year": 2025, "start_month": 6, "start_day": 1,
        "end_year":   2025, "end_month":   1, "end_day":   1,
    }
    resp = client.post("/chart/transit-timing", json=bad)
    assert resp.status_code == 422


def test_api_moon_many_hits_in_year():
    """Moon should produce many exact hits in a year (crosses each natal many times)."""
    resp = client.post("/chart/transit-timing", json={
        **REQ_1Y, "include_outer": False, "include_nodes": False
    }).json()
    moon_hits = [h for h in resp["exact_hits"] if h["transit_planet_name"] == "Moon"]
    # Moon makes ~13 orbits/year × 7 natal × (1 conj + 4 asp × 2 targets) = 819 max
    # Realistically: >400 Moon hits in a year
    assert len(moon_hits) > 400, f"Expected >400 Moon hits, got {len(moon_hits)}"
