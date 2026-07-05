"""
Epic 6.3 — Triplicity Lords Detail tests.

Verifies:
  1.  Core: calc_dignities returns triplicity_group in {"Fire","Earth","Air","Water"}
  2.  Core: triplicity_day_lord / night_lord / part_lord are valid planet IDs (0-6)
  3.  Core: three lords are distinct from each other
  4.  Core: lord names match expected name for their planet ID
  5.  Core: Sun in Fire sign → day=Sun, night=Jupiter, part=Saturn
  6.  Core: Moon in Earth sign → day=Venus, night=Moon, part=Mars
  7.  Core: Mercury in Air sign → day=Saturn, night=Mercury, part=Jupiter
  8.  Core: Venus in Water sign → day=Venus, night=Mars, part=Moon
  9.  Core: triplicity_role is "day" when planet is day lord and daytime=True
 10.  Core: triplicity_role is "night" when planet is night lord and daytime=False
 11.  Core: triplicity_role is "participating" when planet is part lord
 12.  Core: triplicity_role is "none" when planet has no triplicity role
 13.  Core: triplicity=True iff planet matches the active (day/night) lord
 14.  Core: triplicity=False for the participating lord
 15.  Core: Dorothean table spot-checks (all 4 elements × day/night lords)
 16.  Core: sign-to-group assignment is correct for all 12 signs
 17.  Core: triplicity_role is independent of daytime (lords don't change, only active)
 18.  API: dignities list has 7 items
 19.  API: each dignity has triplicity_group, day/night/part lord fields
 20.  API: triplicity_role in {"day","night","participating","none"}
 21.  API: triplicity_group in {"Fire","Earth","Air","Water"}
 22.  API: triplicity bool matches (planet_id == day_lord and day_chart)
          or (planet_id == night_lord and not day_chart)
 23.  API: Sun in Gemini day chart → Air group, triplicity=False (Saturn is day lord)
 24.  API: Saturn in Gemini day chart → Air group, triplicity=True (Saturn is day lord)
 25.  API: existing fields (domicile, exaltation, score, etc.) still present
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import swisseph as swe
from fastapi.testclient import TestClient
from main import app
from core.dignities import (
    calc_dignities, is_day_chart,
    SUN, MOON, MERCURY, VENUS, MARS, JUPITER, SATURN,
    PLANET_NAMES,
    _TRIPLICITY_GROUP, _TRIPLICITY_RULERS, _TRIPLICITY_NAMES,
)

# ── Ephemeris ──────────────────────────────────────────────────────────────────

EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../backend/ephe")
)
swe.set_ephe_path(EPHE_PATH)

client = TestClient(app)

NATAL_REQ = {
    "year": 1990, "month": 6, "day": 15,
    "hour": 10, "minute": 30,
    "lat": 41.9, "lon": 12.5,
    "hsys": "P",
    "ut_offset": 0,
}

# ── Expected triplicity table (group index → [day, night, part]) ────────────
# Group indices: 0=Fire, 1=Air, 2=Water, 3=Earth

EXPECTED_RULERS = {
    "Fire":  (SUN,   JUPITER, SATURN),   # Aries, Leo, Sag
    "Air":   (SATURN, MERCURY, JUPITER), # Gemini, Libra, Aqu
    "Water": (VENUS,  MARS,    MOON),    # Cancer, Scorpio, Pis
    "Earth": (VENUS,  MOON,    MARS),    # Taurus, Virgo, Cap
}

# Sign index → expected group name
SIGN_GROUPS = [
    "Fire",  # 0 Aries
    "Earth", # 1 Taurus
    "Air",   # 2 Gemini
    "Water", # 3 Cancer
    "Fire",  # 4 Leo
    "Earth", # 5 Virgo
    "Air",   # 6 Libra
    "Water", # 7 Scorpio
    "Fire",  # 8 Sagittarius
    "Earth", # 9 Capricorn
    "Air",   # 10 Aquarius
    "Water", # 11 Pisces
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def dignity_at(planet_id: int, sign_idx: int, daytime: bool):
    """Return DignityResult placing planet_id at 0° of sign_idx."""
    return calc_dignities(planet_id, sign_idx * 30.0, daytime)


# ── Core tests — structure ─────────────────────────────────────────────────────

def test_triplicity_group_valid():
    valid = {"Fire", "Earth", "Air", "Water"}
    for sign in range(12):
        for pid in range(7):
            d = dignity_at(pid, sign, True)
            assert d.triplicity_group in valid, (
                f"sign={sign} pid={pid}: unexpected group '{d.triplicity_group}'"
            )


def test_lord_ids_valid_range():
    for sign in range(12):
        d = dignity_at(SUN, sign, True)
        assert 0 <= d.triplicity_day_lord <= 6
        assert 0 <= d.triplicity_night_lord <= 6
        assert 0 <= d.triplicity_part_lord <= 6


def test_three_lords_distinct():
    """Day, night, and participating lords must all be different planets."""
    for sign in range(12):
        d = dignity_at(SUN, sign, True)
        lords = {d.triplicity_day_lord, d.triplicity_night_lord, d.triplicity_part_lord}
        assert len(lords) == 3, (
            f"sign={sign} ({d.triplicity_group}): lords not distinct: "
            f"{d.triplicity_day_lord_name}/{d.triplicity_night_lord_name}/{d.triplicity_part_lord_name}"
        )


def test_lord_names_match_ids():
    for sign in range(12):
        d = dignity_at(SUN, sign, True)
        assert d.triplicity_day_lord_name   == PLANET_NAMES[d.triplicity_day_lord]
        assert d.triplicity_night_lord_name == PLANET_NAMES[d.triplicity_night_lord]
        assert d.triplicity_part_lord_name  == PLANET_NAMES[d.triplicity_part_lord]


# ── Core tests — Dorothean table spot-checks ───────────────────────────────────

def test_fire_triplicity_lords():
    for sign_idx in [0, 4, 8]:   # Aries, Leo, Sag
        d = dignity_at(SUN, sign_idx, True)
        assert d.triplicity_group == "Fire"
        assert d.triplicity_day_lord   == SUN
        assert d.triplicity_night_lord == JUPITER
        assert d.triplicity_part_lord  == SATURN


def test_earth_triplicity_lords():
    for sign_idx in [1, 5, 9]:   # Taurus, Virgo, Cap
        d = dignity_at(SUN, sign_idx, True)
        assert d.triplicity_group == "Earth"
        assert d.triplicity_day_lord   == VENUS
        assert d.triplicity_night_lord == MOON
        assert d.triplicity_part_lord  == MARS


def test_air_triplicity_lords():
    for sign_idx in [2, 6, 10]:  # Gemini, Libra, Aqu
        d = dignity_at(SUN, sign_idx, True)
        assert d.triplicity_group == "Air"
        assert d.triplicity_day_lord   == SATURN
        assert d.triplicity_night_lord == MERCURY
        assert d.triplicity_part_lord  == JUPITER


def test_water_triplicity_lords():
    for sign_idx in [3, 7, 11]:  # Cancer, Scorpio, Pis
        d = dignity_at(SUN, sign_idx, True)
        assert d.triplicity_group == "Water"
        assert d.triplicity_day_lord   == VENUS
        assert d.triplicity_night_lord == MARS
        assert d.triplicity_part_lord  == MOON


def test_sign_to_group_all_signs():
    for sign_idx, expected in enumerate(SIGN_GROUPS):
        d = dignity_at(SUN, sign_idx, True)
        assert d.triplicity_group == expected, (
            f"sign={sign_idx}: expected {expected}, got {d.triplicity_group}"
        )


# ── Core tests — triplicity_role ──────────────────────────────────────────────

def test_role_day_lord_in_day_chart():
    # Sun is day lord of Fire
    d = calc_dignities(SUN, 0.0, True)  # Sun at 0°Aries, day chart
    assert d.triplicity_role == "day"


def test_role_night_lord_in_night_chart():
    # Jupiter is night lord of Fire
    d = calc_dignities(JUPITER, 0.0, False)  # Jupiter at 0°Aries, night chart
    assert d.triplicity_role == "night"


def test_role_participating_lord():
    # Saturn is participating lord of Fire (regardless of daytime)
    d_day   = calc_dignities(SATURN, 0.0, True)
    d_night = calc_dignities(SATURN, 0.0, False)
    assert d_day.triplicity_role   == "participating"
    assert d_night.triplicity_role == "participating"


def test_role_none():
    # Moon has no role in Aries (Fire) triplicity
    d = calc_dignities(MOON, 0.0, True)
    assert d.triplicity_role == "none"


def test_role_independent_of_daytime():
    """Lords themselves don't change with day/night — only the active one differs."""
    for sign in range(12):
        for pid in range(7):
            dd = dignity_at(pid, sign, True)
            dn = dignity_at(pid, sign, False)
            assert dd.triplicity_day_lord   == dn.triplicity_day_lord
            assert dd.triplicity_night_lord == dn.triplicity_night_lord
            assert dd.triplicity_part_lord  == dn.triplicity_part_lord
            assert dd.triplicity_group      == dn.triplicity_group
            assert dd.triplicity_role       == dn.triplicity_role


