"""
Accidental Dignities Full Scoring — Epic 6.2.

Computes accidental dignity score for each of the 7 traditional planets.

Scoring table (Morinus / Bonatti tradition):

  House type:
    Angular   (I, IV, VII, X)   +5
    Succedent (II, V, VIII, XI) +3
    Cadent    (III, VI, IX, XII) +1

  Motion speed (vs mean daily motion):
    Fast in motion               +2
    Slow in motion               -2

  Direction:
    Direct                       +4
    Retrograde                   -5

  Light phase (elongation from Sun):
    Increasing in light          +2   (elongation 0-180°, toward opposition)
    Decreasing in light          -2   (elongation 180-360°, toward conjunction)

  Solar proximity (from calc_conditions):
    Cazimi                       +5
    Free from beams              +5
    Under beams                  -4
    Combust                      -5

  Hayz (from calc_sect):
    In hayz                      +6

  Joy:
    In joy house                 +1
"""

from __future__ import annotations
from dataclasses import dataclass

from core.conditions import ConditionsResult
from core.sect import SectResult, JOY_HOUSE, planet_house

# ─── Constants ──────────────────────────────────────────────────────────────────

_PLANET_NAMES = {
    0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
    4: "Mars", 5: "Jupiter", 6: "Saturn",
}

# Mean daily motion in degrees/day
_MEAN_MOTION = {
    0: 0.9856,    # Sun
    1: 13.18,     # Moon
    2: 1.383,     # Mercury
    3: 1.2,       # Venus
    4: 0.524,     # Mars
    5: 0.083,     # Jupiter
    6: 0.034,     # Saturn
}

_ANGULAR   = frozenset([1, 4, 7, 10])
_SUCCEDENT = frozenset([2, 5, 8, 11])
_CADENT    = frozenset([3, 6, 9, 12])


# ─── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class AccidentalDignityResult:
    planet_id:   int
    planet_name: str
    house:       int    # 1-based house number

    # Condition flags
    is_angular:       bool
    is_succedent:     bool
    is_cadent:        bool
    fast_in_motion:   bool
    slow_in_motion:   bool
    direct:           bool
    retrograde:       bool
    increasing_light: bool
    decreasing_light: bool
    cazimi:           bool
    free_from_beams:  bool
    under_beams:      bool
    combust:          bool
    in_hayz:          bool
    in_joy:           bool

    # Score breakdown
    house_score:      int
    motion_score:     int
    direction_score:  int
    light_score:      int
    solar_score:      int
    hayz_score:       int
    joy_score:        int

    accidental_score: int


# ─── Core calculation ────────────────────────────────────────────────────────────

def calc_accidental_dignities(
    planet_lons:   dict,         # {0..6: ecliptic longitude}
    planet_speeds: dict,         # {0..6: speed deg/day, negative=retrograde}
    house_cusps:   list[float],  # 12 values — house_cusps[0] = H1 longitude
    cond_result:   ConditionsResult,
    sect_result:   SectResult,
) -> list[AccidentalDignityResult]:
    """
    Compute accidental dignity score for each of the 7 traditional planets.

    Returns a list of 7 AccidentalDignityResult objects in planet-id order
    (Sun=0 first, Saturn=6 last).
    """
    cond_by_pid = {c.planet_id: c for c in cond_result.planet_conditions}
    sect_by_pid = {s.planet_id: s for s in sect_result.planet_sects}

    results: list[AccidentalDignityResult] = []

    for pid in range(7):
        lon   = planet_lons[pid]
        speed = planet_speeds[pid]

        # ── House type ─────────────────────────────────────────────────────────
        house = planet_house(lon, house_cusps)

        is_angular   = house in _ANGULAR
        is_succedent = house in _SUCCEDENT
        is_cadent    = house in _CADENT

        house_score = 5 if is_angular else (3 if is_succedent else 1)

        # ── Motion speed ───────────────────────────────────────────────────────
        mean  = _MEAN_MOTION[pid]
        aspd  = abs(speed)

        fast_in_motion = aspd > mean
        slow_in_motion = aspd < mean

        motion_score = 2 if fast_in_motion else (-2 if slow_in_motion else 0)

        # ── Direction ──────────────────────────────────────────────────────────
        retrograde = speed < 0.0
        direct     = not retrograde

        direction_score = -5 if retrograde else 4

        # ── Light phase ────────────────────────────────────────────────────────
        # The Sun has no elongation from itself.
        if pid == 0:
            increasing_light = False
            decreasing_light = False
            light_score      = 0
        else:
            cond = cond_by_pid.get(pid)
            elong = cond.elongation if cond else 0.0
            # 0–180° = moving toward opposition = increasing in light
            # 180–360° = moving back toward conjunction = decreasing in light
            increasing_light = elong < 180.0
            decreasing_light = not increasing_light
            light_score      = 2 if increasing_light else -2

        # ── Solar proximity ────────────────────────────────────────────────────
        # Sun is its own light — no proximity score.
        if pid == 0:
            cazimi = free_from_beams = under_beams = combust = False
            solar_score = 0
        else:
            cond = cond_by_pid.get(pid)
            if cond:
                cazimi          = cond.cazimi
                free_from_beams = cond.free_from_beams
                under_beams     = cond.under_beams
                combust         = cond.combust
            else:
                cazimi = free_from_beams = under_beams = combust = False

            if cazimi:
                solar_score = 5
            elif combust:
                solar_score = -5
            elif under_beams:
                solar_score = -4
            elif free_from_beams:
                solar_score = 5
            else:
                solar_score = 0   # safety fallback

        # ── Hayz ──────────────────────────────────────────────────────────────
        sect    = sect_by_pid.get(pid)
        in_hayz = sect.in_hayz if sect else False
        hayz_score = 6 if in_hayz else 0

        # ── Joy ───────────────────────────────────────────────────────────────
        in_joy    = house == JOY_HOUSE.get(pid, -1)
        joy_score = 1 if in_joy else 0

        # ── Total accidental score ─────────────────────────────────────────────
        accidental_score = (
            house_score + motion_score + direction_score + light_score
            + solar_score + hayz_score + joy_score
        )

        results.append(AccidentalDignityResult(
            planet_id=pid,
            planet_name=_PLANET_NAMES[pid],
            house=house,
            is_angular=is_angular,
            is_succedent=is_succedent,
            is_cadent=is_cadent,
            fast_in_motion=fast_in_motion,
            slow_in_motion=slow_in_motion,
            direct=direct,
            retrograde=retrograde,
            increasing_light=increasing_light,
            decreasing_light=decreasing_light,
            cazimi=cazimi,
            free_from_beams=free_from_beams,
            under_beams=under_beams,
            combust=combust,
            in_hayz=in_hayz,
            in_joy=in_joy,
            house_score=house_score,
            motion_score=motion_score,
            direction_score=direction_score,
            light_score=light_score,
            solar_score=solar_score,
            hayz_score=hayz_score,
            joy_score=joy_score,
            accidental_score=accidental_score,
        ))

    return results
