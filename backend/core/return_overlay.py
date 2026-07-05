"""
Return Chart Integration (Epic 3.3).

Computes the overlay between a return chart and the natal chart:

1. Natal planet placements in return chart houses.
   Each natal planet's ecliptic longitude is located in the return chart's
   house system (which house cusp range it occupies).

2. Return-to-natal cross-aspects.
   For every pair (return planet, natal planet) the 5 Ptolemaic aspects are
   checked using combined-orb logic identical to the natal aspect engine.
   Natal planets are treated as fixed (speed = 0); applying/separating is
   determined solely by the return planet's daily motion.
"""

from __future__ import annotations
from dataclasses import dataclass

from core.aspects import (
    ASPECT_ANGLES, ASPECT_NAMES, DEFAULT_ORB,
    _arc, _sign_diff, ASPECT_SIGN_DIFF,
)

# ── Planet name table ─────────────────────────────────────────────────────────

_NAMES = {
    0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
    4: "Mars", 5: "Jupiter", 6: "Saturn",
}


# ── House placement ───────────────────────────────────────────────────────────

def _planet_in_house(lon: float, cusps: list[float]) -> int:
    """
    Return 1-based house number (1–12) for `lon` given a list of 12 cusp longitudes.

    Uses the standard algorithm: a planet is in house N when it lies in the
    arc from cusp N to cusp N+1 (both measured forward in the zodiac).
    Handles wrapping across 0°/360°.
    """
    for h in range(12):
        start = cusps[h]
        end   = cusps[(h + 1) % 12]
        if end > start:                   # normal arc (no 360° crossing)
            if start <= lon < end:
                return h + 1
        else:                             # arc crosses 0°
            if lon >= start or lon < end:
                return h + 1
    return 1  # fallback (shouldn't happen with valid cusps)


# ── Applying check for cross-chart pair ───────────────────────────────────────

def _is_applying_cross(
    ret_lon: float, ret_speed: float,
    nat_lon: float,
    aspect_angle: float,
) -> bool:
    """
    True when the return planet (with its daily speed) is closing the orb
    toward the exact aspect with the static natal planet.

    The natal planet is treated as fixed (speed = 0).
    """
    orb_now  = _arc(ret_lon, nat_lon) - aspect_angle
    ret_lon1 = (ret_lon + ret_speed) % 360
    orb_next = _arc(ret_lon1, nat_lon) - aspect_angle
    return abs(orb_next) < abs(orb_now)


# ── Result dataclasses ────────────────────────────────────────────────────────

@dataclass
class NatalPlanetPlacement:
    planet_id:   int
    planet_name: str
    natal_lon:   float
    return_house: int   # 1-based


@dataclass
class ReturnNatalAspect:
    return_planet_id:   int
    return_planet_name: str
    natal_planet_id:    int
    natal_planet_name:  str
    aspect_type:        int
    aspect_name:        str
    orb:                float
    max_orb:            float
    applying:           bool
    exact:              bool


@dataclass
class ReturnNatalOverlayResult:
    natal_planets:  list  # list[PlanetPosition] — natal chart planet data
    placements:     list[NatalPlanetPlacement]
    cross_aspects:  list[ReturnNatalAspect]


# ── Main calculation ───────────────────────────────────────────────────────────

def calc_return_natal_overlay(
    return_planets,      # list[PlanetPosition] — return chart
    natal_planets,       # list[PlanetPosition] — natal chart (7 traditional)
    return_cusps: list[float],
    exact_threshold: float = 1.0,
) -> ReturnNatalOverlayResult:
    """
    Compute the overlay between a return chart and the natal chart.

    Parameters
    ----------
    return_planets : list of PlanetPosition
        Planets computed at the return moment (includes speed info).
    natal_planets : list of PlanetPosition
        Planets computed at the birth moment.
    return_cusps : list of 12 floats
        House cusp longitudes from the return chart.
    exact_threshold : float
        Orb (degrees) within which an aspect is considered exact.

    Returns
    -------
    ReturnNatalOverlayResult
    """
    # ── Natal placements in return houses ─────────────────────────────────────
    placements: list[NatalPlanetPlacement] = []
    for p in natal_planets:
        if p.id not in _NAMES:
            continue
        house = _planet_in_house(p.lon, return_cusps)
        placements.append(NatalPlanetPlacement(
            planet_id=p.id,
            planet_name=p.name,
            natal_lon=p.lon,
            return_house=house,
        ))

    # ── Cross-aspects: return planets × natal planets ─────────────────────────
    # Only the 7 traditional planets participate on both sides.
    trad_ids = set(_NAMES.keys())

    ret_map = {p.id: p for p in return_planets if p.id in trad_ids}
    nat_map = {p.id: p for p in natal_planets  if p.id in trad_ids}

    cross_aspects: list[ReturnNatalAspect] = []

    for ret_id, ret_p in ret_map.items():
        for nat_id, nat_p in nat_map.items():
            # Skip self-to-self (same planet in return vs natal)
            if ret_id == nat_id:
                continue

            arc   = _arc(ret_p.lon, nat_p.lon)
            max_o = (DEFAULT_ORB.get(ret_id, 7.0) + DEFAULT_ORB.get(nat_id, 7.0)) / 2.0

            for asp_type, angle in ASPECT_ANGLES.items():
                orb = abs(arc - angle)
                if orb > max_o:
                    continue

                applying = _is_applying_cross(
                    ret_p.lon, ret_p.speed, nat_p.lon, angle
                )
                exact = (orb <= exact_threshold)

                cross_aspects.append(ReturnNatalAspect(
                    return_planet_id=ret_id,
                    return_planet_name=ret_p.name,
                    natal_planet_id=nat_id,
                    natal_planet_name=nat_p.name,
                    aspect_type=asp_type,
                    aspect_name=ASPECT_NAMES[asp_type],
                    orb=round(orb, 4),
                    max_orb=round(max_o, 2),
                    applying=applying,
                    exact=exact,
                ))

    # Sort by orb (tightest aspects first)
    cross_aspects.sort(key=lambda a: a.orb)

    return ReturnNatalOverlayResult(
        natal_planets=natal_planets,
        placements=placements,
        cross_aspects=cross_aspects,
    )