def test_triplicity_bool_matches_active_lord():
    """triplicity=True iff planet == active lord (day lord in day, night lord in night)."""
    for sign in range(12):
        for pid in range(7):
            dd = dignity_at(pid, sign, True)
            dn = dignity_at(pid, sign, False)
            assert dd.triplicity == (pid == dd.triplicity_day_lord), (
                f"pid={pid} sign={sign} day: triplicity={dd.triplicity} but "
                f"day_lord={dd.triplicity_day_lord}"
            )
            assert dn.triplicity == (pid == dn.triplicity_night_lord), (
                f"pid={pid} sign={sign} night: triplicity={dn.triplicity} but "
                f"night_lord={dn.triplicity_night_lord}"
            )


def test_triplicity_false_for_participating_lord():
    """Participating lord never gets triplicity=True (only day or night lord does)."""
    # Saturn is participating lord of Fire
    dd = calc_dignities(SATURN, 0.0, True)   # day chart  — day lord is Sun
    dn = calc_dignities(SATURN, 0.0, False)  # night chart — night lord is Jupiter
    assert not dd.triplicity
    assert not dn.triplicity


# ── Core tests — existing fields unchanged ─────────────────────────────────────

def test_existing_fields_still_present():
    d = calc_dignities(SUN, 120.0, True)  # Sun at 0°Leo = domicile
    assert d.domicile
    assert d.score >= 5
    assert hasattr(d, "sign_idx")
    assert hasattr(d, "peregrine")
    assert hasattr(d, "detriment")
    assert hasattr(d, "fall")


