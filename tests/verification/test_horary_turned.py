"""
Epic 10.4 — Horary Turned Charts tests.

Verifies:
  1. Core: H10 from H3 → natal H12  (sibling's career)
  2. Core: H2  from H3 → natal H4   (sibling's money)
  3. Core: H6  from H10 → natal H3  (mother's illness)
  4. Core: H2  from H11 → natal H12 (friend's money)
  5. Core: identity case from_house=1 → turned chart = natal chart
  6. Core: all_turned_houses has exactly 12 items
  7. Core: all_turned_houses ordered by turned_house 1–12
  8. Core: turned_house H1 always maps to natal from_house
  9. Core: lord derivation correct (Aries cusp → Mars)
 10. Core: lord derivation correct (Taurus cusp → Venus)
 11. Core: explanation string is non-empty and human-readable
 12. Core: explanation mentions natal house number
 13. Core: from_house_topic present and non-empty
 14. Core: ValueError on from_house=0
 15. Core: ValueError on quesited_house=13
 16. API: POST /chart/horary/turned returns 200
 17. API: response has all required fields
 18. API: all_turned_houses has 12 items
 19. API: turned_quesited_house matches formula
 20. API: turned_lord_name is a valid planet name
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import pytest
from fastapi.testclient import TestClient
from main import app
from core.horary_turned import calc_horary_turned

client = TestClient(app)

# ── Equal-house cusps helper ──────────────────────────────────────────────────

def _make_cusps(asc_lon: float) -> list[float]:
    """Equal-house cusps — 30° apart, starting at asc_lon."""
    return [(asc_lon + 30 * h) % 360 for h in range(12)]


# Aries ASC: H1=0°(Aries), H2=30°(Taurus), H3=60°(Gemini) …
ARIES_ASC = _make_cusps(0.0)

# Taurus ASC: H1=30°(Taurus) …
TAURUS_ASC = _make_cusps(30.0)

_VALID_PLANET_NAMES = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}

# ── Core formula tests ────────────────────────────────────────────────────────

def test_h10_from_h3_is_natal_h12():
    """Sibling's career: H10 from H3 = ((3-1)+(10-1))%12+1 = 12."""
    res = calc_horary_turned(ARIES_ASC, from_house=3, quesited_house=10)
    assert res.turned_quesited_house == 12


def test_h2_from_h3_is_natal_h4():
    """Sibling's money: H2 from H3 = ((3-1)+(2-1))%12+1 = 4."""
    res = calc_horary_turned(ARIES_ASC, from_house=3, quesited_house=2)
    assert res.turned_quesited_house == 4


def test_h6_from_h10_is_natal_h3():
    """Mother's illness: H6 from H10 = ((10-1)+(6-1))%12+1 = 3."""
    res = calc_horary_turned(ARIES_ASC, from_house=10, quesited_house=6)
    assert res.turned_quesited_house == 3


def test_h2_from_h11_is_natal_h12():
    """Friend's money: H2 from H11 = ((11-1)+(2-1))%12+1 = 12."""
    res = calc_horary_turned(ARIES_ASC, from_house=11, quesited_house=2)
    assert res.turned_quesited_house == 12


def test_identity_from_house_1():
    """from_house=1 → turned chart = natal chart (H7 from H1 = natal H7)."""
    res = calc_horary_turned(ARIES_ASC, from_house=1, quesited_house=7)
    assert res.turned_quesited_house == 7


def test_identity_all_turned_match_natal():
    """from_house=1 → every turned house equals its natal house."""
    res = calc_horary_turned(ARIES_ASC, from_house=1, quesited_house=1)
    for item in res.all_turned_houses:
        assert item.turned_house == item.natal_house


# ── all_turned_houses structure ───────────────────────────────────────────────

def test_all_turned_houses_count():
    res = calc_horary_turned(ARIES_ASC, from_house=3, quesited_house=10)
    assert len(res.all_turned_houses) == 12


