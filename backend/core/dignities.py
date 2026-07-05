"""
Essential Dignities — ported from Morinus almutens.py / options.py
Classical medieval tradition: Dorothean triplicities, Egyptian terms, Chaldean decans.

Planet IDs match pyswisseph constants:
  0=Sun  1=Moon  2=Mercury  3=Venus  4=Mars  5=Jupiter  6=Saturn
"""

from dataclasses import dataclass

# ─── Planet constants ─────────────────────────────────────────────────────
SUN, MOON, MERCURY, VENUS, MARS, JUPITER, SATURN = 0, 1, 2, 3, 4, 5, 6

PLANET_NAMES = {
    SUN: "Sun", MOON: "Moon", MERCURY: "Mercury", VENUS: "Venus",
    MARS: "Mars", JUPITER: "Jupiter", SATURN: "Saturn",
}

SIGN_DEG = 30.0

# ─── Dignity tables (ported from Morinus options.py / almutens.py) ────────

# Domicile lord per sign (index 0=Aries … 11=Pisces)
DOMICILE = [MARS, VENUS, MERCURY, MOON, SUN, MERCURY,
            VENUS, MARS, JUPITER, SATURN, SATURN, JUPITER]

# Exalted planet per sign (-1 = no exaltation)
EXALTATION = [SUN, MOON, -1, JUPITER, -1, MERCURY,
              SATURN, -1, -1, MARS, -1, VENUS]

# Which triplicity group each sign belongs to (0=Fire,1=Air,2=Water,3=Earth)
_TRIPLICITY_GROUP = [0, 3, 1, 2, 0, 3, 1, 2, 0, 3, 1, 2]

# Dorothean triplicity rulers [group][day_ruler, night_ruler, participating]
_TRIPLICITY_RULERS = [
    [SUN,    JUPITER, SATURN],   # Fire  (Aries, Leo, Sagittarius)
    [SATURN, MERCURY, JUPITER],  # Air   (Gemini, Libra, Aquarius)
    [VENUS,  MARS,    MOON],     # Water (Cancer, Scorpio, Pisces)
    [VENUS,  MOON,    MARS],     # Earth (Taurus, Virgo, Capricorn)
]

_TRIPLICITY_NAMES = ["Fire", "Air", "Water", "Earth"]   # index matches group

# Egyptian Terms per sign: [[planet, degrees_span], ...]
_TERMS = [
    [[JUPITER,6],[VENUS,6],[MERCURY,8],[MARS,5],[SATURN,5]],   # Aries
    [[VENUS,8],[MERCURY,6],[JUPITER,8],[SATURN,5],[MARS,3]],   # Taurus
    [[MERCURY,6],[JUPITER,6],[VENUS,5],[MARS,7],[SATURN,6]],   # Gemini
    [[MARS,7],[VENUS,6],[MERCURY,6],[JUPITER,7],[SATURN,4]],   # Cancer
    [[JUPITER,6],[VENUS,5],[SATURN,7],[MERCURY,6],[MARS,6]],   # Leo
    [[MERCURY,7],[VENUS,10],[JUPITER,4],[MARS,7],[SATURN,2]],  # Virgo
    [[SATURN,6],[MERCURY,8],[JUPITER,7],[VENUS,7],[MARS,2]],   # Libra
    [[MARS,7],[VENUS,4],[MERCURY,8],[JUPITER,5],[SATURN,6]],   # Scorpio
    [[JUPITER,12],[VENUS,5],[MERCURY,4],[SATURN,5],[MARS,4]],  # Sagittarius
    [[MERCURY,7],[JUPITER,7],[VENUS,8],[SATURN,4],[MARS,4]],   # Capricorn
    [[MERCURY,7],[VENUS,6],[JUPITER,7],[MARS,5],[SATURN,5]],   # Aquarius
    [[VENUS,12],[JUPITER,4],[MERCURY,3],[MARS,9],[SATURN,2]],  # Pisces
]

# Chaldean Decans per sign: [1st_decan, 2nd_decan, 3rd_decan] (10° each)
_DECANS = [
    [MARS,    SUN,     VENUS],    # Aries
    [MERCURY, MOON,    SATURN],   # Taurus
    [JUPITER, MARS,    SUN],      # Gemini
    [VENUS,   MERCURY, MOON],     # Cancer
    [SATURN,  JUPITER, MARS],     # Leo
    [SUN,     VENUS,   MERCURY],  # Virgo
    [MOON,    SATURN,  JUPITER],  # Libra
    [MARS,    SUN,     VENUS],    # Scorpio
    [MERCURY, MOON,    SATURN],   # Sagittarius
    [JUPITER, MARS,    SUN],      # Capricorn
    [VENUS,   MERCURY, MOON],     # Aquarius
    [SATURN,  JUPITER, MARS],     # Pisces
]

# Default dignity scores [domicile, exaltation, triplicity, term, face]
DIGNITY_SCORES = [5, 4, 3, 2, 1]

# Debility tables (derived: opposite sign of domicile/exaltation)
DETRIMENT = [DOMICILE[(s + 6) % 12] for s in range(12)]
FALL      = [EXALTATION[(s + 6) % 12] for s in range(12)]  # -1 where no fall