# ── API tests ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def api_resp():
    resp = client.post("/chart/natal", json=NATAL_REQ)
    assert resp.status_code == 200, f"API error: {resp.text}"
    return resp.json()


@pytest.fixture(scope="module")
def api_dignities(api_resp):
    return api_resp["dignities"]


def test_api_seven_dignities(api_dignities):
    assert len(api_dignities) == 7


def test_api_triplicity_fields_present(api_dignities):
    required = {
        "triplicity_group",
        "triplicity_day_lord", "triplicity_night_lord", "triplicity_part_lord",
        "triplicity_day_lord_name", "triplicity_night_lord_name", "triplicity_part_lord_name",
        "triplicity_role",
    }
    for d in api_dignities:
        for f in required:
            assert f in d, f"Missing field '{f}' in {d['planet_name']}"


def test_api_triplicity_group_valid(api_dignities):
    valid = {"Fire", "Earth", "Air", "Water"}
    for d in api_dignities:
        assert d["triplicity_group"] in valid, (
            f"{d['planet_name']}: invalid group '{d['triplicity_group']}'"
        )


def test_api_triplicity_role_valid(api_dignities):
    valid = {"day", "night", "participating", "none"}
    for d in api_dignities:
        assert d["triplicity_role"] in valid, (
            f"{d['planet_name']}: invalid role '{d['triplicity_role']}'"
        )


def test_api_lord_ids_valid(api_dignities):
    for d in api_dignities:
        assert 0 <= d["triplicity_day_lord"] <= 6
        assert 0 <= d["triplicity_night_lord"] <= 6
        assert 0 <= d["triplicity_part_lord"] <= 6


def test_api_lord_names_correct(api_dignities):
    names = {0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
             4: "Mars", 5: "Jupiter", 6: "Saturn"}
    for d in api_dignities:
        assert d["triplicity_day_lord_name"]   == names[d["triplicity_day_lord"]]
        assert d["triplicity_night_lord_name"] == names[d["triplicity_night_lord"]]
        assert d["triplicity_part_lord_name"]  == names[d["triplicity_part_lord"]]


def test_api_triplicity_bool_matches_active_lord(api_resp, api_dignities):
    day_chart = api_resp["day_chart"]
    for d in api_dignities:
        if day_chart:
            expected = (d["planet_id"] == d["triplicity_day_lord"])
        else:
            expected = (d["planet_id"] == d["triplicity_night_lord"])
        assert d["triplicity"] == expected, (
            f"{d['planet_name']}: triplicity={d['triplicity']} but "
            f"expected={expected} (day_chart={day_chart})"
        )


def test_api_existing_fields_still_present(api_dignities):
    for d in api_dignities:
        for f in ["domicile", "exaltation", "triplicity", "term", "face",
                  "peregrine", "detriment", "fall", "score", "sign_idx"]:
            assert f in d, f"Existing field '{f}' missing from {d['planet_name']}"


def test_api_rome_1990_sun_group():
    """Rome 1990-06-15: Sun is at ~24°Gemini → Air triplicity.
    Air day lord = Saturn, so Sun triplicity=False in a day chart."""
    resp = client.post("/chart/natal", json=NATAL_REQ).json()
    day_chart = resp["day_chart"]
    sun_d = next(d for d in resp["dignities"] if d["planet_name"] == "Sun")

    assert sun_d["triplicity_group"] == "Air"
    assert sun_d["triplicity_day_lord_name"] == "Saturn"
    assert sun_d["triplicity_night_lord_name"] == "Mercury"
    assert sun_d["triplicity_part_lord_name"] == "Jupiter"

    if day_chart:
        # Day chart: active lord = Saturn; Sun's role = "none" (Sun not in Air lords)
        assert not sun_d["triplicity"]
        assert sun_d["triplicity_role"] == "none"


def test_api_rome_1990_saturn_group():
    """Saturn in Air (Gemini/Libra/Aquarius) day chart → triplicity=True."""
    resp = client.post("/chart/natal", json=NATAL_REQ).json()
    day_chart = resp["day_chart"]
    sat_d = next(d for d in resp["dignities"] if d["planet_name"] == "Saturn")

    if sat_d["triplicity_group"] == "Air" and day_chart:
        assert sat_d["triplicity"]
        assert sat_d["triplicity_role"] == "day"
