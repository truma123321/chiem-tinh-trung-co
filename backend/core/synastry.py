"""
Synastry — comparison of two natal charts (Epic 8.1).

Computes three layers of inter-chart analysis:
  1. Cross-aspects: A's planets vs B's planets (5 Ptolemaic aspects, fixed orbs).
  2. Overlay houses: each planet placed in the other chart's house system.
  3. Antiscia synastry: shadow points (antiscion/contra-antiscion) of A vs B
     planets and B vs A planets.

Planet IDs: 0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
"""

from __future__ import annotations
from dataclasses import dataclass, field

# ─── Constants ────────────────────────────────────────────────────────────────

_PLANET_NAMES: dict[int, str] = {
    0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
    4: "Mars", 5: "Jupiter", 6: "Saturn",
}

# Standard synastry orbs (slightly smaller than natal)
SYNASTRY_ORBS: dict[int, float] = {
    0:   8.0,   # Conjunction
    60:  4.0,   # Sextile
    90:  7.0,   # Square
    120: 7.0,   # Trine
    180: 8.0,   # Opposition
}

ASPECT_NAMES: dict[int, str] = {
    0: "Conjunction", 60: "Sextile", 90: "Square",
    120: "Trine", 180: "Opposition",
}

# Antiscia orbs (tighter, following classical tradition)
ANTISCIA_CONJ_ORB   = 1.0   # conjunction/antiscia orb
ANTISCIA_ASPECT_ORB = 0.5   # other aspects
ANTISCIA_ORBS: dict[int, float] = {
    0:   ANTISCIA_CONJ_ORB,
    60:  ANTISCIA_ASPECT_ORB,
    90:  ANTISCIA_ASPECT_ORB,
    120: ANTISCIA_ASPECT_ORB,
    180: ANTISCIA_ASPECT_ORB,
}


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class SynastryAspect:
    planet_a_id:   int
    planet_a_name: str
    planet_b_id:   int
    planet_b_name: str
    aspect_angle:  int      # 0, 60, 90, 120, 180
    aspect_name:   str
    orb:           float    # actual orb in degrees
    max_orb:       float    # allowed max orb for this aspect


@dataclass
class OverlayPlanet:
    planet_id:   int
    planet_name: str
    planet_lon:  float
    house:       int        # 1–12 in the receiving chart


@dataclass
class SynastryAntisciaAspect:
    source:      str    # "A" or "B" — which chart's planet provides the shadow
    planet_id:   int    # the planet whose antiscion is used
    planet_name: str
    shadow_type: str    # "antiscion" | "contra_antiscion"
    shadow_lon:  float
    target_id:   int    # the other chart's planet
    target_name: str
    target_lon:  float
    aspect_angle: int
    aspect_name:  str
    orb:          float


@dataclass
class SynastryResult:
    cross_aspects:         list[SynastryAspect]
    a_planets_in_b_houses: list[OverlayPlanet]
    b_planets_in_a_houses: list[OverlayPlanet]
    antiscia_aspects:      list[SynastryAntisciaAspect]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _arc(lon_a: float, lon_b: float) -> float:
    """Shortest arc between two longitudes, returned in [0°, 180°]."""
    diff = abs(lon_a - lon_b) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff


def _antiscion(lon: float) -> float:
    """Mirror of lon over the Cancer/Capricorn axis (90°/270°)."""
    return (180.0 - lon) % 360.0


def _contra_antiscion(lon: float) -> float:
    """Mirror of lon over the Aries/Libra axis (0°/180°)."""
    return (360.0 - lon) % 360.0


def _find_house(lon: float, cusps: list[float]) -> int:
    """
    Return the 1-based house number that `lon` falls in.
    `cusps`: 12 values, index 0 = house-1 cusp … index 11 = house-12 cusp.
    """
    for h in range(12):
        c1 = cusps[h]
        c2 = cusps[(h + 1) % 12]
        if c2 > c1:
            if c1 <= lon < c2:
                return h + 1
        else:          # segment wraps around 0°/360°
            if lon >= c1 or lon < c2:
                return h + 1
    return 1           # fallback