# ─── Result ───────────────────────────────────────────────────────────────

@dataclass
class DignityResult:
    planet_id: int
    planet_name: str
    sign_idx: int       # 0=Aries … 11=Pisces
    domicile: bool
    exaltation: bool
    triplicity: bool    # True = active (day or night) Dorothean ruler of the triplicity
    term: bool
    face: bool
    peregrine: bool     # no essential dignity at all
    detriment: bool
    fall: bool
    score: int          # sum of positive scores minus debility scores

    # Triplicity lord detail (Epic 6.3)
    triplicity_group:          str   # "Fire" | "Earth" | "Air" | "Water"
    triplicity_day_lord:       int   # planet ID of the day triplicity lord
    triplicity_night_lord:     int   # planet ID of the night triplicity lord
    triplicity_part_lord:      int   # planet ID of the participating lord
    triplicity_day_lord_name:  str
    triplicity_night_lord_name: str
    triplicity_part_lord_name: str
    triplicity_role: str  # role of *this* planet: "day"|"night"|"participating"|"none"


# ─── Core calculation ─────────────────────────────────────────────────────

def calc_dignities(planet_id: int, lon: float, daytime: bool) -> DignityResult:
    """
    Essential dignities for planet_id (0-6) at ecliptic longitude lon.
    daytime: True when Sun is above the horizon (day chart).
    """
    sign = int(lon / SIGN_DEG) % 12
    pos  = lon % SIGN_DEG

    # Domicile
    is_dom  = DOMICILE[sign] == planet_id

    # Exaltation
    is_exal = EXALTATION[sign] not in (-1, None) and EXALTATION[sign] == planet_id

    # Triplicity — day or night ruler (Dorothean)
    group         = _TRIPLICITY_GROUP[sign]
    trip_day      = _TRIPLICITY_RULERS[group][0]
    trip_night    = _TRIPLICITY_RULERS[group][1]
    trip_part     = _TRIPLICITY_RULERS[group][2]
    tr_ruler      = trip_day if daytime else trip_night
    is_trip       = tr_ruler == planet_id

    # Role this planet plays in the sign's triplicity
    if planet_id == trip_day:
        trip_role = "day"
    elif planet_id == trip_night:
        trip_role = "night"
    elif planet_id == trip_part:
        trip_role = "participating"
    else:
        trip_role = "none"

    # Egyptian Term
    cumul, term_planet = 0.0, -1
    for p, span in _TERMS[sign]:
        cumul += span
        if cumul > pos:
            term_planet = p
            break
    is_term = term_planet == planet_id

    # Chaldean Face / Decan (10° each)
    decan_idx = int(pos / 10)
    is_face   = _DECANS[sign][decan_idx] == planet_id

    # Debilities
    is_det  = DETRIMENT[sign] == planet_id
    fall_pl = FALL[sign]
    is_fall = fall_pl not in (-1, None) and fall_pl == planet_id

    # Peregrine = zero essential dignities
    is_pereg = not (is_dom or is_exal or is_trip or is_term or is_face)

    score = (
        (DIGNITY_SCORES[0] if is_dom  else 0)
      + (DIGNITY_SCORES[1] if is_exal else 0)
      + (DIGNITY_SCORES[2] if is_trip else 0)
      + (DIGNITY_SCORES[3] if is_term else 0)
      + (DIGNITY_SCORES[4] if is_face else 0)
      - (DIGNITY_SCORES[0] if is_det  else 0)
      - (DIGNITY_SCORES[1] if is_fall else 0)
    )

    return DignityResult(
        planet_id=planet_id,
        planet_name=PLANET_NAMES[planet_id],
        sign_idx=sign,
        domicile=is_dom,
        exaltation=is_exal,
        triplicity=is_trip,
        term=is_term,
        face=is_face,
        peregrine=is_pereg,
        detriment=is_det,
        fall=is_fall,
        score=score,
        triplicity_group=_TRIPLICITY_NAMES[group],
        triplicity_day_lord=trip_day,
        triplicity_night_lord=trip_night,
        triplicity_part_lord=trip_part,
        triplicity_day_lord_name=PLANET_NAMES[trip_day],
        triplicity_night_lord_name=PLANET_NAMES[trip_night],
        triplicity_part_lord_name=PLANET_NAMES[trip_part],
        triplicity_role=trip_role,
    )


def is_day_chart(sun_lon: float, asc: float) -> bool:
    """
    True when Sun is above the horizon (houses 7–12 arc).

    Houses 7-12 span from DSC = (ASC+180)° counterclockwise back to ASC.
    A planet is in that arc when (planet_lon - ASC) % 360 >= 180.

    Example: ASC=0° → MC=270°, IC=90°.
      Sun@270° (at MC, overhead) → (270-0)%360=270 ≥ 180 → day chart ✓
      Sun@90°  (at IC, underground) → (90-0)%360=90  < 180 → night chart ✓
    """
    return (sun_lon - asc) % 360 >= 180
