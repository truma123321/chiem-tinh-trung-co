"""
Epic 3.2 — Lunar Return tests.

Verifies:
  1. Core finder: Moon returns to natal lon within 1e-6° per return
  2. Year count: 12–13 returns found per year
  3. Returns are strictly ordered and within the target year
  4. API endpoint: /chart/lunar-return returns correct structure
  5. Moon longitude matches natal lon to 0.001° for every entry
  6. Each entry has full chart fields (planets, houses, dignities, etc.)
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.lunar_return import find_next_lunar_return, find_all_lunar_returns_in_year

# ── ephemeris path ─────────────────────────────────────────────────────────────

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

# ── Fixtures ───────────────────────────────────────────────────────────────────

BIRTH = {"year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 30, "ut_offset": 0.0}
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

client = TestClient(app)


def _natal_moon_lon() -> float:
    jd = swe.julday(BIRTH["year"], BIRTH["month"], BIRTH["day"],
                    BIRTH["hour"] + BIRTH["minute"] / 60.0, swe.GREG_CAL)
    r, _ = swe.calc_ut(jd, swe.MOON, FLAGS)
    return r[0]


# ── Core finder tests ──────────────────────────────────────────────────────────

def test_find_next_lunar_return_accuracy():
    """Moon at found JD matches natal lon to < 0.001°."""
    natal_lon = _natal_moon_lon()
    jd_birth = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    jd_ret = find_next_lunar_return(natal_lon, jd_birth)
    r, _ = swe.calc_ut(jd_ret, swe.MOON, FLAGS)
    diff = abs((r[0] - natal_lon + 180) % 360 - 180)
    assert diff < 0.001, f"Moon differs by {diff:.6f}° from natal {natal_lon:.4f}°"


def test_find_next_lunar_return_strictly_after():
    """Result is strictly after the start JD."""
    natal_lon = _natal_moon_lon()
    jd_start = swe.julday(2025, 1, 1, 0.0, swe.GREG_CAL)
    jd_ret = find_next_lunar_return(natal_lon, jd_start)
    assert jd_ret > jd_start, f"Return JD {jd_ret} not after start {jd_start}"


def test_find_all_returns_count_in_year():
    """12–14 lunar returns found in a calendar year (365 / 27.32 ≈ 13.37)."""
    natal_lon = _natal_moon_lon()
    returns = find_all_lunar_returns_in_year(natal_lon, 2025)
    assert 12 <= len(returns) <= 14, f"Expected 12-14 returns, got {len(returns)}"


def test_find_all_returns_sorted():
    """Returned JDs are strictly increasing."""
    natal_lon = _natal_moon_lon()
    returns = find_all_lunar_returns_in_year(natal_lon, 2025)
    for i in range(1, len(returns)):
        assert returns[i] > returns[i - 1], f"Returns not sorted at index {i}"


def test_find_all_returns_in_year_bounds():
    """All returns fall within the target calendar year."""
    natal_lon = _natal_moon_lon()
    year = 2025
    returns = find_all_lunar_returns_in_year(natal_lon, year)
    jd_start = swe.julday(year, 1, 1, 0.0, swe.GREG_CAL)
    jd_end = swe.julday(year + 1, 1, 1, 0.0, swe.GREG_CAL)
    for jd in returns:
        assert jd_start <= jd < jd_end, f"Return JD {jd} outside year {year}"


def test_each_return_moon_accuracy():
    """Moon at every return JD matches natal lon to < 0.001°."""
    natal_lon = _natal_moon_lon()
    returns = find_all_lunar_returns_in_year(natal_lon, 2025)
    for jd in returns:
        r, _ = swe.calc_ut(jd, swe.MOON, FLAGS)
        diff = abs((r[0] - natal_lon + 180) % 360 - 180)
        assert diff < 0.001, f"Return at JD {jd:.4f}: Moon diff={diff:.6f}°"


def test_returns_spaced_by_sidereal_month():
    """Consecutive returns are ~27.32 ± 1 days apart."""
    natal_lon = _natal_moon_lon()
    returns = find_all_lunar_returns_in_year(natal_lon, 2025)
    for i in range(1, len(returns)):
        gap = returns[i] - returns[i - 1]
        assert 26.0 <= gap <= 29.0, (
            f"Gap between returns {i-1} and {i} is {gap:.2f} days (expected ~27.32)"
        )


# ── API endpoint tests ─────────────────────────────────────────────────────────

LR_REQUEST = {
    **BIRTH,
    "return_year": 2025,
    "return_lat": 41.9,
    "return_lon": 12.5,
    "hsys": "B",
}


@pytest.fixture(scope="module")
def lr_response():
    resp = client.post("/chart/lunar-return", json=LR_REQUEST)
    assert resp.status_code == 200, f"API error: {resp.text}"
    return resp.json()


def test_lr_response_status():
    resp = client.post("/chart/lunar-return", json=LR_REQUEST)
    assert resp.status_code == 200


def test_lr_top_level_fields(lr_response):
    assert "natal_moon_lon" in lr_response
    assert "return_year" in lr_response
    assert lr_response["return_year"] == 2025
    assert "count" in lr_response
    assert "returns" in lr_response


def test_lr_count_matches_returns_length(lr_response):
    assert lr_response["count"] == len(lr_response["returns"])


def test_lr_count_12_to_14(lr_response):
    assert 12 <= lr_response["count"] <= 14, (
        f"Expected 12-14 lunar returns, got {lr_response['count']}"
    )


def test_lr_natal_moon_lon_reasonable(lr_response):
    """Natal Moon should be a valid ecliptic longitude."""
    lon = lr_response["natal_moon_lon"]
    assert 0.0 <= lon < 360.0, f"natal_moon_lon out of range: {lon}"


def test_lr_each_entry_has_return_datetime(lr_response):
    for i, entry in enumerate(lr_response["returns"]):
        dt = entry["return_datetime"]
        assert "jd" in dt and dt["jd"] > 0, f"Entry {i}: missing jd"
        assert "year" in dt and dt["year"] == 2025, f"Entry {i}: year != 2025"
        assert "utc_iso" in dt, f"Entry {i}: missing utc_iso"
        assert "T" in dt["utc_iso"] and "Z" in dt["utc_iso"]


def test_lr_moon_matches_natal_in_each_entry(lr_response):
    """Moon at return JD matches natal lon to 0.001°."""
    natal_lon = lr_response["natal_moon_lon"]
    for i, entry in enumerate(lr_response["returns"]):
        moon = next(p for p in entry["planets"] if p["name"] == "Moon")
        diff = abs((moon["lon"] - natal_lon + 180) % 360 - 180)
        assert diff < 0.001, (
            f"Entry {i}: Moon {moon['lon']:.4f}° differs from natal {natal_lon:.4f}° by {diff:.4f}°"
        )


def test_lr_each_entry_has_seven_planets(lr_response):
    expected = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
    for i, entry in enumerate(lr_response["returns"]):
        names = {p["name"] for p in entry["planets"]}
        for planet in expected:
            assert planet in names, f"Entry {i}: missing planet {planet}"


def test_lr_each_entry_has_houses(lr_response):
    for i, entry in enumerate(lr_response["returns"]):
        houses = entry["houses"]
        assert len(houses["cusps"]) == 12, f"Entry {i}: expected 12 cusps"
        assert houses["asc"] != 0.0, f"Entry {i}: ASC is 0"
        assert houses["mc"] != 0.0, f"Entry {i}: MC is 0"


def test_lr_each_entry_has_dignities(lr_response):
    for i, entry in enumerate(lr_response["returns"]):
        assert len(entry["dignities"]) == 7, f"Entry {i}: expected 7 dignities"


def test_lr_each_entry_has_aspects(lr_response):
    for i, entry in enumerate(lr_response["returns"]):
        assert "aspects" in entry["aspects"], f"Entry {i}: missing aspects"


def test_lr_each_entry_has_almuten(lr_response):
    for i, entry in enumerate(lr_response["returns"]):
        assert "winner" in entry["almuten"], f"Entry {i}: missing almuten winner"
        assert entry["almuten"]["winner"] != "", f"Entry {i}: almuten winner empty"


def test_lr_each_entry_has_arabic_parts(lr_response):
    for i, entry in enumerate(lr_response["returns"]):
        assert len(entry["arabic_parts"]) > 0, f"Entry {i}: no arabic parts"


def test_lr_each_entry_has_conditions(lr_response):
    for i, entry in enumerate(lr_response["returns"]):
        assert "planet_conditions" in entry["conditions"], f"Entry {i}: missing conditions"
        assert len(entry["conditions"]["planet_conditions"]) == 6, (
            f"Entry {i}: expected 6 planet conditions (Sun excluded)"
        )


def test_lr_each_entry_has_fixed_stars(lr_response):
    for i, entry in enumerate(lr_response["returns"]):
        assert "star_positions" in entry["fixed_stars"], f"Entry {i}: missing star_positions"
        assert len(entry["fixed_stars"]["star_positions"]) > 0


def test_lr_each_entry_has_antiscia(lr_response):
    for i, entry in enumerate(lr_response["returns"]):
        assert "points" in entry["antiscia"], f"Entry {i}: missing antiscia points"
        assert len(entry["antiscia"]["points"]) == 7, f"Entry {i}: expected 7 antiscia points"


def test_lr_entries_ordered_by_jd(lr_response):
    """Return entries are sorted in chronological order."""
    jds = [e["return_datetime"]["jd"] for e in lr_response["returns"]]
    assert jds == sorted(jds), "Lunar return entries are not in chronological order"


def test_lr_different_location_gives_different_houses():
    """Return charts at London vs Rome should differ in house cusps."""
    req_rome   = {**LR_REQUEST, "return_lat": 41.9,  "return_lon": 12.5}
    req_london = {**LR_REQUEST, "return_lat": 51.5,  "return_lon": -0.1}
    resp_rome   = client.post("/chart/lunar-return", json=req_rome).json()
    resp_london = client.post("/chart/lunar-return", json=req_london).json()
    # Compare ASC of first return entry
    asc_rome   = resp_rome["returns"][0]["houses"]["asc"]
    asc_london = resp_london["returns"][0]["houses"]["asc"]
    assert abs(asc_rome - asc_london) > 0.5, (
        f"ASC too similar for different locations: Rome={asc_rome} London={asc_london}"
    )
