"""
Essential Dignities for Horary Significators — Epic 9.3.

Evaluates the five essential dignities and three essential debilities for
the querent significator (H1 lord), the quesited significator (H-N lord),
and the Moon (co-significator of the querent).

Essential Dignities (+):
  1. Domicile      +5  — planet in one of its own signs
  2. Exaltation    +4  — planet in its exaltation sign
  3. Triplicity    +3  — planet is sect triplicity lord of its element
  4. Term (Bound)  +2  — planet within its Egyptian term
  5. Face (Decan)  +1  — planet within its Chaldean face

Essential Debilities (−):
  1. Detriment     −5  — planet in the sign(s) opposite its domicile
  2. Fall          −4  — planet in the sign opposite its exaltation
  3. Peregrine flag    — planet has no positive essential dignity whatsoever

Sect:
  Day chart: Sun in houses 7–12 (above horizon).
  Night chart: Sun in houses 1–6 (below horizon).
  Triplicity lords differ by sect.

References:
  William Lilly, Christian Astrology, Book 1.
  Al-Biruni / Ptolemy triplicity lords as used by Lilly.
  Egyptian terms (Ptolemy, Tetrabiblos I.20).
  Chaldean faces (Decans).

Planet IDs: 0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
"""

from __future__ import annotations
from dataclasses import dataclass

# ─── Constants ────────────────────────────────────────────────────────────────

_PLANET_NAMES: dict[int, str] = {
    0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
    4: "Mars", 5: "Jupiter", 6: "Saturn",
}

_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

# Traditional sign lords (sign_idx → planet_id)
_SIGN_LORDS: dict[int, int] = {
    0: 4, 1: 3, 2: 2, 3: 1, 4: 0, 5: 2,
    6: 3, 7: 4, 8: 5, 9: 6, 10: 6, 11: 5,
}

# Classical exaltation (planet_id → sign_idx)
_EXALTATION: dict[int, int] = {
    0: 0,   # Sun     → Aries
    1: 1,   # Moon    → Taurus
    2: 5,   # Mercury → Virgo
    3: 11,  # Venus   → Pisces
    4: 9,   # Mars    → Capricorn
    5: 3,   # Jupiter → Cancer
    6: 6,   # Saturn  → Libra
}

# Classical fall = opposite exaltation (planet_id → sign_idx)
_FALL: dict[int, int] = {
    0: 6,   # Sun     → Libra
    1: 7,   # Moon    → Scorpio
    2: 11,  # Mercury → Pisces
    3: 5,   # Venus   → Virgo
    4: 3,   # Mars    → Cancer
    5: 9,   # Jupiter → Capricorn
    6: 0,   # Saturn  → Aries
}

# Detriment = opposite domicile (planet_id → frozenset of sign indices)
_DETRIMENT: dict[int, tuple[int, ...]] = {
    0: (10,),      # Sun:     Aquarius
    1: (9,),       # Moon:    Capricorn
    2: (8, 11),    # Mercury: Sagittarius + Pisces
    3: (0, 7),     # Venus:   Aries + Scorpio
    4: (1, 6),     # Mars:    Taurus + Libra
    5: (2, 5),     # Jupiter: Gemini + Virgo
    6: (3, 4),     # Saturn:  Cancer + Leo
}

# Triplicity lords: (fire_signs, air_signs, earth_signs, water_signs)
# Each entry: (sign_indices_tuple, day_lord, night_lord)
_TRIPLICITIES: list[tuple[tuple[int, ...], int, int]] = [
    ((0, 4, 8),   0, 5),   # Fire:  day=Sun(0),    night=Jupiter(5)
    ((1, 5, 9),   3, 1),   # Earth: day=Venus(3),  night=Moon(1)
    ((2, 6, 10),  6, 2),   # Air:   day=Saturn(6), night=Mercury(2)
    ((3, 7, 11),  3, 4),   # Water: day=Venus(3),  night=Mars(4)
]

