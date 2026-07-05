"""
Planetary Conditions — classical / medieval tradition.

Solar proximity conditions (per Bonatti, Liber Astronomiae):
  Cazimi       : planet within 0°17' of Sun's exact longitude (in the heart)
  Combust      : planet within 8° of Sun (not cazimi) — severe debility
  Under Beams  : planet within 15° of Sun (not combust) — moderate debility
  Free         : beyond 15° from Sun — no solar debility

Oriental / Occidental (per Bonatti / Ptolemy):
  Oriental     : planet's longitude is ahead of the Sun in zodiac order
                 (planet_lon - sun_lon) % 360 < 180°
  Occidental   : planet is behind the Sun in zodiac order

Void of Course Moon (classical Hellenistic / Bonatti):
  Moon will make NO more applying aspects (by orb) to the 7 classical
  planets before it changes sign.

Planet IDs: 0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
"""

from __future__ import annotations
from dataclasses import dataclass
from core.aspects import ASPECT_ANGLES, DEFAULT_ORB, _arc, _combined_orb

# ─── Solar proximity thresholds ────────────────────────────────────────────

CAZIMI_ORB    =  17 / 60.0    # 0°17' in decimal degrees
COMBUST_ORB   =  8.0          # 8° (most medieval sources)
BEAMS_ORB     = 15.0          # 15° (under the beams)

# These are the SUN's default threshold contributions
# Combined orb for Sun-planet = (sun_orb + planet_orb) / 2
# But solar proximity uses FIXED thresholds, not combined orbs.


# ─── Result type ───────────────────────────────────────────────────────────

@dataclass
class PlanetCondition:
    planet_id: int
    planet_name: str

    # Solar proximity
    sun_distance: float      # arc distance from Sun in degrees (0–180)
    cazimi: bool             # within 0°17' of Sun
    combust: bool            # within 8° (not cazimi)
    under_beams: bool        # within 15° (not combust/cazimi)
    free_from_beams: bool    # beyond 15°

    # Direction relative to Sun
    oriental: bool           # ahead of Sun in zodiac order (planet_lon > sun_lon within 180°)
    occidental: bool         # behind the Sun in zodiac order

    # Phase elongation (raw signed value for display)
    elongation: float        # (planet_lon - sun_lon) % 360 — 0° to 360°


@dataclass
class MoonCondition:
    void_of_course: bool
    # If not void: which planet and aspect it will perfect next
    next_aspect_planet: int | None      # planet ID
    next_aspect_planet_name: str | None
    next_aspect_type: int | None        # from ASPECT_ANGLES keys
    next_aspect_orb: float | None       # remaining degrees to perfection


@dataclass
class ConditionsResult:
    planet_conditions: list[PlanetCondition]  # for planets 1–6 (Moon–Saturn, Sun excluded)
    moon: MoonCondition


# ─── Helpers ───────────────────────────────────────────────────────────────

_PLANET_NAMES = {
    0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
    4: "Mars", 5: "Jupiter", 6: "Saturn",
}

_ASPECT_NAMES = {0: "Conjunction", 1: "Sextile", 2: "Square", 3: "Trine", 4: "Opposition"}


def _degrees_remaining_in_sign(lon: float, speed: float) -> float:
    """Degrees until planet leaves its current sign (forward motion assumed)."""
    sign_end = (int(lon / 30) + 1) * 30.0
    return sign_end - (lon % 360)


# ─── Core calculation ──────────────────────────────────────────────────────

