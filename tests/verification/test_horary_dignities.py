"""
Epic 9.3 — Essential Dignities for Horary Significators tests.

POST /chart/horary/dignities evaluates the five essential dignities and
three essential debilities for the querent, quesited, and Moon.

Essential Dignities: Domicile(+5), Exaltation(+4), Triplicity(+3),
                     Term(+2), Face(+1)
Essential Debilities: Detriment(−5), Fall(−4), Peregrine (flag)

Verifies:
  1.  Core: result type is HoraryDignityResult
  2.  Core: day_chart is bool
  3.  Core: house numbers preserved
  4.  Core: significator planet_ids in [0–6]
  5.  Core: significator lons in [0°, 360°)
  6.  Core: significator signs valid
  7.  Core: sign_lon in [0°, 30°)
  8.  Core: score = sum of dignities minus sum of debilities
  9.  Core: strength in {"Dignified","Peregrine","Debilitated"}
  10. Core: day chart detected (Rome 1990 = day chart, Sun in H10)
  11. Core: night chart detected (synthetic Sun in H3)
  12. Core: domicile — Sun in Leo scores +5 for dom
  13. Core: domicile — Moon in Cancer scores +5 for dom
  14. Core: domicile — Saturn in Capricorn scores +5 for dom
  15. Core: exaltation — Sun in Aries scores +4 for exalt
  16. Core: exaltation — Moon in Taurus scores +4 for exalt
  17. Core: exaltation — Jupiter in Cancer scores +4 for exalt
  18. Core: triplicity day — Sun in Aries (fire) day chart gets triplicity
  19. Core: triplicity night — Moon in Taurus (earth) night chart gets triplicity
  20. Core: triplicity sect matters — Sun in Aries night chart gets NO triplicity
  21. Core: term — Mercury in Gemini 0-6° gets own Egyptian term
  22. Core: term — Saturn in Capricorn 22-25° gets own term
  23. Core: term — Sun in Leo 0-5° gets Jupiter term, not Sun term
  24. Core: face — Sun in Gemini 20-30° in its own face
  25. Core: face — Mars in Aries 0-10° in its own face
  26. Core: detriment — Sun in Aquarius is in detriment (−5)
  27. Core: detriment — Saturn in Leo is in detriment (−5)
  28. Core: fall — Moon in Scorpio is in fall (−4)
  29. Core: fall — Venus in Virgo is in fall (−4)
  30. Core: peregrine — planet with no positive dignity
  31. Core: not peregrine when any positive dignity present
  32. Core: strength Dignified when score > 0
  33. Core: strength Peregrine when score == 0
  34. Core: strength Debilitated when score < 0
  35. Core: moon_dignity present with valid strength
  36. API: POST /chart/horary/dignities returns 200
  37. API: day_chart is bool
  38. API: significator signs valid
  39. API: dignity score present
  40. API: strength in valid set
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.horary_dignities import (
    calc_horary_dignities, calc_dignity, HoraryDignityResult,
    _is_day_chart, _EXALTATION, _FALL, _DETRIMENT,
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
_VALID_STRENGTH = {"Dignified", "Peregrine", "Debilitated"}


def _get_chart(y, m, d, h, lat, lon, hsys="P"):
    jd = swe.julday(y, m, d, h, swe.GREG_CAL)
    lons = {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, _FLAGS)
        lons[pid] = r[0]
    cusps_raw, _ = swe.houses(jd, lat, lon, hsys.encode())
    return lons, list(cusps_raw)


# Rome 1990-06-15 10:30 UT — day chart (Sun H10)
# H1=Mercury(Gemini), H7=Jupiter(Cancer)
LONS, CUSPS = _get_chart(1990, 6, 15, 10.5, 41.9, 12.5)

DIGNITY_REQ = {
    "year": 1990, "month": 6, "day": 15,
    "hour": 10, "minute": 30,
    "lat": 41.9, "lon": 12.5, "hsys": "P", "ut_offset": 0,
    "querent_house": 1, "quesited_house": 7,
}


@pytest.fixture(scope="module")
def result():
    return calc_horary_dignities(LONS, CUSPS, querent_house=1, quesited_house=7)


# ── Core structural tests ──────────────────────────────────────────────────────

def test_result_type(result):
    assert isinstance(result, HoraryDignityResult)


def test_day_chart_is_bool(result):
    assert isinstance(result.day_chart, bool)


def test_house_numbers_preserved(result):
    assert result.querent_house == 1
    assert result.quesited_house == 7


def test_significator_ids_valid(result):
    assert 0 <= result.querent_significator.planet_id <= 6
    assert 0 <= result.quesited_significator.planet_id <= 6


def test_significator_lons_in_range(result):
    assert 0.0 <= result.querent_significator.lon < 360.0
    assert 0.0 <= result.quesited_significator.lon < 360.0


def test_significator_signs_valid(result):
    assert result.querent_significator.sign in _VALID_SIGNS
    assert result.quesited_significator.sign in _VALID_SIGNS


def test_sign_lon_in_range(result):
    assert 0.0 <= result.querent_significator.sign_lon < 30.0
    assert 0.0 <= result.quesited_significator.sign_lon < 30.0


def test_score_formula(result):
    """Score = positive dignities - debilities."""
    for sd in [result.querent_significator, result.quesited_significator]:
        d = sd.dignity
        pos = (5 if d.domicile else 0) + (4 if d.exaltation else 0) + \
              (3 if d.triplicity else 0) + (2 if d.term else 0) + (1 if d.face else 0)
        neg = (-5 if d.detriment else 0) + (-4 if d.fall else 0)
        assert d.score == pos + neg, f"{sd.planet_name}: score {d.score} != {pos+neg}"


def test_strength_valid(result):
    for sd in [result.querent_significator, result.quesited_significator]:
        assert sd.dignity.strength in _VALID_STRENGTH


# ── Sect / Day–Night tests ─────────────────────────────────────────────────────

def test_day_chart_rome_1990(result):
    """Rome 1990 10:30 UT — Sun in H10 → day chart."""
    assert result.day_chart is True


def test_night_chart_detection():
    """Synthetic chart: Sun placed in H3 (below horizon) → night chart."""
    # Equal cusps with H1=0° Aries; H3 cusp=60°. Place Sun at 65° → H3.
    cusps = [i * 30.0 for i in range(12)]
    lons_night = dict(LONS)
    lons_night[0] = 65.0   # Sun at 65° Taurus, house 3
    assert _is_day_chart(65.0, cusps) is False


# ── Domicile tests ─────────────────────────────────────────────────────────────

def test_domicile_sun_in_leo():
    """Sun (pid=0) at 130° Leo → domicile=True, score at least +5."""
    d = calc_dignity(0, 130.0, True)
    assert d.domicile is True
    assert d.score >= 5


def test_domicile_moon_in_cancer():
    """Moon (pid=1) at 95° Cancer → domicile=True."""
    d = calc_dignity(1, 95.0, True)
    assert d.domicile is True
    assert d.score >= 5


def test_domicile_saturn_in_capricorn():
    """Saturn (pid=6) at 285° Capricorn → domicile=True."""
    d = calc_dignity(6, 285.0, True)
    assert d.domicile is True
    assert d.score >= 5


# ── Exaltation tests ───────────────────────────────────────────────────────────

def test_exaltation_sun_in_aries():
    """Sun at 10° Aries → exaltation=True, score at least +4."""
    d = calc_dignity(0, 10.0, True)
    assert d.exaltation is True
    assert d.score >= 4


def test_exaltation_moon_in_taurus():
    """Moon at 35° Taurus → exaltation=True."""
    d = calc_dignity(1, 35.0, True)
    assert d.exaltation is True
    assert d.score >= 4


def test_exaltation_jupiter_in_cancer(result):
    """Rome 1990: Jupiter at Cancer → exaltation=True."""
    d = result.quesited_significator.dignity
    assert result.quesited_significator.sign == "Cancer"
    assert d.exaltation is True


# ── Triplicity tests ───────────────────────────────────────────────────────────

def test_triplicity_day_sun_in_fire():
    """Sun in Aries (fire) on day chart → triplicity=True (Sun is fire day lord)."""
    d = calc_dignity(0, 10.0, True)    # day chart
    assert d.triplicity is True


def test_triplicity_night_moon_in_earth():
    """Moon in Taurus (earth) on night chart → triplicity=True (Moon is earth night lord)."""
    d = calc_dignity(1, 35.0, False)   # night chart
    assert d.triplicity is True


def test_triplicity_sect_matters():
    """Sun in Aries on NIGHT chart → triplicity=False (fire night lord = Jupiter)."""
    d = calc_dignity(0, 10.0, False)   # night chart
    assert d.triplicity is False


# ── Term tests ─────────────────────────────────────────────────────────────────

def test_term_mercury_in_gemini(result):
    """Rome 1990: Mercury at Gemini 5.58° → in Mercury's own term (0-7°)."""
    d = result.querent_significator.dignity
    assert result.querent_significator.sign == "Gemini"
    assert d.term is True