def test_all_turned_houses_ordered():
    res = calc_horary_turned(ARIES_ASC, from_house=3, quesited_house=10)
    for i, item in enumerate(res.all_turned_houses, start=1):
        assert item.turned_house == i


def test_turned_house_1_maps_to_from_house():
    """Turned H1 is always the 'from_house' perspective — natal = from_house."""
    for fh in range(1, 13):
        res = calc_horary_turned(ARIES_ASC, from_house=fh, quesited_house=1)
        assert res.all_turned_houses[0].natal_house == fh


# ── Lord derivation ───────────────────────────────────────────────────────────

def test_aries_cusp_lord_is_mars():
    """H1 cusp at 0° (Aries) → Mars (pid=4)."""
    # from_house=1 → turned H1 = natal H1, cusp at 0° (Aries)
    res = calc_horary_turned(ARIES_ASC, from_house=1, quesited_house=1)
    h1 = res.all_turned_houses[0]
    assert h1.lord_name == "Mars"
    assert h1.lord_id == 4


def test_taurus_cusp_lord_is_venus():
    """H1 cusp at 30° (Taurus) → Venus (pid=3)."""
    res = calc_horary_turned(TAURUS_ASC, from_house=1, quesited_house=1)
    h1 = res.all_turned_houses[0]
    assert h1.lord_name == "Venus"
    assert h1.lord_id == 3


# ── Explanation string ────────────────────────────────────────────────────────

def test_explanation_non_empty():
    res = calc_horary_turned(ARIES_ASC, from_house=3, quesited_house=10)
    assert isinstance(res.explanation, str)
    assert len(res.explanation) > 10


def test_explanation_mentions_natal_house():
    res = calc_horary_turned(ARIES_ASC, from_house=3, quesited_house=10)
    assert "H12" in res.explanation or "12" in res.explanation


def test_from_house_topic_non_empty():
    res = calc_horary_turned(ARIES_ASC, from_house=3, quesited_house=10)
    assert isinstance(res.from_house_topic, str)
    assert len(res.from_house_topic) > 0


# ── Validation errors ─────────────────────────────────────────────────────────

def test_raises_on_from_house_zero():
    with pytest.raises(ValueError):
        calc_horary_turned(ARIES_ASC, from_house=0, quesited_house=7)


def test_raises_on_quesited_house_13():
    with pytest.raises(ValueError):
        calc_horary_turned(ARIES_ASC, from_house=1, quesited_house=13)


# ── API tests ─────────────────────────────────────────────────────────────────

BASE_REQ = {
    "year": 1990, "month": 6, "day": 15,
    "hour": 10, "minute": 30,
    "lat": 41.9, "lon": 12.5,
    "hsys": "P", "ut_offset": 0.0,
    "from_house": 3,
    "quesited_house": 10,
    "querent_house": 1,
}


def test_api_returns_200():
    resp = client.post("/chart/horary/turned", json=BASE_REQ)
    assert resp.status_code == 200


def test_api_required_fields():
    data = client.post("/chart/horary/turned", json=BASE_REQ).json()
    for field in (
        "from_house", "from_house_topic", "querent_house",
        "original_quesited_house", "turned_quesited_house",
        "turned_lord_id", "turned_lord_name", "explanation",
        "all_turned_houses",
    ):
        assert field in data, f"Missing field: {field}"


def test_api_all_turned_houses_count():
    data = client.post("/chart/horary/turned", json=BASE_REQ).json()
    assert len(data["all_turned_houses"]) == 12


def test_api_turned_quesited_matches_formula():
    """H10 from H3 → natal H12."""
    data = client.post("/chart/horary/turned", json=BASE_REQ).json()
    # from_house=3, quesited_house=10 → (2+9)%12+1 = 12
    assert data["turned_quesited_house"] == 12


def test_api_turned_lord_is_valid_planet():
    data = client.post("/chart/horary/turned", json=BASE_REQ).json()
    assert data["turned_lord_name"] in _VALID_PLANET_NAMES
