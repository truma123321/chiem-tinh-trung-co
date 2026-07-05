"""
Traditional Aspects — medieval / Hellenistic tradition.

Five Ptolemaic aspects:
  Conjunction (0°), Sextile (60°), Square (90°), Trine (120°), Opposition (180°)

Two modes:
  1. Orb-based (medieval): comparison by ecliptic longitude ± combined orb
  2. Sign-based (Hellenistic): planets in the same or configured signs,
     regardless of degree — called "whole-sign aspects"

Application / Separation:
  Planet A applies to planet B when the faster planet is closing the orb.
  Planet A separates from planet B when the faster planet is opening the orb.

Collection of Light:
  Slower planet C collects light from faster planets A and B when both A and B
  are applying to C (within orb) and A-B are not perfecting their own aspect.

Translation of Light:
  Planet C translates light from A to B when C has recently separated from A
  (still within orb) and is currently applying to B.

Reception:
  Planet A is in reception with planet B when A is in one of B's dignities
  (domicile / exaltation) and B is in one of A's dignities.

Planet IDs: 0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from core.dignities import DOMICILE, EXALTATION, PLANET_NAMES

# ─── Aspect constants ──────────────────────────────────────────────────────

CONJUNCTION = 0
SEXTILE     = 1
SQUARE      = 2
TRINE       = 3
OPPOSITION  = 4

ASPECT_ANGLES = {
    CONJUNCTION: 0.0,
    SEXTILE:    60.0,
    SQUARE:     90.0,
    TRINE:     120.0,
    OPPOSITION:180.0,
}

ASPECT_NAMES = {
    CONJUNCTION: "Conjunction",
    SEXTILE:     "Sextile",
    SQUARE:      "Square",
    TRINE:       "Trine",
    OPPOSITION:  "Opposition",
}

# Sign separation required for each aspect (whole-sign mode)
ASPECT_SIGN_DIFF = {
    CONJUNCTION: 0,
    SEXTILE:     2,
    SQUARE:      3,
    TRINE:       4,
    OPPOSITION:  6,
}

# ─── Default orbs (Bonatti / Zoller, per planet) ──────────────────────────
# Each planet contributes half its orb to any aspect it participates in.
# Combined orb = (orb_A + orb_B) / 2.  Some traditions use full orbs.

DEFAULT_ORB = {
    0: 15.0,   # Sun
    1: 12.0,   # Moon
    2:  7.0,   # Mercury
    3:  7.0,   # Venus
    4:  8.0,   # Mars
    5:  9.0,   # Jupiter
    6:  9.0,   # Saturn
}


def _combined_orb(pid_a: int, pid_b: int) -> float:
    """Combined orb for an aspect between planets A and B."""
    return (DEFAULT_ORB.get(pid_a, 7.0) + DEFAULT_ORB.get(pid_b, 7.0)) / 2.0


def _arc(lon_a: float, lon_b: float) -> float:
    """Shortest arc between two longitudes (0–180°)."""
    d = abs(lon_a - lon_b) % 360
    return d if d <= 180 else 360 - d


def _sign(lon: float) -> int:
    """Sign index 0=Aries … 11=Pisces."""
    return int(lon / 30) % 12


def _sign_diff(lon_a: float, lon_b: float) -> int:
    """Shortest sign separation (0–6)."""
    s = abs(_sign(lon_a) - _sign(lon_b))
    return s if s <= 6 else 12 - s


# ─── Result types ──────────────────────────────────────────────────────────

@dataclass
class Aspect:
    planet_a: int           # pyswisseph planet ID
    planet_b: int
    name_a: str
    name_b: str
    aspect_type: int        # CONJUNCTION .. OPPOSITION
    aspect_name: str
    orb: float              # actual orb in degrees (how far from exact)
    max_orb: float          # allowed orb
    applying: bool          # True = planets closing toward exact
    exact: bool             # within 1° (configurable)
    sinister: bool          # True = A casts aspect forward (sinister / dexter)
    whole_sign: bool        # True = aspects confirmed by whole-sign
    mutual_reception: bool  # mutual reception by domicile or exaltation


@dataclass
class CollectionOfLight:
    collector: int          # slower planet collecting light
    collector_name: str
    from_a: int             # faster planet A applying to collector
    from_b: int             # faster planet B applying to collector
    name_a: str
    name_b: str
    orb_a: float            # orb of A → collector
    orb_b: float            # orb of B → collector


@dataclass
class TranslationOfLight:
    translator: int         # planet doing the translating
    translator_name: str
    from_planet: int        # planet translator just separated from
    to_planet: int          # planet translator is applying to
    from_name: str
    to_name: str
    sep_orb: float          # orb of separation (still within range)
    app_orb: float          # orb of application


@dataclass
class AspectsResult:
    aspects: list[Aspect]
    collections: list[CollectionOfLight]
    translations: list[TranslationOfLight]


# ─── Core calculation ──────────────────────────────────────────────────────

def _is_applying(
    pid_a: int, pid_b: int,
    lon_a: float, lon_b: float,
    spd_a: float, spd_b: float,
    aspect_angle: float,
) -> bool:
    """
    True when the faster planet is closing toward the exact aspect degree.

    Strategy: compute the orb now vs. orb in 1 day (using speeds as proxy).
    If the orb decreases, they are applying.
    """
    orb_now = _arc(lon_a, lon_b) - aspect_angle
    # Approximate position in 1 day
    lon_a1 = (lon_a + spd_a) % 360
    lon_b1 = (lon_b + spd_b) % 360
    orb_next = _arc(lon_a1, lon_b1) - aspect_angle
    return abs(orb_next) < abs(orb_now)


def _mutual_reception(pid_a: int, lon_a: float, pid_b: int, lon_b: float) -> bool:
    """True when A is in B's domicile/exaltation AND B is in A's domicile/exaltation."""
    sign_a = _sign(lon_a)
    sign_b = _sign(lon_b)

    a_in_b_dom  = DOMICILE[sign_a] == pid_b
    a_in_b_exal = EXALTATION[sign_a] == pid_b

    b_in_a_dom  = DOMICILE[sign_b] == pid_a
    b_in_a_exal = EXALTATION[sign_b] == pid_a

    return (a_in_b_dom or a_in_b_exal) and (b_in_a_dom or b_in_a_exal)


def calc_aspects(
    planet_lons: dict,       # {pid: lon}
    planet_speeds: dict,     # {pid: speed_deg_per_day}
    exact_threshold: float = 1.0,   # degrees — "exact" aspect boundary
) -> AspectsResult:
    """
    Compute all traditional aspects between the 7 classical planets.

    planet_lons:   {0..6: ecliptic longitude}
    planet_speeds: {0..6: speed in deg/day, negative = retrograde}
    """
    planets = sorted(planet_lons.keys())   # [0,1,2,3,4,5,6]
    aspects: list[Aspect] = []

    for i, pid_a in enumerate(planets):
        for pid_b in planets[i+1:]:
            lon_a = planet_lons[pid_a]
            lon_b = planet_lons[pid_b]
            spd_a = planet_speeds.get(pid_a, 0.0)
            spd_b = planet_speeds.get(pid_b, 0.0)
            arc   = _arc(lon_a, lon_b)
            sdiff = _sign_diff(lon_a, lon_b)

            for asp_type, angle in ASPECT_ANGLES.items():
                orb = abs(arc - angle)
                max_orb = _combined_orb(pid_a, pid_b)

                if orb > max_orb:
                    continue

                applying = _is_applying(pid_a, pid_b, lon_a, lon_b, spd_a, spd_b, angle)
                whole_sign = (sdiff == ASPECT_SIGN_DIFF[asp_type])
                exact = (orb <= exact_threshold)

                # Sinister aspect: A casts its ray forward (toward higher longitude)
                # In traditional astrology, sinister = in zodiac order from A to B
                d = (lon_b - lon_a) % 360
                sinister = (d <= 180)

                mr = _mutual_reception(pid_a, lon_a, pid_b, lon_b)

                aspects.append(Aspect(
                    planet_a=pid_a,
                    planet_b=pid_b,
                    name_a=PLANET_NAMES[pid_a],
                    name_b=PLANET_NAMES[pid_b],
                    aspect_type=asp_type,
                    aspect_name=ASPECT_NAMES[asp_type],
                    orb=round(orb, 4),
                    max_orb=round(max_orb, 2),
                    applying=applying,
                    exact=exact,
                    sinister=sinister,
                    whole_sign=whole_sign,
                    mutual_reception=mr,
                ))

    # ── Collection of Light ────────────────────────────────────────────────
    # Find planets (C) that have two other planets (A, B) applying to them.
    # C must be slower than both A and B.
    collections: list[CollectionOfLight] = []

    applying_to: dict[int, list[tuple[int, float]]] = {p: [] for p in planets}
    for asp in aspects:
        if asp.applying:
            # The faster planet applies to the slower
            spd_a = abs(planet_speeds.get(asp.planet_a, 0.0))
            spd_b = abs(planet_speeds.get(asp.planet_b, 0.0))
            if spd_a >= spd_b:
                applying_to[asp.planet_b].append((asp.planet_a, asp.orb))
            else:
                applying_to[asp.planet_a].append((asp.planet_b, asp.orb))

    for collector, applicants in applying_to.items():
        if len(applicants) < 2:
            continue
        # Check that the two applicants are not in applying aspect with each other
        for idx in range(len(applicants)):
            for jdx in range(idx + 1, len(applicants)):
                from_a, orb_a = applicants[idx]
                from_b, orb_b = applicants[jdx]
                # Check A-B are not themselves in an applying aspect
                ab_applying = any(
                    asp.applying
                    and {asp.planet_a, asp.planet_b} == {from_a, from_b}
                    for asp in aspects
                )
                if not ab_applying:
                    collections.append(CollectionOfLight(
                        collector=collector,
                        collector_name=PLANET_NAMES[collector],
                        from_a=from_a,
                        from_b=from_b,
                        name_a=PLANET_NAMES[from_a],
                        name_b=PLANET_NAMES[from_b],
                        orb_a=round(orb_a, 4),
                        orb_b=round(orb_b, 4),
                    ))

    # ── Translation of Light ───────────────────────────────────────────────
    # Planet C translates light from A to B when:
    #   1. C has recently separated from A (still within orb)
    #   2. C is applying to B
    # A and B are not in a direct applying aspect.
    translations: list[TranslationOfLight] = []

    separating: dict[int, list[tuple[int, float]]] = {p: [] for p in planets}
    for asp in aspects:
        if not asp.applying:
            spd_a = abs(planet_speeds.get(asp.planet_a, 0.0))
            spd_b = abs(planet_speeds.get(asp.planet_b, 0.0))
            if spd_a >= spd_b:
                separating[asp.planet_a].append((asp.planet_b, asp.orb))
            else:
                separating[asp.planet_b].append((asp.planet_a, asp.orb))

    for translator in planets:
        sep_list = separating.get(translator, [])
        app_list = applying_to.get(translator, [])
        # C must be faster than both the planet it separated from and the one it applies to
        for from_p, sep_orb in sep_list:
            for to_p, app_orb in app_list:
                if from_p == to_p:
                    continue
                # A and B not in applying aspect
                ab_applying = any(
                    asp.applying
                    and {asp.planet_a, asp.planet_b} == {from_p, to_p}
                    for asp in aspects
                )
                if not ab_applying:
                    translations.append(TranslationOfLight(
                        translator=translator,
                        translator_name=PLANET_NAMES[translator],
                        from_planet=from_p,
                        to_planet=to_p,
                        from_name=PLANET_NAMES[from_p],
                        to_name=PLANET_NAMES[to_p],
                        sep_orb=round(sep_orb, 4),
                        app_orb=round(app_orb, 4),
                    ))

    return AspectsResult(
        aspects=aspects,
        collections=collections,
        translations=translations,
    )