def test_term_saturn_in_capricorn_own_term():
    """Saturn (pid=6) at 24° Capricorn (sign_lon=24°) → Saturn term (22-26°)."""
    d = calc_dignity(6, 294.0, True)   # 294° = Capricorn 24°
    assert d.term is True


def test_term_sun_not_in_own_leo_term():
    """Sun at 3° Leo (sign_lon=3°) → Jupiter term (0-6°), not Sun → term=False."""
    d = calc_dignity(0, 123.0, True)   # 123° = Leo 3°
    assert d.term is False


# ── Face tests ─────────────────────────────────────────────────────────────────

def test_face_sun_in_gemini_third_decan():
    """Sun at 84° Gemini (sign_lon=24°) → Gemini 20-30° = Sun's face."""
    d = calc_dignity(0, 84.0, True)
    assert d.face is True


def test_face_mars_in_aries_first_decan():
    """Mars at 5° Aries (sign_lon=5°) → Aries 0-10° = Mars's face."""
    d = calc_dignity(4, 5.0, True)
    assert d.face is True


# ── Detriment tests ───────────────────────────────────────────────────────────

def test_detriment_sun_in_aquarius():
    """Sun (pid=0) at 310° Aquarius → detriment=True, score ≤ -5."""
    d = calc_dignity(0, 310.0, True)
    assert d.detriment is True
    assert d.score <= -5