def calc_conditions(
    planet_lons: dict,    # {0..6: ecliptic longitude}
    planet_speeds: dict,  # {0..6: speed deg/day, negative=retrograde}
) -> ConditionsResult:
    """
    Compute solar proximity conditions for Moon–Saturn,
    and void-of-course status for the Moon.
    """
    sun_lon   = planet_lons[0]
    moon_lon  = planet_lons[1]
    moon_spd  = planet_speeds.get(1, 13.0)   # Moon ~13°/day

    planet_conditions: list[PlanetCondition] = []

    for pid in range(1, 7):   # Moon through Saturn (exclude Sun)
        lon = planet_lons[pid]
        dist = _arc(lon, sun_lon)          # 0–180°

        cazimi      = dist <= CAZIMI_ORB
        combust     = (not cazimi) and dist <= COMBUST_ORB
        under_beams = (not cazimi) and (not combust) and dist <= BEAMS_ORB
        free        = dist > BEAMS_ORB

        # Oriental: planet is ahead of Sun in zodiac order (rising before Sun)
        elong = (lon - sun_lon) % 360      # 0–360°
        oriental   = elong < 180.0
        occidental = elong >= 180.0

        planet_conditions.append(PlanetCondition(
            planet_id=pid,
            planet_name=_PLANET_NAMES[pid],
            sun_distance=round(dist, 4),
            cazimi=cazimi,
            combust=combust,
            under_beams=under_beams,
            free_from_beams=free,
            oriental=oriental,
            occidental=occidental,
            elongation=round(elong, 4),
        ))

    # ── Void of Course Moon ────────────────────────────────────────────────
    # Moon is VOC when no applying aspect to the 7 planets will perfect
    # before Moon leaves its current sign.

    degrees_left = _degrees_remaining_in_sign(moon_lon, moon_spd)
    # Moon speed ≈ 13°/day, so days left in sign = degrees_left / moon_speed
    # We check if Moon will perfect any aspect within those remaining degrees.

    # For each planet (Sun–Saturn), find if Moon applies to an aspect
    # that will perfect within the remaining sign degrees.

    best_next: tuple[float, int, int, float] | None = None   # (degrees_to_perfect, pid, asp_type, current_orb)

    for pid in range(0, 7):
        if pid == 1:
            continue   # skip Moon-Moon

        other_lon = planet_lons[pid]
        other_spd = planet_speeds.get(pid, 0.0)

        arc = _arc(moon_lon, other_lon)
        max_orb = _combined_orb(1, pid)

        for asp_type, angle in ASPECT_ANGLES.items():
            orb = abs(arc - angle)
            if orb > max_orb:
                continue

            # Check application using relative velocity.
            # Moon-planet relative closing speed: positive = closing.
            # For a conjunction: Moon applies if Moon approaches planet longitude.
            # General case: use small dt to avoid overshooting fast Moon.
            dt = 1.0 / 48.0   # 30-minute steps for accuracy
            moon_lon1  = (moon_lon  + moon_spd  * dt) % 360
            other_lon1 = (other_lon + other_spd * dt) % 360
            arc1 = _arc(moon_lon1, other_lon1)
            orb1 = abs(arc1 - angle)

            if orb1 >= orb:
                continue   # separating (or stationary)

            # Rate of orb closure per day
            daily_closure = (orb - orb1) / dt
            if daily_closure <= 0:
                continue
            days_to_exact = orb / daily_closure
            degrees_moon_travels = days_to_exact * abs(moon_spd)

            if degrees_moon_travels <= degrees_left:
                # This aspect will perfect before Moon changes sign
                if best_next is None or degrees_moon_travels < best_next[0]:
                    best_next = (degrees_moon_travels, pid, asp_type, orb)

    if best_next is None:
        moon_cond = MoonCondition(
            void_of_course=True,
            next_aspect_planet=None,
            next_aspect_planet_name=None,
            next_aspect_type=None,
            next_aspect_orb=None,
        )
    else:
        _, next_pid, next_asp, next_orb = best_next
        moon_cond = MoonCondition(
            void_of_course=False,
            next_aspect_planet=next_pid,
            next_aspect_planet_name=_PLANET_NAMES[next_pid],
            next_aspect_type=next_asp,
            next_aspect_orb=round(next_orb, 4),
        )

    return ConditionsResult(
        planet_conditions=planet_conditions,
        moon=moon_cond,
    )