# Egyptian terms: list of 12 signs, each a list of (planet_id, upper_bound_exclusive)
# The term applies when: sign_lon < upper_bound.
_EGYPTIAN_TERMS: list[list[tuple[int, float]]] = [
    [(5, 6), (3, 12), (2, 20), (4, 25), (6, 30)],    # 0  Aries
    [(3, 8), (2, 15), (5, 22), (6, 26), (4, 30)],    # 1  Taurus
    [(2, 7), (5, 13), (3, 17), (4, 24), (6, 30)],    # 2  Gemini
    [(4, 7), (5, 13), (2, 19), (3, 26), (6, 30)],    # 3  Cancer
    [(5, 6), (3, 11), (6, 18), (2, 24), (4, 30)],    # 4  Leo
    [(2, 7), (3, 13), (5, 18), (6, 21), (4, 30)],    # 5  Virgo
    [(6, 6), (2, 14), (5, 21), (3, 28), (4, 30)],    # 6  Libra
    [(4, 7), (3, 11), (2, 19), (5, 24), (6, 30)],    # 7  Scorpio
    [(5, 12), (3, 17), (2, 21), (6, 26), (4, 30)],   # 8  Sagittarius
    [(2, 7), (5, 14), (3, 22), (6, 26), (4, 30)],    # 9  Capricorn
    [(2, 7), (3, 13), (5, 20), (4, 25), (6, 30)],    # 10 Aquarius
    [(3, 12), (5, 16), (2, 19), (4, 28), (6, 30)],   # 11 Pisces
]

# Chaldean faces (decans): list of 12 signs, each [pid_0-10, pid_10-20, pid_20-30]
_FACES: list[list[int]] = [
    [4, 0, 3],   # 0  Aries:        Mars, Sun, Venus
    [2, 1, 6],   # 1  Taurus:       Mercury, Moon, Saturn
    [5, 4, 0],   # 2  Gemini:       Jupiter, Mars, Sun
    [3, 2, 1],   # 3  Cancer:       Venus, Mercury, Moon
    [6, 5, 4],   # 4  Leo:          Saturn, Jupiter, Mars
    [0, 3, 2],   # 5  Virgo:        Sun, Venus, Mercury
    [1, 6, 5],   # 6  Libra:        Moon, Saturn, Jupiter
    [4, 0, 3],   # 7  Scorpio:      Mars, Sun, Venus
    [2, 1, 6],   # 8  Sagittarius:  Mercury, Moon, Saturn
    [5, 4, 0],   # 9  Capricorn:    Jupiter, Mars, Sun
    [3, 2, 1],   # 10 Aquarius:     Venus, Mercury, Moon
    [6, 5, 4],   # 11 Pisces:       Saturn, Jupiter, Mars
]


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class DignityDetail:
    domicile:    bool   # in own sign                  (+5)
    exaltation:  bool   # in exaltation sign            (+4)
    triplicity:  bool   # sect triplicity lord          (+3)
    term:        bool   # in own Egyptian term          (+2)
    face:        bool   # in own Chaldean face/decan    (+1)
    detriment:   bool   # in opposite domicile          (−5)
    fall:        bool   # in opposite exaltation        (−4)
    peregrine:   bool   # no positive dignity at all
    score:       int    # net dignity score
    strength:    str    # "Dignified" | "Peregrine" | "Debilitated"


@dataclass
class SignificatorDignity:
    planet_id:   int
    planet_name: str
    lon:         float
    sign:        str
    sign_lon:    float
    dignity:     DignityDetail


@dataclass
class HoraryDignityResult:
    day_chart:             bool
    querent_house:         int
    quesited_house:        int
    querent_significator:  SignificatorDignity
    quesited_significator: SignificatorDignity
    moon_dignity:          DignityDetail   # Moon as co-significator


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _find_house(lon: float, cusps: list[float]) -> int:
    for h in range(12):
        c1 = cusps[h]
        c2 = cusps[(h + 1) % 12]
        if c2 > c1:
            if c1 <= lon < c2:
                return h + 1
        else:
            if lon >= c1 or lon < c2:
                return h + 1
    return 1