def test_detriment_saturn_in_leo():
    """Saturn (pid=6) at 130° Leo → detriment=True."""
    d = calc_dignity(6, 130.0, True)
    assert d.detriment is True
    assert d.score <= -5


# ── Fall tests ────────────────────────────────────────────────────────────────

def test_fall_moon_in_scorpio():
    """Moon (pid=1) at 220° Scorpio → fall=True."""
    d = calc_dignity(1, 220.0, True)
    assert d.fall is True
    assert d.score <= -4


def test_fall_venus_in_virgo():
    """Venus (pid=3) at 160° Virgo → fall=True.
    Score may still be positive on a day chart because Venus is earth triplicity day lord.
    """
    d = calc_dignity(3, 160.0, True)
    assert d.fall is True
    # Venus also gets triplicity (+3) in Virgo on a day chart, so score can be positive.
    # Verify the fall flag is correctly set; score test handles arithmetic separately.


# ── Peregrine tests ───────────────────────────────────────────────────────────

def test_peregrine_saturn_in_taurus():
    """Saturn at 45° Taurus: no domicile/exalt/trip/term/face → peregrine=True."""
    d = calc_dignity(6, 45.0, True)    # Taurus 15°, day chart
    assert d.peregrine is True
    assert d.score == 0


def test_not_peregrine_when_dignified():
    """Planet with any positive dignity is NOT peregrine."""
    d = calc_dignity(0, 130.0, True)   # Sun in Leo (domicile)
    assert d.peregrine is False
    d2 = calc_dignity(1, 35.0, False)  # Moon in Taurus (exalt+trip night)
    assert d2.peregrine is False


# ── Strength label tests ───────────────────────────────────────────────────────

def test_strength_dignified_when_positive():
    """score > 0 → strength='Dignified'."""
    d = calc_dignity(0, 130.0, True)   # Sun in Leo: score=+8
    assert d.score > 0
    assert d.strength == "Dignified"


def test_strength_peregrine_when_zero():
    """score = 0 and no positive dignity → strength='Peregrine'."""
    d = calc_dignity(6, 45.0, True)    # Saturn at Taurus 15°
    assert d.score == 0
    assert d.strength == "Peregrine"


def test_strength_debilitated_when_negative():
    """score < 0 → strength='Debilitated'."""
    d = calc_dignity(0, 310.0, True)   # Sun in Aquarius (detriment)
    assert d.score < 0
    assert d.strength == "Debilitated"


# ── Moon co-significator ──────────────────────────────────────────────────────

def test_moon_dignity_present(result):
    """Moon dignity is present with a valid strength."""
    assert result.moon_dignity is not None
    assert result.moon_dignity.strength in _VALID_STRENGTH


# ── API endpoint tests ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_resp():
    r = client.post("/chart/horary/dignities", json=DIGNITY_REQ)
    assert r.status_code == 200
    return r.json()


def test_api_200(api_resp):
    assert "querent_significator" in api_resp


def test_api_day_chart_is_bool(api_resp):
    assert isinstance(api_resp["day_chart"], bool)


def test_api_significator_signs_valid(api_resp):
    assert api_resp["querent_significator"]["sign"] in _VALID_SIGNS
    assert api_resp["quesited_significator"]["sign"] in _VALID_SIGNS


def test_api_dignity_score_present(api_resp):
    assert "score" in api_resp["querent_significator"]["dignity"]
    assert "score" in api_resp["quesited_significator"]["dignity"]


def test_api_strength_valid(api_resp):
    assert api_resp["querent_significator"]["dignity"]["strength"] in _VALID_STRENGTH
    assert api_resp["quesited_significator"]["dignity"]["strength"] in _VALID_STRENGTH
