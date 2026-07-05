"""
Doryphory (Spear-Bearers) — Epic 6.5.

Ancient Hellenistic doctrine of solar bodyguards.

Morning spear-bearers (Doryphoros):
  Planets Oriental and within 30° of the Sun — they rise just before the Sun.
  Elongation: 0° < (planet_lon − sun_lon) % 360 < 30°

Evening spear-bearers (Akolouthos):
  Planets Occidental and within 30° of the Sun — they set just after the Sun.
  Elongation: 330° < (planet_lon − sun_lon) % 360 < 360°

Planets exactly conjunct the Sun (elongation = 0°) are excluded
(they are cazimi/combust, not spear-bearers).

Planet IDs: 0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
"""

from __future__ import annotations
from dataclasses import dataclass

_PLANET_NAMES = {
    0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
    4: "Mars", 5: "Jupiter", 6: "Saturn",
}

DEFAULT_ORB: float = 30.0   # degrees — standard doryphory orb


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class DoryphoryBearer:
    planet_id:    int
    planet_name:  str
    elongation:   float   # (planet_lon − sun_lon) % 360, raw (0–360°)
    sun_distance: float   # arc distance from Sun (0–orb degrees)
    bearer_type:  str     # "morning" | "evening"


@dataclass
class DoryphoryResult:
    morning_bearers: list[DoryphoryBearer]   # Oriental, within orb
    evening_bearers: list[DoryphoryBearer]   # Occidental, within orb
    has_doryphory:   bool                    # True when any bearer exists
    bearer_count:    int                     # total morning + evening


# ─── Core calculation ─────────────────────────────────────────────────────────

def calc_doryphory(
    planet_lons: dict,          # {0..6: ecliptic longitude}
    orb: float = DEFAULT_ORB,   # maximum elongation for a bearer (default 30°)
) -> DoryphoryResult:
    """
    Find all morning and evening spear-bearers among the 7 traditional planets.

    A planet is a morning bearer  when 0° < elongation <  orb.
    A planet is an evening bearer when 0° < (360° − elongation) < orb.
    (elongation = (planet_lon − sun_lon) % 360)

    The Sun (pid=0) is skipped; all other classical planets are checked.
    """
    sun_lon = planet_lons[0]
    morning: list[DoryphoryBearer] = []
    evening: list[DoryphoryBearer] = []

    for pid in range(1, 7):   # Moon through Saturn, skip Sun
        lon   = planet_lons[pid]
        elong = (lon - sun_lon) % 360.0

        if 0.0 < elong < orb:
            # Morning bearer: planet is ahead of Sun (Oriental) within orb
            morning.append(DoryphoryBearer(
                planet_id=pid,
                planet_name=_PLANET_NAMES[pid],
                elongation=round(elong, 4),
                sun_distance=round(elong, 4),
                bearer_type="morning",
            ))
        elif (360.0 - orb) < elong < 360.0:
            # Evening bearer: planet is behind Sun (Occidental) within orb
            dist = 360.0 - elong
            evening.append(DoryphoryBearer(
                planet_id=pid,
                planet_name=_PLANET_NAMES[pid],
                elongation=round(elong, 4),
                sun_distance=round(dist, 4),
                bearer_type="evening",
            ))

    return DoryphoryResult(
        morning_bearers=morning,
        evening_bearers=evening,
        has_doryphory=bool(morning or evening),
        bearer_count=len(morning) + len(evening),
    )
