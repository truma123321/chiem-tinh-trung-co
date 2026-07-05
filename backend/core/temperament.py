"""
Temperament (Complexion) — Galen / medieval tradition.

The four temperaments arise from the combination of two qualities:
  Hot+Wet  = Sanguine    (Jupiter / Air signs / Spring)
  Hot+Dry  = Choleric    (Mars / Fire signs / Summer)
  Cold+Dry = Melancholic (Saturn / Earth signs / Autumn)
  Cold+Wet = Phlegmatic  (Moon, Venus / Water signs / Winter)

Method (Bonatti / Lilly / Ptolemy Tetrabiblos I.10):
Six factors each contribute one temperament vote:
  1. Season of birth (from Sun's tropical longitude)
  2. Rising sign element
  3. Lord of the Ascendant (sign ruler)
  4. Moon's sign element
  5. Lord of the Moon's sign (sign ruler)
  6. Dominant/almuten planet

The temperament with the most votes is primary; second-most is secondary.
Hot/Cold and Wet/Dry totals determine the active qualities.

Planet IDs: 0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
"""

from __future__ import annotations
from dataclasses import dataclass

# ─── Planet names ──────────────────────────────────────────────────────────────

_PLANET_NAMES = {
    0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
    4: "Mars", 5: "Jupiter", 6: "Saturn",
}

# ─── Sign rulers (traditional, Chaldean) ──────────────────────────────────────

_SIGN_RULER = {
    0: 4,   # Aries → Mars
    1: 3,   # Taurus → Venus
    2: 2,   # Gemini → Mercury
    3: 1,   # Cancer → Moon
    4: 0,   # Leo → Sun
    5: 2,   # Virgo → Mercury
    6: 3,   # Libra → Venus
    7: 4,   # Scorpio → Mars
    8: 5,   # Sagittarius → Jupiter
    9: 6,   # Capricorn → Saturn
    10: 6,  # Aquarius → Saturn
    11: 5,  # Pisces → Jupiter
}

# ─── Sign element → temperament ───────────────────────────────────────────────

_SIGN_TEMPERAMENT = {
    0:  "Choleric",    # Aries (Fire)
    1:  "Melancholic", # Taurus (Earth)
    2:  "Sanguine",    # Gemini (Air)
    3:  "Phlegmatic",  # Cancer (Water)
    4:  "Choleric",    # Leo (Fire)
    5:  "Melancholic", # Virgo (Earth)
    6:  "Sanguine",    # Libra (Air)
    7:  "Phlegmatic",  # Scorpio (Water)
    8:  "Choleric",    # Sagittarius (Fire)
    9:  "Melancholic", # Capricorn (Earth)
    10: "Sanguine",    # Aquarius (Air)
    11: "Phlegmatic",  # Pisces (Water)
}

# ─── Planet → temperament ─────────────────────────────────────────────────────

_PLANET_TEMPERAMENT = {
    0: "Choleric",    # Sun (Hot+Dry)
    1: "Phlegmatic",  # Moon (Cold+Wet)
    2: "Melancholic", # Mercury (Cold+Dry)
    3: "Phlegmatic",  # Venus (Cold+Wet)
    4: "Choleric",    # Mars (Hot+Dry)
    5: "Sanguine",    # Jupiter (Hot+Wet)
    6: "Melancholic", # Saturn (Cold+Dry)
}

# ─── Temperament → primary qualities ──────────────────────────────────────────

TEMPERAMENT_QUALITIES = {
    "Sanguine":    ("Hot", "Wet"),
    "Choleric":    ("Hot", "Dry"),
    "Melancholic": ("Cold", "Dry"),
    "Phlegmatic":  ("Cold", "Wet"),
}

_ALL_TEMPERAMENTS = ["Sanguine", "Choleric", "Melancholic", "Phlegmatic"]


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class TemperamentContribution:
    factor: str        # e.g. "Season", "Rising Sign", "Lord of ASC (Mars)"
    temperament: str   # "Sanguine" | "Choleric" | "Melancholic" | "Phlegmatic"
    quality_1: str     # "Hot" | "Cold"
    quality_2: str     # "Wet" | "Dry"


