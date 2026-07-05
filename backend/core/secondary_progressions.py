"""
Secondary Progressions — day-for-a-year method.

Formula:
    age_years    = (target_jd  − birth_jd) / 365.25
    progressed_jd = birth_jd + age_years        [real days past birth]

Each real day after birth symbolises one year of life.  Planetary positions
and house cusps computed at progressed_jd represent the progressed chart.

Progressed Lunation:
    Phase angle  = (prog_moon_lon − prog_sun_lon) % 360°
    The synodic cycle in progressed time is ~29.5 symbolic years (days real).
    We find the most recent progressed New Moon (0°) and Full Moon (180°)
    before the current progressed moment using Newton-Raphson on the
    synodic phase function.
"""

from __future__ import annotations
from dataclasses import dataclass
import swisseph as swe

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

# Mean synodic speed of Moon relative to Sun (deg/day real ≈ deg/year symbolic)
_MOON_MEAN_SPEED    = 13.176  # deg/day
_SUN_MEAN_SPEED     = 0.9856  # deg/day
_SYNODIC_SPEED_MEAN = _MOON_MEAN_SPEED - _SUN_MEAN_SPEED  # ~12.19 deg/day

# Tertiary progression month lengths (real days per symbolic period)
SIDEREAL_MONTH = 27.32158   # days — Moon's sidereal revolution
SYNODIC_MONTH  = 29.53059   # days — Moon's synodic (phase) cycle


# ── Phase helpers ─────────────────────────────────────────────────────────────

def _phase_angle(jd: float) -> float:
    """(prog_moon_lon − prog_sun_lon) % 360°."""
    r_m, _ = swe.calc_ut(jd, swe.MOON, _FLAGS)
    r_s, _ = swe.calc_ut(jd, swe.SUN,  _FLAGS)
    return (r_m[0] - r_s[0]) % 360.0


_PHASE_NAMES = [
    (0.0,   22.5,  "New Moon"),
    (22.5,  67.5,  "Waxing Crescent"),
    (67.5,  112.5, "First Quarter"),
    (112.5, 157.5, "Waxing Gibbous"),
    (157.5, 202.5, "Full Moon"),
    (202.5, 247.5, "Disseminating"),
    (247.5, 292.5, "Last Quarter"),
    (292.5, 337.5, "Waning Crescent"),
    (337.5, 360.0, "New Moon"),
]


def _phase_name(angle: float) -> str:
    for lo, hi, name in _PHASE_NAMES:
        if lo <= angle < hi:
            return name
    return "New Moon"


def _find_last_lunation(jd_prog: float, target_phase: float) -> float:
    """
    Return the most recent JD strictly before `jd_prog` where
    (prog_moon − prog_sun) % 360 == target_phase.

    Uses a synodic-speed estimate for the initial seed, then N-R refinement.
    """
    current_phase = _phase_angle(jd_prog)

    # Degrees we need to go backward to reach the last occurrence
    delta = (current_phase - target_phase) % 360.0
    if delta < 1e-4:
        delta = 360.0   # we are exactly there — step back one full cycle

    jd_est = jd_prog - delta / _SYNODIC_SPEED_MEAN

    # Newton-Raphson
    for _ in range(30):
        r_moon, _ = swe.calc_ut(jd_est, swe.MOON, _FLAGS)
        r_sun,  _ = swe.calc_ut(jd_est, swe.SUN,  _FLAGS)
        phase = (r_moon[0] - r_sun[0]) % 360.0
        diff  = (phase - target_phase + 180.0) % 360.0 - 180.0
        if abs(diff) < 1e-8:
            break
        syn_speed = r_moon[3] - r_sun[3]
        if abs(syn_speed) < 0.01:
            syn_speed = _SYNODIC_SPEED_MEAN
        jd_est -= diff / syn_speed

    # Safety: result must precede the target moment
    if jd_est >= jd_prog:
        jd_est -= 360.0 / _SYNODIC_SPEED_MEAN   # go back one synodic cycle and re-refine
        for _ in range(10):
            r_moon, _ = swe.calc_ut(jd_est, swe.MOON, _FLAGS)
            r_sun,  _ = swe.calc_ut(jd_est, swe.SUN,  _FLAGS)
            phase = (r_moon[0] - r_sun[0]) % 360.0
            diff  = (phase - target_phase + 180.0) % 360.0 - 180.0
            if abs(diff) < 1e-8:
                break
            syn_speed = r_moon[3] - r_sun[3] or _SYNODIC_SPEED_MEAN
            jd_est -= diff / syn_speed

    return jd_est


# ── JD conversion ─────────────────────────────────────────────────────────────

def progressed_jd(birth_jd: float, target_jd: float) -> tuple[float, float]:
    """
    Return (age_years, jd_prog) for the day-for-a-year method.

    age_years = (target_jd − birth_jd) / 365.25
    jd_prog   = birth_jd + age_years      (days after birth)
    """
    age = (target_jd - birth_jd) / 365.25
    return age, birth_jd + age


def tertiary_jd(
    birth_jd: float,
    target_jd: float,
    month_type: str = "sidereal",
) -> tuple[float, float, float]:
    """
    Return (age_months, jd_prog, month_days) for the day-for-a-month method.

    Tertiary progressions: 1 real day = 1 lunar month of life.

    month_type:
        "sidereal" → 1 day = 27.32158 days  (Moon's sidereal revolution)
        "synodic"  → 1 day = 29.53059 days  (Moon's synodic/phase cycle)

    age_months = (target_jd − birth_jd) / month_days
    jd_prog    = birth_jd + age_months
    """
    month_days = SYNODIC_MONTH if month_type == "synodic" else SIDEREAL_MONTH
    age_months = (target_jd - birth_jd) / month_days
    return age_months, birth_jd + age_months, month_days


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ProgressedLunation:
    phase_angle:        float   # 0–360°  (prog_moon − prog_sun)
    phase_name:         str
    last_new_moon_jd:   float   # progressed JD of last prog New Moon
    last_new_moon_age:  float   # symbolic age (years) at that New Moon
    last_full_moon_jd:  float   # progressed JD of last prog Full Moon
    last_full_moon_age: float


# ── Main calculation ───────────────────────────────────────────────────────────

def calc_progressed_lunation(birth_jd: float, jd_prog: float) -> ProgressedLunation:
    """Compute the progressed lunar phase and locate the last NM/FM."""
    angle = _phase_angle(jd_prog)

    jd_nm = _find_last_lunation(jd_prog, 0.0)
    jd_fm = _find_last_lunation(jd_prog, 180.0)

    age_nm = jd_nm - birth_jd
    age_fm = jd_fm - birth_jd

    return ProgressedLunation(
        phase_angle=round(angle, 4),
        phase_name=_phase_name(angle),
        last_new_moon_jd=round(jd_nm, 6),
        last_new_moon_age=round(age_nm, 4),
        last_full_moon_jd=round(jd_fm, 6),
        last_full_moon_age=round(age_fm, 4),
    )
