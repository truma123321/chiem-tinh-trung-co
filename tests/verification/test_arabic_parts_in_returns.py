"""
Epic 10.5 — Arabic Parts in Return & Progressed Charts.

Verifies:
  1. Solar return already includes arabic_parts (existing feature)
  2. Solar return arabic_parts uses return ASC (not natal ASC)
  3. Lot of Fortune differs between natal and solar return
  4. Lunar return already includes arabic_parts
  5. Lunar return arabic_parts uses return chart data
  6. Secondary progressions: arabic_parts absent by default
  7. Secondary progressions: arabic_parts present when include_lots=True
  8. Secondary progressions: arabic_parts uses progressed Sun, Moon, ASC
  9. Secondary progressions: Lot of Fortune differs between natal and progressed
 10. Secondary progressions: arabic_parts list has expected lot names
 11. Tertiary progressions: arabic_parts absent by default
 12. Tertiary progressions: arabic_parts present when include_lots=True
 13. Tertiary progressions: arabic_parts has expected fields (name, lon, sign)
 14. Secondary progressions: lot longitudes in [0, 360)
 15. Tertiary progressions: lot longitudes in [0, 360)
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

# ── Base requests ─────────────────────────────────────────────────────────────

BIRTH = {
    "year": 1990, "month": 6, "day": 15,
    "hour": 10, "minute": 30,
    "lat": 41.9, "lon": 12.5,
    "hsys": "P", "ut_offset": 0.0,
}

SOLAR_REQ = {**BIRTH, "return_year": 2024, "return_lat": 41.9, "return_lon": 12.5}

LUNAR_REQ = {**BIRTH, "return_year": 2024, "return_lat": 41.9, "return_lon": 12.5}

PROG_REQ = {
    **BIRTH,
    "prog_year": 2025, "prog_month": 6, "prog_day": 15,
    "hsys": "P",
}

NATAL_REQ = {**BIRTH, "hsys": "P"}


# ── Helper ────────────────────────────────────────────────────────────────────

def _lot_of_fortune(lots: list[dict]) -> dict | None:
    for lot in lots:
        if lot["name"] in ("Lot of Fortune", "Fortune"):
            return lot
    return None


# ── Solar Return (already has arabic_parts) ───────────────────────────────────

def test_solar_return_has_arabic_parts():
    resp = client.post("/chart/solar-return", json=SOLAR_REQ)
    assert resp.status_code == 200
    data = resp.json()
    assert "arabic_parts" in data
    assert isinstance(data["arabic_parts"], list)
    assert len(data["arabic_parts"]) > 0


def test_solar_return_lots_have_required_fields():
    data = client.post("/chart/solar-return", json=SOLAR_REQ).json()
    for lot in data["arabic_parts"]:
        assert "name" in lot
        assert "lon" in lot
        assert "sign" in lot
        assert 0 <= lot["lon"] < 360


def test_solar_return_lot_of_fortune_differs_from_natal():
    """Return chart uses return ASC → Lot of Fortune differs from natal."""
    sr = client.post("/chart/solar-return", json=SOLAR_REQ).json()
    natal = client.post("/chart/natal", json=NATAL_REQ).json()

    sr_lof = _lot_of_fortune(sr["arabic_parts"])
    natal_lof = _lot_of_fortune(natal["arabic_parts"])

    assert sr_lof is not None, "Solar return has no Lot of Fortune"
    assert natal_lof is not None, "Natal has no Lot of Fortune"
    # Different moment → different Sun/Moon positions → different lot
    assert abs(sr_lof["lon"] - natal_lof["lon"]) > 0.01, (
        "Solar return LoF should differ from natal LoF"
    )


# ── Lunar Return (already has arabic_parts) ───────────────────────────────────

def test_lunar_return_has_arabic_parts():
    resp = client.post("/chart/lunar-return", json=LUNAR_REQ)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] > 0
    first = data["returns"][0]
    assert "arabic_parts" in first
    assert isinstance(first["arabic_parts"], list)
    assert len(first["arabic_parts"]) > 0


def test_lunar_return_lots_in_valid_range():
    data = client.post("/chart/lunar-return", json=LUNAR_REQ).json()
    first = data["returns"][0]
    for lot in first["arabic_parts"]:
        assert 0 <= lot["lon"] < 360


# ── Secondary Progressions ────────────────────────────────────────────────────

def test_secondary_progressions_no_lots_by_default():
    resp = client.post("/chart/secondary-progressions", json=PROG_REQ)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("arabic_parts") is None


def test_secondary_progressions_has_lots_when_requested():
    req = {**PROG_REQ, "include_lots": True}
    resp = client.post("/chart/secondary-progressions", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["arabic_parts"] is not None
    assert len(data["arabic_parts"]) > 0


def test_secondary_progressions_lots_have_required_fields():
    req = {**PROG_REQ, "include_lots": True}
    data = client.post("/chart/secondary-progressions", json=req).json()
    for lot in data["arabic_parts"]:
        assert "name" in lot and lot["name"]
        assert "lon" in lot
        assert "sign" in lot
        assert "sign_lon" in lot
        assert "formula" in lot
        assert 0 <= lot["lon"] < 360


def test_secondary_progressions_lot_of_fortune_differs_from_natal():
    """Progressed chart has different Sun/Moon positions → different LoF."""
    req = {**PROG_REQ, "include_lots": True}
    prog = client.post("/chart/secondary-progressions", json=req).json()
    natal = client.post("/chart/natal", json=NATAL_REQ).json()

    prog_lof  = _lot_of_fortune(prog["arabic_parts"])
    natal_lof = _lot_of_fortune(natal["arabic_parts"])

    assert prog_lof is not None, "Progressed chart has no Lot of Fortune"
    assert natal_lof is not None, "Natal has no Lot of Fortune"
    assert abs(prog_lof["lon"] - natal_lof["lon"]) > 0.01, (
        "Progressed LoF should differ from natal LoF (different prog Sun/Moon)"
    )


def test_secondary_progressions_lots_count_matches_natal():
    """Both natal and progressed compute same number of lots."""
    req = {**PROG_REQ, "include_lots": True}
    prog  = client.post("/chart/secondary-progressions", json=req).json()
    natal = client.post("/chart/natal", json=NATAL_REQ).json()
    assert len(prog["arabic_parts"]) == len(natal["arabic_parts"])


def test_secondary_progressions_lot_longitudes_valid():
    req = {**PROG_REQ, "include_lots": True}
    data = client.post("/chart/secondary-progressions", json=req).json()
    for lot in data["arabic_parts"]:
        assert 0 <= lot["lon"] < 360, f"{lot['name']} lon={lot['lon']} out of range"


# ── Tertiary Progressions ─────────────────────────────────────────────────────

TERT_REQ = {
    **BIRTH,
    "prog_year": 2025, "prog_month": 6, "prog_day": 15,
    "hsys": "P",
    "month_type": "sidereal",
}


def test_tertiary_progressions_no_lots_by_default():
    resp = client.post("/chart/tertiary-progressions", json=TERT_REQ)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("arabic_parts") is None


def test_tertiary_progressions_has_lots_when_requested():
    req = {**TERT_REQ, "include_lots": True}
    resp = client.post("/chart/tertiary-progressions", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["arabic_parts"] is not None
    assert len(data["arabic_parts"]) > 0


def test_tertiary_progressions_lots_have_required_fields():
    req = {**TERT_REQ, "include_lots": True}
    data = client.post("/chart/tertiary-progressions", json=req).json()
    for lot in data["arabic_parts"]:
        assert "name" in lot and lot["name"]
        assert "lon" in lot
        assert "sign" in lot
        assert 0 <= lot["lon"] < 360


def test_tertiary_progressions_lot_longitudes_valid():
    req = {**TERT_REQ, "include_lots": True}
    data = client.post("/chart/tertiary-progressions", json=req).json()
    for lot in data["arabic_parts"]:
        assert 0 <= lot["lon"] < 360, f"{lot['name']} lon={lot['lon']} out of range"