@dataclass
class TemperamentResult:
    primary: str           # dominant temperament label
    secondary: str         # runner-up
    primary_quality_1: str # "Hot" | "Cold"
    primary_quality_2: str # "Wet" | "Dry"
    hot_score: int
    cold_score: int
    wet_score: int
    dry_score: int
    scores: dict           # {temperament: vote_count}
    contributions: list    # list[TemperamentContribution]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _season_temperament(sun_lon: float) -> str:
    """Temperament from season of birth (based on Sun's tropical longitude)."""
    q = int(sun_lon / 90) % 4
    return ["Sanguine", "Choleric", "Melancholic", "Phlegmatic"][q]
    # Spring 0–89° → Sanguine (Hot+Wet)
    # Summer 90–179° → Choleric (Hot+Dry)
    # Autumn 180–269° → Melancholic (Cold+Dry)
    # Winter 270–359° → Phlegmatic (Cold+Wet)


# ─── Core calculation ─────────────────────────────────────────────────────────

def calc_temperament(
    planet_lons: dict,   # {0..6: ecliptic longitude}
    asc_lon: float,      # Ascendant longitude
    almuten_id: int,     # dominant planet ID (0..6)
) -> TemperamentResult:
    """
    Calculate the native's temperament from six classical factors.
    Returns primary + secondary temperament with supporting scores.
    """
    scores: dict[str, int] = {t: 0 for t in _ALL_TEMPERAMENTS}
    contributions: list[TemperamentContribution] = []

    def _vote(factor: str, temp: str) -> None:
        scores[temp] += 1
        q1, q2 = TEMPERAMENT_QUALITIES[temp]
        contributions.append(TemperamentContribution(
            factor=factor, temperament=temp, quality_1=q1, quality_2=q2,
        ))

    # 1. Season of birth (Sun's longitude → tropical season)
    season_temp = _season_temperament(planet_lons[0])
    _vote("Season", season_temp)

    # 2. Rising sign element
    asc_sign = int(asc_lon / 30) % 12
    _vote("Rising Sign", _SIGN_TEMPERAMENT[asc_sign])

    # 3. Lord of the Ascendant
    asc_lord = _SIGN_RULER[asc_sign]
    _vote(f"Lord of ASC ({_PLANET_NAMES[asc_lord]})", _PLANET_TEMPERAMENT[asc_lord])

    # 4. Moon's sign element
    moon_sign = int(planet_lons[1] / 30) % 12
    _vote("Moon's Sign", _SIGN_TEMPERAMENT[moon_sign])

    # 5. Lord of Moon's sign
    moon_lord = _SIGN_RULER[moon_sign]
    _vote(f"Lord of Moon ({_PLANET_NAMES[moon_lord]})", _PLANET_TEMPERAMENT[moon_lord])

    # 6. Dominant / almuten planet
    _vote(f"Almuten ({_PLANET_NAMES[almuten_id]})", _PLANET_TEMPERAMENT[almuten_id])

    # ── Determine primary and secondary ──────────────────────────────────────
    sorted_temps = sorted(_ALL_TEMPERAMENTS, key=lambda t: -scores[t])
    primary   = sorted_temps[0]
    secondary = sorted_temps[1]
    q1, q2 = TEMPERAMENT_QUALITIES[primary]

    # ── Quality totals ────────────────────────────────────────────────────────
    hot_score  = scores["Sanguine"]  + scores["Choleric"]
    cold_score = scores["Melancholic"] + scores["Phlegmatic"]
    wet_score  = scores["Sanguine"]  + scores["Phlegmatic"]
    dry_score  = scores["Choleric"]  + scores["Melancholic"]

    return TemperamentResult(
        primary=primary,
        secondary=secondary,
        primary_quality_1=q1,
        primary_quality_2=q2,
        hot_score=hot_score,
        cold_score=cold_score,
        wet_score=wet_score,
        dry_score=dry_score,
        scores=scores,
        contributions=contributions,
    )