def _house_lord(house_num: int, cusps: list[float]) -> int:
    cusp_lon = cusps[house_num - 1]
    sign_idx = int(cusp_lon / 30) % 12
    return _SIGN_LORDS[sign_idx]


def _is_day_chart(sun_lon: float, cusps: list[float]) -> bool:
    """Day chart = Sun in houses 7–12 (above the horizon)."""
    h = _find_house(sun_lon, cusps)
    return h >= 7


def calc_dignity(pid: int, lon: float, day_chart: bool) -> DignityDetail:
    """
    Compute essential dignity/debility for planet `pid` at longitude `lon`.
    `day_chart` controls which triplicity lord applies.
    """
    sign_idx = int(lon / 30) % 12
    sign_lon = lon % 30.0

    # ── Dignities ────────────────────────────────────────────────────────────

    domicile   = (_SIGN_LORDS[sign_idx] == pid)
    exaltation = (_EXALTATION.get(pid) == sign_idx)

    triplicity = False
    for signs, day_lord, night_lord in _TRIPLICITIES:
        if sign_idx in signs:
            triplicity = (pid == (day_lord if day_chart else night_lord))
            break

    term = False
    for term_pid, upper in _EGYPTIAN_TERMS[sign_idx]:
        if sign_lon < upper:
            term = (pid == term_pid)
            break

    face_idx = int(sign_lon / 10)   # 0, 1, or 2
    face = (_FACES[sign_idx][face_idx] == pid)

    # ── Debilities ───────────────────────────────────────────────────────────

    detriment = (sign_idx in _DETRIMENT.get(pid, ()))
    fall      = (_FALL.get(pid) == sign_idx)

    # ── Score & summary ──────────────────────────────────────────────────────

    pos_score = (
        (5 if domicile   else 0) +
        (4 if exaltation else 0) +
        (3 if triplicity else 0) +
        (2 if term       else 0) +
        (1 if face       else 0)
    )
    neg_score = (-5 if detriment else 0) + (-4 if fall else 0)
    score     = pos_score + neg_score
    peregrine = (pos_score == 0)

    if score > 0:
        strength = "Dignified"
    elif score < 0:
        strength = "Debilitated"
    else:
        strength = "Peregrine"

    return DignityDetail(
        domicile=domicile,
        exaltation=exaltation,
        triplicity=triplicity,
        term=term,
        face=face,
        detriment=detriment,
        fall=fall,
        peregrine=peregrine,
        score=score,
        strength=strength,
    )


# ─── Core calculation ──────────────────────────────────────────────────────────

def calc_horary_dignities(
    planet_lons:    dict[int, float],
    cusps:          list[float],
    querent_house:  int = 1,
    quesited_house: int = 7,
) -> HoraryDignityResult:
    """
    Compute essential dignities for querent, quesited, and Moon.

    planet_lons    : {planet_id: ecliptic_longitude} for 7 classical planets
    cusps          : 12 house cusp longitudes
    querent_house  : house number of the querent (default 1)
    quesited_house : house number of the quesited
    """
    day_chart = _is_day_chart(planet_lons[0], cusps)

    q_id  = _house_lord(querent_house,  cusps)
    s_id  = _house_lord(quesited_house, cusps)

    def _sig_dignity(pid: int) -> SignificatorDignity:
        lon      = planet_lons[pid]
        sign_idx = int(lon / 30) % 12
        return SignificatorDignity(
            planet_id=pid,
            planet_name=_PLANET_NAMES[pid],
            lon=round(lon, 4),
            sign=_SIGNS[sign_idx],
            sign_lon=round(lon % 30.0, 4),
            dignity=calc_dignity(pid, lon, day_chart),
        )

    moon_lon = planet_lons[1]
    moon_dignity = calc_dignity(1, moon_lon, day_chart)

    return HoraryDignityResult(
        day_chart=day_chart,
        querent_house=querent_house,
        quesited_house=quesited_house,
        querent_significator=_sig_dignity(q_id),
        quesited_significator=_sig_dignity(s_id),
        moon_dignity=moon_dignity,
    )
