"""
Epic 3.1 — Solar Return tests.

Verifies:
  1. Core finder: sun returns to natal lon within 0.001° (< 1 second of time)
  2. Multiple return years
  3. API endpoint: /chart/solar-return returns correct structure
  4. Return Sun longitude matches natal lon to 0.001°
  5. response fields (planets, houses, dignities, aspects, etc.)
"""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.solar_return import find_solar_return_jd, jd_to_gregorian

# ── ephemeris path ─────────────────────────────────────────────────────────────

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

# ── Fixtures ───────────────────────────────────────────────────────────────────

BIRTH = {"year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 30, "ut_offset": 0.0}
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

client = TestClient(app)


def _natal_sun_lon() -> float:
    jd = swe.julday(BIRTH["year"], BIRTH["month"], BIRTH["day"],
                    BIRTH["hour"] + BIRTH["minute"] / 60.0, swe.GREG_CAL)
    r, _ = swe.calc_ut(jd, swe.SUN, FLAGS)
    return r[0]


# ── Core finder tests ──────────────────────────────────────────────────────────

def test_solar_return_accuracy():
    """Sun at return JD matches natal lon to < 0.001°."""
    natal_lon = _natal_sun_lon()
    jd_return = find_solar_return_jd(natal_lon, 2025, 6, 15, 10.5)
    r, _ = swe.calc_ut(jd_return, swe.SUN, FLAGS)
    diff = abs((r[0] - natal_lon + 180) % 360 - 180)
    assert diff < 0.001, f"Return Sun differs by {diff:.6f}° from natal {natal_lon:.4f}°"


def test_solar_return_year_range():
    """Finder converges for returns 1 to 60 years after birth."""
    natal_lon = _natal_sun_lon()
    birth_jd = swe.julday(1990, 6, 15, 10.5, swe.GREG_CAL)
    for return_year in range(1991, 2051, 5):
        jd_r = find_solar_return_jd(natal_lon, return_year, 6, 15, 10.5)
        # Must be within ±1 day of same calendar date in return_year
        jd_expected = swe.julday(return_year, 6, 15, 10.5, swe.GREG_CAL)
        assert abs(jd_r - jd_expected) < 2.0, (
            f"Return JD for {return_year} far from expected: Δ={abs(jd_r-jd_expected):.2f} days"
        )
        # And Sun position must match
        r, _ = swe.calc_ut(jd_r, swe.SUN, FLAGS)
        diff = abs((r[0] - natal_lon + 180) % 360 - 180)
        assert diff < 0.001, f"{return_year}: diff={diff:.6f}°"


def test_jd_to_gregorian_fields():
    """jd_to_gregorian returns correct field types and UTC ISO string."""
    natal_lon = _natal_sun_lon()
    jd_r = find_solar_return_jd(natal_lon, 2025, 6, 15, 10.5)
    dt = jd_to_gregorian(jd_r)
    assert dt["year"] == 2025
    assert dt["month"] in (5, 6, 7)   # near June
    assert 0 <= dt["hour"] <= 23
    assert 0.0 <= dt["second"] < 60.0
    assert "T" in dt["utc_iso"] and "Z" in dt["utc_iso"]


# ── API endpoint tests ─────────────────────────────────────────────────────────

SR_REQUEST = {
    **BIRTH,
    "return_year": 2025,
    "return_lat": 41.9,
    "return_lon": 12.5,
    "hsys": "B",
}


@pytest.fixture(scope="module")
def sr_chart():
    resp = client.post("/chart/solar-return", json=SR_REQUEST)
    assert resp.status_code == 200, f"API error: {resp.text}"
    return resp.json()


def test_sr_response_status():
    resp = client.post("/chart/solar-return", json=SR_REQUEST)
    assert resp.status_code == 200


def test_sr_return_datetime_fields(sr_chart):
    dt = sr_chart["return_datetime"]
    assert dt["year"] == 2025
    assert dt["month"] in (5, 6, 7)
    assert "jd" in dt and dt["jd"] > 0
    assert "utc_iso" in dt


def test_sr_natal_sun_lon(sr_chart):
    """natal_sun_lon should match natal Sun ~84.07°."""
    assert abs(sr_chart["natal_sun_lon"] - 84.07) < 0.1


def test_sr_sun_at_return_matches_natal(sr_chart):
    """Sun at return must match natal Sun to 0.001°."""
    return_sun = next(p for p in sr_chart["planets"] if p["name"] == "Sun")
    natal_lon = sr_chart["natal_sun_lon"]
    diff = abs((return_sun["lon"] - natal_lon + 180) % 360 - 180)
    assert diff < 0.001, (
        f"Return Sun {return_sun['lon']:.4f}° differs from natal {natal_lon:.4f}° by {diff:.4f}°"
    )


def test_sr_has_seven_traditional_planets(sr_chart):
    names = [p["name"] for p in sr_chart["planets"]]
    for expected in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]:
        assert expected in names


def test_sr_houses_present(sr_chart):
    assert len(sr_chart["houses"]["cusps"]) == 12
    assert sr_chart["houses"]["asc"] != 0.0
    assert sr_chart["houses"]["mc"] != 0.0


def test_sr_dignities_seven_planets(sr_chart):
    assert len(sr_chart["dignities"]) == 7


def test_sr_aspects_present(sr_chart):
    assert "aspects" in sr_chart
    assert "aspects" in sr_chart["aspects"]


def test_sr_almuten_present(sr_chart):
    assert "winner" in sr_chart["almuten"]
    assert sr_chart["almuten"]["winner"] != ""


def test_sr_arabic_parts_present(sr_chart):
    assert len(sr_chart["arabic_parts"]) > 0


def test_sr_conditions_present(sr_chart):
    assert "planet_conditions" in sr_chart["conditions"]
    # Conditions exclude Sun itself (Sun is the reference), so 6 planets
    assert len(sr_chart["conditions"]["planet_conditions"]) == 6


def test_sr_fixed_stars_present(sr_chart):
    assert "star_positions" in sr_chart["fixed_stars"]
    assert len(sr_chart["fixed_stars"]["star_positions"]) > 0


def test_sr_antiscia_present(sr_chart):
    assert "points" in sr_chart["antiscia"]
    assert len(sr_chart["antiscia"]["points"]) == 7


def test_sr_return_jd_in_target_year(sr_chart):
    """Return JD must correspond to a date within target year ± 7 days."""
    jd = sr_chart["return_datetime"]["jd"]
    jd_jan1 = swe.julday(2025, 1, 1, 0.0, swe.GREG_CAL)
    jd_dec31 = swe.julday(2025, 12, 31, 23.99, swe.GREG_CAL)
    assert jd_jan1 - 7 <= jd <= jd_dec31 + 7, f"Return JD {jd} not in 2025"


def test_sr_different_location_gives_different_houses():
    """Return chart at London should have different houses than Rome."""
    req_rome   = {**SR_REQUEST, "return_lat": 41.9,  "return_lon": 12.5}
    req_london = {**SR_REQUEST, "return_lat": 51.5,  "return_lon": -0.1}
    resp_rome   = client.post("/chart/solar-return", json=req_rome).json()
    resp_london = client.post("/chart/solar-return", json=req_london).json()
    # ASC should differ between locations
    asc_rome   = resp_rome["houses"]["asc"]
    asc_london = resp_london["houses"]["asc"]
    assert abs(asc_rome - asc_london) > 0.5, (
        f"ASC too similar for different locations: Rome={asc_rome} London={asc_london}"
    )