# ─── Core calculation ──────────────────────────────────────────────────────────

def calc_synastry(
    planet_lons_a: dict[int, float],
    planet_lons_b: dict[int, float],
    cusps_a: list[float],   # 12 cusp longitudes for chart A (houses 1–12)
    cusps_b: list[float],   # 12 cusp longitudes for chart B (houses 1–12)
) -> SynastryResult:
    """
    Compare two natal charts.

    planet_lons_a/b : {planet_id: ecliptic_longitude} for the 7 classical planets.
    cusps_a/b       : list of 12 house cusp longitudes (house 1 first).
    """

    # ── 1. Cross-aspects ──────────────────────────────────────────────────────
    cross_aspects: list[SynastryAspect] = []
    for pid_a, lon_a in sorted(planet_lons_a.items()):
        for pid_b, lon_b in sorted(planet_lons_b.items()):
            arc = _arc(lon_a, lon_b)
            for angle, max_orb in sorted(SYNASTRY_ORBS.items()):
                orb = abs(arc - angle)
                if orb <= max_orb:
                    cross_aspects.append(SynastryAspect(
                        planet_a_id=pid_a,
                        planet_a_name=_PLANET_NAMES[pid_a],
                        planet_b_id=pid_b,
                        planet_b_name=_PLANET_NAMES[pid_b],
                        aspect_angle=angle,
                        aspect_name=ASPECT_NAMES[angle],
                        orb=round(orb, 4),
                        max_orb=max_orb,
                    ))

    # ── 2. Overlay houses ─────────────────────────────────────────────────────
    a_planets_in_b: list[OverlayPlanet] = [
        OverlayPlanet(
            planet_id=pid, planet_name=_PLANET_NAMES[pid],
            planet_lon=round(lon, 4),
            house=_find_house(lon, cusps_b),
        )
        for pid, lon in sorted(planet_lons_a.items())
    ]

    b_planets_in_a: list[OverlayPlanet] = [
        OverlayPlanet(
            planet_id=pid, planet_name=_PLANET_NAMES[pid],
            planet_lon=round(lon, 4),
            house=_find_house(lon, cusps_a),
        )
        for pid, lon in sorted(planet_lons_b.items())
    ]

    # ── 3. Antiscia synastry aspects ──────────────────────────────────────────
    antiscia_aspects: list[SynastryAntisciaAspect] = []

    for source, lons_src, lons_tgt in [
        ("A", planet_lons_a, planet_lons_b),
        ("B", planet_lons_b, planet_lons_a),
    ]:
        for pid_src, lon_src in sorted(lons_src.items()):
            shadows = [
                ("antiscion",        _antiscion(lon_src)),
                ("contra_antiscion", _contra_antiscion(lon_src)),
            ]
            for shadow_type, shadow_lon in shadows:
                for pid_tgt, lon_tgt in sorted(lons_tgt.items()):
                    arc = _arc(shadow_lon, lon_tgt)
                    for angle, asp_orb in sorted(ANTISCIA_ORBS.items()):
                        orb = abs(arc - angle)
                        if orb <= asp_orb:
                            antiscia_aspects.append(SynastryAntisciaAspect(
                                source=source,
                                planet_id=pid_src,
                                planet_name=_PLANET_NAMES[pid_src],
                                shadow_type=shadow_type,
                                shadow_lon=round(shadow_lon, 4),
                                target_id=pid_tgt,
                                target_name=_PLANET_NAMES[pid_tgt],
                                target_lon=round(lon_tgt, 4),
                                aspect_angle=angle,
                                aspect_name=ASPECT_NAMES[angle],
                                orb=round(orb, 4),
                            ))

    return SynastryResult(
        cross_aspects=cross_aspects,
        a_planets_in_b_houses=a_planets_in_b,
        b_planets_in_a_houses=b_planets_in_a,
        antiscia_aspects=antiscia_aspects,
    )
