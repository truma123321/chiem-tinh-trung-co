"""
Composite Chart — midpoint method (Epic 8.2).

The composite chart is formed by taking the near midpoint of each pair of
corresponding points from two natal charts:
  - 7 classical planet positions (Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn)
  - Ascendant
  - Midheaven (MC)

Near midpoint of two ecliptic longitudes A and B:
  diff = (B - A) mod 360°
  if diff <= 180°: midpoint = A + diff/2
  else:            midpoint = A + diff/2 + 180°  (crosses 0°/360° boundary)

Aspects are computed between the composite planets using standard natal orbs.

Planet IDs: 0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
"""

from __future__ import annotations
from dataclasses import dataclass, field

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

# Aspect orbs for composite chart (same as standard natal orbs)
COMPOSITE_ORBS: dict[int, float] = {
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


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class CompositePlanet:
    planet_id:   int
    planet_name: str
    lon:         float      # composite (midpoint) longitude [0°, 360°)
    sign:        str        # zodiac sign name
    sign_lon:    float      # degrees within sign [0°, 30°)
    retrograde:  bool       # True if BOTH natal planets are retrograde


@dataclass
class CompositeAspect:
    planet_a_id:   int
    planet_a_name: str
    planet_b_id:   int
    planet_b_name: str
    aspect_angle:  int      # 0, 60, 90, 120, 180
    aspect_name:   str
    orb:           float
    max_orb:       float


@dataclass
class CompositeResult:
    planets:  list[CompositePlanet]    # 7 classical, ordered by planet_id
    asc:      float                    # composite ASC longitude
    asc_sign: str
    mc:       float                    # composite MC longitude
    mc_sign:  str
    aspects:  list[CompositeAspect]    # aspects between composite planets


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _midpoint(lon_a: float, lon_b: float) -> float:
    """
    Near midpoint of two ecliptic longitudes.
    Returns the midpoint on the shorter arc between lon_a and lon_b.
    Result is in [0°, 360°).
    """
    diff = (lon_b - lon_a) % 360.0
    if diff <= 180.0:
        return (lon_a + diff / 2.0) % 360.0
    else:
        return (lon_a + diff / 2.0 + 180.0) % 360.0


def _sign_info(lon: float) -> tuple[str, float]:
    idx = int(lon / 30.0) % 12
    return _SIGNS[idx], round(lon % 30.0, 4)


def _arc(lon_a: float, lon_b: float) -> float:
    """Shortest arc between two longitudes, [0°, 180°]."""
    diff = abs(lon_a - lon_b) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff


# ─── Core calculation ──────────────────────────────────────────────────────────

def calc_composite(
    planet_lons_a:   dict[int, float],
    planet_lons_b:   dict[int, float],
    planet_speeds_a: dict[int, float],
    planet_speeds_b: dict[int, float],
    asc_a: float,
    asc_b: float,
    mc_a:  float,
    mc_b:  float,
) -> CompositeResult:
    """
    Compute the composite chart from two natal charts.

    planet_lons_a/b   : {planet_id: longitude} for 7 classical planets.
    planet_speeds_a/b : {planet_id: daily motion} — negative = retrograde.
    asc_a/b           : Ascendant longitudes.
    mc_a/b            : Midheaven longitudes.
    """

    # ── Composite planets ─────────────────────────────────────────────────────
    planets: list[CompositePlanet] = []
    for pid in range(7):
        lon = _midpoint(planet_lons_a[pid], planet_lons_b[pid])
        lon = round(lon % 360.0, 4)
        sign, sign_lon = _sign_info(lon)
        retrograde = (planet_speeds_a[pid] < 0) and (planet_speeds_b[pid] < 0)
        planets.append(CompositePlanet(
            planet_id=pid,
            planet_name=_PLANET_NAMES[pid],
            lon=lon,
            sign=sign,
            sign_lon=sign_lon,
            retrograde=retrograde,
        ))

    # ── Composite angles ──────────────────────────────────────────────────────
    comp_asc = round(_midpoint(asc_a, asc_b) % 360.0, 4)
    comp_mc  = round(_midpoint(mc_a,  mc_b)  % 360.0, 4)
    asc_sign, _ = _sign_info(comp_asc)
    mc_sign,  _ = _sign_info(comp_mc)

    # ── Composite aspects (between composite planets) ─────────────────────────
    aspects: list[CompositeAspect] = []
    for i in range(7):
        for j in range(i + 1, 7):   # unique pairs only, no self-aspects
            arc = _arc(planets[i].lon, planets[j].lon)
            for angle, max_orb in sorted(COMPOSITE_ORBS.items()):
                orb = abs(arc - angle)
                if orb <= max_orb:
                    aspects.append(CompositeAspect(
                        planet_a_id=planets[i].planet_id,
                        planet_a_name=planets[i].planet_name,
                        planet_b_id=planets[j].planet_id,
                        planet_b_name=planets[j].planet_name,
                        aspect_angle=angle,
                        aspect_name=ASPECT_NAMES[angle],
                        orb=round(orb, 4),
                        max_orb=max_orb,
                    ))

    return CompositeResult(
        planets=planets,
        asc=comp_asc,
        asc_sign=asc_sign,
        mc=comp_mc,
        mc_sign=mc_sign,
        aspects=aspects,
    )
