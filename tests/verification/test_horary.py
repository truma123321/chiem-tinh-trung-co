"""
Epic 9.1 — Horary Judgment Framework tests.

POST /chart/horary evaluates chart radicality by checking six classical
impediments per William Lilly (Christian Astrology, Book 1).

Checks:
  1. early_asc    — ASC degree within sign < 3°
  2. late_asc     — ASC degree within sign > 27°
  3. saturn_h1    — Saturn in house 1
  4. saturn_h7    — Saturn in house 7
  5. moon_voc     — Moon Void of Course
  6. via_combusta — Moon between 15° Libra and 15° Scorpio

Radicality: 0 factors → Radical | 1 → Doubt | 2+ → Non-radical

Verifies:
  1.  Core: result type is HoraryResult
  2.  Core: asc in [0°, 360°)
  3.  Core: asc_degree in [0°, 30°)
  4.  Core: asc_sign is valid zodiac sign
  5.  Core: moon_lon in [0°, 360°)
  6.  Core: moon_sign is valid zodiac sign
  7.  Core: saturn_house in 1–12
  8.  Core: exactly 6 checks
  9.  Core: check factors are the canonical 6
  10. Core: radicality ∈ {"Radical", "Doubt", "Non-radical"}
  11. Core: negative_count == sum of present checks
  12. Core: negative_count 0 → Radical
  13. Core: negative_count 1 → Doubt
  14. Core: negative_count 2 → Non-radical
  15. Core: early_asc triggers when asc_degree < 3°
  16. Core: late_asc triggers when asc_degree > 27°
  17. Core: early_asc and late_asc never both True
  18. Core: via_combusta triggers when moon in [195°, 225°]
  19. Core: via_combusta False outside [195°, 225°]
  20. Core: moon_voc True → next_aspect_planet/name/orb are None
  21. Core: moon_voc False → next_aspect_planet/name/orb are not None
  22. Core: next_aspect_orb > 0 when not VOC
  23. Core: next_aspect_name is valid Ptolemaic aspect name
  24. Core: saturn_h1 True when Saturn in house 1
  25. Core: saturn_h7 True when Saturn in house 7
  26. Core: saturn_h1 and saturn_h7 never both True
  27. Core: asc_degree == asc % 30 (within 0.001)
  28. Core: asc_sign matches sign of asc longitude
  29. Core: moon_sign matches sign of moon longitude
  30. API: POST /chart/horary returns 200
  31. API: radicality in valid set
  32. API: exactly 6 checks
  33. API: check factors are canonical
  34. API: asc in [0°, 360°)
  35. API: moon_lon in [0°, 360°)
  36. API: saturn_house in 1–12
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.horary import (
    calc_horary, HoraryResult,
    VIA_COMBUSTA_START, VIA_COMBUSTA_END,
    EARLY_ASC_THRESHOLD, LATE_ASC_THRESHOLD,
    _voc_and_next, _find_house,
)

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

client = TestClient(app)

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

_VALID_SIGNS = {
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
}
_VALID_ASPECTS = {"Conjunction", "Sextile", "Square", "Trine", "Opposition"}
_CANONICAL_FACTORS = {
    "early_asc", "late_asc", "saturn_h1", "saturn_h7", "moon_voc", "via_combusta",
}
_VALID_RADICALITY = {"Radical", "Doubt", "Non-radical"}


def _get_chart(y, m, d, h, lat, lon, hsys="P"):
    jd = swe.julday(y, m, d, h, swe.GREG_CAL)
    lons, speeds = {}, {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, _FLAGS)
        lons[pid] = r[0]
        speeds[pid] = r[3]
    cusps_raw, ascmc = swe.houses(jd, lat, lon, hsys.encode())
    return lons, speeds, ascmc[0], list(cusps_raw)


# Standard chart: Rome 1990-06-15 10:30 UT
LONS, SPEEDS, ASC, CUSPS = _get_chart(1990, 6, 15, 10.5, 41.9, 12.5)

HORARY_REQ = {
    "year": 1990, "month": 6, "day": 15,
    "hour": 10, "minute": 30,
    "lat": 41.9, "lon": 12.5, "hsys": "P", "ut_offset": 0,
}


@pytest.fixture(scope="module")
def result():
    return calc_horary(LONS, SPEEDS, ASC, CUSPS)


# ── Core tests ─────────────────────────────────────────────────────────────────

def test_result_type(result):
    assert isinstance(result, HoraryResult)


def test_asc_in_range(result):
    assert 0.0 <= result.asc < 360.0


def test_asc_degree_in_range(result):
    assert 0.0 <= result.asc_degree < 30.0


def test_asc_sign_valid(result):
    assert result.asc_sign in _VALID_SIGNS


def test_moon_lon_in_range(result):
    assert 0.0 <= result.moon_lon < 360.0


def test_moon_sign_valid(result):
    assert result.moon_sign in _VALID_SIGNS


def test_saturn_house_range(result):
    assert 1 <= result.saturn_house <= 12


def test_six_checks(result):
    assert len(result.checks) == 6


def test_check_factors_canonical(result):
    factors = {c.factor for c in result.checks}
    assert factors == _CANONICAL_FACTORS


def test_radicality_valid(result):
    assert result.radicality in _VALID_RADICALITY


def test_negative_count_matches_present(result):
    expected = sum(1 for c in result.checks if c.present)
    assert result.negative_count == expected


def test_zero_negatives_is_radical():
    """Manually craft a chart with 0 negatives → Radical."""
    # ASC at 15° Aries (asc_degree=15, not early/late)
    # Moon at 15.1° Aries, Sun at 20° Aries → Moon applies to Sun conjunction in same sign
    # Saturn at 150° Leo → house 5 (not h1 or h7)
    # Moon not in Via Combusta
    lons = {0: 20.0, 1: 15.1, 2: 60.0, 3: 90.0, 4: 120.0, 5: 240.0, 6: 150.0}
    speeds = {pid: 1.0 for pid in range(7)}
    asc = 15.0  # 15° Aries — asc_degree = 15
    cusps = [15.0 + i * 30.0 for i in range(12)]
    res = calc_horary(lons, speeds, asc, cusps)
    assert res.radicality == "Radical"
    assert res.negative_count == 0


def test_one_negative_is_doubt():
    """Exactly 1 negative factor → Doubt (early_asc only)."""
    # ASC at 1° Aries → early_asc triggers (1 negative)
    # Moon at 15.1° Aries, Sun at 20° Aries → NOT VOC
    # Saturn at 150° → house 5 (not h1 or h7)
    # Moon not in Via Combusta
    lons = {0: 20.0, 1: 15.1, 2: 60.0, 3: 90.0, 4: 120.0, 5: 240.0, 6: 150.0}
    speeds = {pid: 1.0 for pid in range(7)}
    asc = 1.0   # 1° Aries → early_asc triggers
    cusps = [1.0 + i * 30.0 for i in range(12)]
    res = calc_horary(lons, speeds, asc, cusps)
    early_check = next(c for c in res.checks if c.factor == "early_asc")
    assert early_check.present
    assert res.radicality == "Doubt"
    assert res.negative_count == 1


def test_two_negatives_is_non_radical():
    """2+ negative factors → Non-radical."""
    lons = {0: 15.0, 1: 15.1, 2: 30.0, 3: 60.0, 4: 90.0, 5: 120.0, 6: 150.0}
    speeds = {pid: 1.0 for pid in range(7)}
    asc = 1.0   # early_asc
    # Saturn in house 1: place Saturn just above ASC
    cusps = [1.0 + i * 30.0 for i in range(12)]
    lons[6] = 2.0   # Saturn at 2° Aries, house 1
    res = calc_horary(lons, speeds, asc, cusps)
    assert res.negative_count >= 2
    assert res.radicality == "Non-radical"


def test_early_asc_triggers():
    """ASC degree < 3° → early_asc present."""
    lons = {0: 45.0, 1: 90.0, 2: 135.0, 3: 180.0, 4: 225.0, 5: 270.0, 6: 315.0}
    speeds = {pid: 1.0 for pid in range(7)}
    asc = 2.0   # 2° Aries
    cusps = [0.0 + i * 30.0 for i in range(12)]
    res = calc_horary(lons, speeds, asc, cusps)
    check = next(c for c in res.checks if c.factor == "early_asc")
    assert check.present
    assert res.asc_degree < EARLY_ASC_THRESHOLD


def test_late_asc_triggers():
    """ASC degree > 27° → late_asc present."""
    lons = {0: 45.0, 1: 90.0, 2: 135.0, 3: 180.0, 4: 225.0, 5: 270.0, 6: 315.0}
    speeds = {pid: 1.0 for pid in range(7)}
    asc = 28.0  # 28° Aries
    cusps = [0.0 + i * 30.0 for i in range(12)]
    res = calc_horary(lons, speeds, asc, cusps)
    check = next(c for c in res.checks if c.factor == "late_asc")
    assert check.present
    assert res.asc_degree > LATE_ASC_THRESHOLD


def test_early_and_late_asc_never_both():
    """early_asc and late_asc are mutually exclusive."""
    for asc_lon in [0.0, 1.0, 2.5, 15.0, 27.5, 28.0, 29.9, 30.0, 45.0, 180.0]:
        lons = {pid: (asc_lon + pid * 40) % 360 for pid in range(7)}
        speeds = {pid: 1.0 for pid in range(7)}
        cusps = [asc_lon + i * 30.0 for i in range(12)]
        res = calc_horary(lons, speeds, asc_lon, cusps)
        ea = next(c for c in res.checks if c.factor == "early_asc")
        la = next(c for c in res.checks if c.factor == "late_asc")
        assert not (ea.present and la.present), f"Both present at asc={asc_lon}"


def test_via_combusta_triggers():
    """Moon at 200° (Libra 20°) → via_combusta present."""
    lons = {0: 45.0, 1: 200.0, 2: 135.0, 3: 180.0, 4: 225.0, 5: 270.0, 6: 315.0}
    speeds = {pid: 1.0 for pid in range(7)}
    asc = 15.0
    cusps = [0.0 + i * 30.0 for i in range(12)]
    res = calc_horary(lons, speeds, asc, cusps)
    check = next(c for c in res.checks if c.factor == "via_combusta")
    assert check.present
    assert VIA_COMBUSTA_START <= res.moon_lon <= VIA_COMBUSTA_END


def test_via_combusta_false_outside():
    """Moon at 15° (Aries) → via_combusta False."""
    lons = {0: 45.0, 1: 15.0, 2: 90.0, 3: 135.0, 4: 180.0, 5: 270.0, 6: 315.0}
    speeds = {pid: 1.0 for pid in range(7)}
    asc = 15.0
    cusps = [0.0 + i * 30.0 for i in range(12)]
    res = calc_horary(lons, speeds, asc, cusps)
    check = next(c for c in res.checks if c.factor == "via_combusta")
    assert not check.present


def test_moon_voc_returns_none_fields():
    """VOC Moon → next_aspect_planet, name, orb are None."""
    # Moon at 29° Aries (sign_end=30°), no contacts between 29° and 30°
    # Place all planets far from Moon's sign boundary
    lons = {0: 100.0, 1: 29.0, 2: 150.0, 3: 200.0, 4: 250.0, 5: 300.0, 6: 350.0}
    speeds = {pid: 1.0 for pid in range(7)}
    asc = 15.0
    cusps = [0.0 + i * 30.0 for i in range(12)]
    res = calc_horary(lons, speeds, asc, cusps)
    if res.moon_voc:
        assert res.next_aspect_planet is None
        assert res.next_aspect_name is None
        assert res.next_aspect_orb is None


def test_moon_not_voc_has_next_aspect(result):
    """Non-VOC Moon → next_aspect fields are populated."""
    if not result.moon_voc:
        assert result.next_aspect_planet is not None
        assert result.next_aspect_name is not None
        assert result.next_aspect_orb is not None


def test_next_aspect_orb_positive(result):
    """next_aspect_orb > 0 when Moon is not VOC."""
    if not result.moon_voc:
        assert result.next_aspect_orb > 0.0


def test_next_aspect_name_valid(result):
    """next_aspect_name is a valid Ptolemaic aspect."""
    if not result.moon_voc and result.next_aspect_name is not None:
        assert result.next_aspect_name in _VALID_ASPECTS


def test_saturn_h1_trigger():
    """Saturn in house 1 → saturn_h1 present."""
    lons = {0: 45.0, 1: 90.0, 2: 135.0, 3: 180.0, 4: 225.0, 5: 270.0, 6: 2.0}
    speeds = {pid: 1.0 for pid in range(7)}
    asc = 1.0
    cusps = [1.0 + i * 30.0 for i in range(12)]
    res = calc_horary(lons, speeds, asc, cusps)
    check = next(c for c in res.checks if c.factor == "saturn_h1")
    assert check.present
    assert res.saturn_house == 1


def test_saturn_h7_trigger():
    """Saturn in house 7 → saturn_h7 present."""
    lons = {0: 45.0, 1: 90.0, 2: 135.0, 3: 180.0, 4: 225.0, 5: 270.0, 6: 182.0}
    speeds = {pid: 1.0 for pid in range(7)}
    asc = 1.0
    cusps = [1.0 + i * 30.0 for i in range(12)]
    res = calc_horary(lons, speeds, asc, cusps)
    check = next(c for c in res.checks if c.factor == "saturn_h7")
    assert check.present
    assert res.saturn_house == 7


def test_saturn_h1_and_h7_never_both():
    """saturn_h1 and saturn_h7 cannot both be True."""
    lons = {0: 45.0, 1: 90.0, 2: 135.0, 3: 180.0, 4: 225.0, 5: 270.0, 6: 5.0}
    speeds = {pid: 1.0 for pid in range(7)}
    asc = 1.0
    cusps = [1.0 + i * 30.0 for i in range(12)]
    res = calc_horary(lons, speeds, asc, cusps)
    h1 = next(c for c in res.checks if c.factor == "saturn_h1")
    h7 = next(c for c in res.checks if c.factor == "saturn_h7")
    assert not (h1.present and h7.present)


def test_asc_degree_formula(result):
    """asc_degree == asc % 30."""
    expected = result.asc % 30.0
    assert abs(result.asc_degree - expected) < 0.001


def test_asc_sign_matches_lon(result):
    _SIGNS = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    ]
    idx = int(result.asc / 30) % 12
    assert result.asc_sign == _SIGNS[idx]


def test_moon_sign_matches_lon(result):
    _SIGNS = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    ]
    idx = int(result.moon_lon / 30) % 12
    assert result.moon_sign == _SIGNS[idx]


# ── API endpoint tests ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_resp():
    r = client.post("/chart/horary", json=HORARY_REQ)
    assert r.status_code == 200
    return r.json()


def test_api_200(api_resp):
    assert "radicality" in api_resp


def test_api_radicality_valid(api_resp):
    assert api_resp["radicality"] in _VALID_RADICALITY


def test_api_six_checks(api_resp):
    assert len(api_resp["checks"]) == 6


def test_api_check_factors_canonical(api_resp):
    factors = {c["factor"] for c in api_resp["checks"]}
    assert factors == _CANONICAL_FACTORS


def test_api_asc_in_range(api_resp):
    assert 0.0 <= api_resp["asc"] < 360.0


def test_api_moon_lon_in_range(api_resp):
    assert 0.0 <= api_resp["moon_lon"] < 360.0


def test_api_saturn_house_range(api_resp):
    assert 1 <= api_resp["saturn_house"] <= 12
