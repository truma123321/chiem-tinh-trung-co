"""
Antiscia & Contra-antiscia — classical / medieval tradition.

Antiscia (shadow points, per Bonatti / Lilly):
  Each planet casts a shadow point equidistant from the Cancer/Capricorn
  solstice axis.  Planets at antiscion positions share equal day-length
  and were considered to "see" each other in power.

  Formula (reflection across 0°Cancer / 0°Capricorn axis):
    antiscion(L) = (180° − L) % 360°

  Sign pairings (from Lilly, Christian Astrology):
    Aries ↔ Virgo | Taurus ↔ Leo | Gemini ↔ Cancer
    Libra ↔ Pisces | Scorpio ↔ Aquarius | Sagittarius ↔ Capricorn

Contra-antiscia (reflection across 0°Aries / 0°Libra equinox axis):
  contra(L) = (360° − L) % 360°   ≡ antiscion + 180° (mod 360°)

  Sign pairings:
    Aries ↔ Pisces | Taurus ↔ Aquarius | Gemini ↔ Capricorn
    Cancer ↔ Sagittarius | Leo ↔ Scorpio | Virgo ↔ Libra

Antiscia aspect detection (Epic 6.7 — all 5 major aspects):
  Planet A forms an aspect with Planet B via antiscia when the arc between
  A's antiscion/contra-antiscion point and B's natal longitude matches one
  of the 5 major Ptolemaic angles within the aspect-specific orb.

  Orbs:
    Conjunction (0°)  : 1.0° (ANTISCIA_ORB)
    Sextile/Square/Trine/Opposition: 0.5° (ANTISCIA_ASPECT_ORB)

Planet IDs: 0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
"""

from __future__ import annotations
from dataclasses import dataclass

# ─── Configuration ────────────────────────────────────────────────────────────

ANTISCIA_ORB        = 1.0   # conjunction orb (degrees)
ANTISCIA_ASPECT_ORB = 0.5   # non-conjunction aspect orb (degrees)

# Maps aspect angle → (name, orb)
ANTISCIA_ASPECTS: dict[int, tuple[str, float]] = {
    0:   ("Conjunction", ANTISCIA_ORB),
    60:  ("Sextile",     ANTISCIA_ASPECT_ORB),
    90:  ("Square",      ANTISCIA_ASPECT_ORB),
    120: ("Trine",       ANTISCIA_ASPECT_ORB),
    180: ("Opposition",  ANTISCIA_ASPECT_ORB),
}

# ─── Planet names ─────────────────────────────────────────────────────────────

_PLANET_NAMES = {
    0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
    4: "Mars", 5: "Jupiter", 6: "Saturn",
}


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class AntisciaPoint:
    planet_id: int
    planet_name: str
    lon: float              # actual ecliptic longitude
    antiscion: float        # shadow point = (180° − lon) % 360°
    contra_antiscion: float # contra-shadow = (360° − lon) % 360°


@dataclass
class AntisciaAspect:
    planet_a: int
    name_a: str
    planet_b: int
    name_b: str
    aspect_type: str   # "antiscion" | "contra_antiscion"
    aspect_angle: int  # 0, 60, 90, 120, 180
    aspect_name: str   # "Conjunction", "Sextile", "Square", "Trine", "Opposition"
    orb: float         # degrees


@dataclass
class AntisciaResult:
    points: list[AntisciaPoint]
    aspects: list[AntisciaAspect]   # sorted by orb


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _arc(a: float, b: float) -> float:
    """Shortest arc between two longitudes, 0–180°."""
    d = abs(a - b) % 360.0
    return d if d <= 180.0 else 360.0 - d


def _antiscion(lon: float) -> float:
    """Reflection across the 0°Cancer/0°Cap solstice axis."""
    return (180.0 - lon) % 360.0


def _contra(lon: float) -> float:
    """Reflection across the 0°Aries/0°Libra equinox axis."""
    return (360.0 - lon) % 360.0


# ─── Core calculation ─────────────────────────────────────────────────────────

def calc_antiscia(
    planet_lons: dict,   # {0..6: ecliptic longitude}
) -> AntisciaResult:
    """
    Compute antiscion / contra-antiscion shadow points for all 7 classical
    planets and detect all 5 major Ptolemaic aspects between antiscia points
    and natal planet positions.
    """
    # ── Shadow points ────────────────────────────────────────────────────────
    points: list[AntisciaPoint] = []
    for pid in range(7):
        lon = planet_lons[pid]
        points.append(AntisciaPoint(
            planet_id=pid,
            planet_name=_PLANET_NAMES[pid],
            lon=round(lon, 4),
            antiscion=round(_antiscion(lon), 4),
            contra_antiscion=round(_contra(lon), 4),
        ))

    # ── Aspect detection ─────────────────────────────────────────────────────
    # For each ordered pair (A < B) and each antiscia type, check all 5
    # major aspects between A's shadow point and B's natal longitude.
    aspects: list[AntisciaAspect] = []

    for i in range(7):
        for j in range(i + 1, 7):
            lon_a = planet_lons[i]
            lon_b = planet_lons[j]

            anti_a   = _antiscion(lon_a)
            contra_a = _contra(lon_a)

            arc_anti   = _arc(anti_a,   lon_b)
            arc_contra = _arc(contra_a, lon_b)

            for angle, (asp_name, asp_orb) in ANTISCIA_ASPECTS.items():
                diff_anti   = abs(arc_anti   - angle)
                diff_contra = abs(arc_contra - angle)

                if diff_anti <= asp_orb:
                    aspects.append(AntisciaAspect(
                        planet_a=i, name_a=_PLANET_NAMES[i],
                        planet_b=j, name_b=_PLANET_NAMES[j],
                        aspect_type="antiscion",
                        aspect_angle=angle,
                        aspect_name=asp_name,
                        orb=round(diff_anti, 4),
                    ))

                if diff_contra <= asp_orb:
                    aspects.append(AntisciaAspect(
                        planet_a=i, name_a=_PLANET_NAMES[i],
                        planet_b=j, name_b=_PLANET_NAMES[j],
                        aspect_type="contra_antiscion",
                        aspect_angle=angle,
                        aspect_name=asp_name,
                        orb=round(diff_contra, 4),
                    ))

    aspects.sort(key=lambda a: a.orb)
    return AntisciaResult(points=points, aspects=aspects)
