"""
Solar Arc Directions (Epic 4.2).

Method:
    solar_arc       = prog_sun_lon − natal_sun_lon     (mod 360°, always positive)
    directed_point  = natal_point_lon + solar_arc       (mod 360°)

The solar arc is derived from secondary progressions (1 day = 1 year).
Every natal point is pushed forward by the same arc: Sun's motion since birth.

Directed-to-natal aspects:
    Check all 5 Ptolemaic aspects between each directed point and each natal
    point (7 planets + ASC + MC on both sides).  Skip self-to-self pairs.
    Max orb for solar arc is typically 1–2° (= 1–2 years).

Exact hit date:
    For each aspect, find the real calendar date when the arc is exact using
    Newton-Raphson on the progressed Sun's longitude function.
"""

from __future__ import annotations
from dataclasses import dataclass
import swisseph as swe

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

# ── Aspect constants (same as aspects.py) ─────────────────────────────────────
CONJUNCTION = 0
SEXTILE     = 1
SQUARE      = 2
TRINE       = 3
OPPOSITION  = 4

ASPECT_ANGLES: dict[int, float] = {
    CONJUNCTION: 0.0,
    SEXTILE:    60.0,
    SQUARE:     90.0,
    TRINE:     120.0,
    OPPOSITION:180.0,
}

ASPECT_NAMES: dict[int, str] = {
    CONJUNCTION: "Conjunction",
    SEXTILE:     "Sextile",
    SQUARE:      "Square",
    TRINE:       "Trine",
    OPPOSITION:  "Opposition",
}

# Default combined orb per planet pair (half each)
_ORB: dict[str, float] = {
    "Sun": 15.0, "Moon": 12.0, "Mercury": 7.0, "Venus": 7.0,
    "Mars": 8.0, "Jupiter": 9.0, "Saturn": 9.0,
    "ASC": 8.0,  "MC": 8.0,
}
_DEFAULT_ORB = 7.0


def _combined_orb(name_a: str, name_b: str) -> float:
    return (_ORB.get(name_a, _DEFAULT_ORB) + _ORB.get(name_b, _DEFAULT_ORB)) / 2.0


def _arc(lon_a: float, lon_b: float) -> float:
    """Shortest arc between two longitudes (0–180°)."""
    d = abs(lon_a - lon_b) % 360
    return d if d <= 180 else 360 - d


# ── Exact date finder ─────────────────────────────────────────────────────────

def _find_exact_hit_jd(
    birth_jd: float,
    natal_sun_lon: float,
    target_arc: float,
    max_years: float = 120.0,
) -> float | None:
    """
    Find the real calendar JD when solar_arc = target_arc.

    Strategy:
        prog_sun(jd_p) − natal_sun ≡ target_arc (mod 360°)
        jd_p ≈ birth_jd + target_arc   (Sun ≈ 1°/day)
        Newton-Raphson on the residual.

    Returns the real calendar JD = birth_jd + age * 365.25,
    or None if the target is outside [0, max_years] range.
    """
    if target_arc < 0 or target_arc >= 360:
        return None

    # Initial estimate (1° per progressed day ≈ 1° per year)
    jd_p_est = birth_jd + target_arc

    for _ in range(30):
        r, _ = swe.calc_ut(jd_p_est, swe.SUN, _FLAGS)
        current_arc = (r[0] - natal_sun_lon) % 360.0
        diff = (current_arc - target_arc + 180.0) % 360.0 - 180.0
        if abs(diff) < 1e-8:
            break
        speed = r[3] if abs(r[3]) > 0.01 else 1.0
        jd_p_est -= diff / speed

    age_years = jd_p_est - birth_jd
    if age_years < 0 or age_years > max_years:
        return None

    # Convert from progressed JD to real calendar JD
    real_jd = birth_jd + age_years * 365.25
    return real_jd


# ── Result dataclasses ────────────────────────────────────────────────────────

@dataclass
class DirectedPoint:
    name:         str
    natal_lon:    float
    directed_lon: float
    sign:         str
    sign_lon:     float


@dataclass
class DirectedAspect:
    directed_name:  str
    directed_lon:   float
    natal_name:     str
    natal_lon:      float
    aspect_type:    int
    aspect_name:    str
    orb:            float
    max_orb:        float
    applying:       bool    # True = arc has not yet reached exact
    exact_jd:       float | None   # real calendar JD of exact hit (None if outside range)


@dataclass
class SolarArcResult:
    solar_arc:       float
    directed_points: list[DirectedPoint]
    aspects:         list[DirectedAspect]


# ── Signs ─────────────────────────────────────────────────────────────────────
_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


def _lon_to_sign(lon: float) -> tuple[str, float]:
    return _SIGNS[int(lon / 30) % 12], round(lon % 30, 4)


# ── Main calculation ───────────────────────────────────────────────────────────

def calc_solar_arc_directions(
    birth_jd: float,
    jd_prog: float,
    natal_points: list[tuple[str, float]],   # [(name, natal_lon), ...]
    max_orb: float = 2.0,
) -> SolarArcResult:
    """
    Compute solar arc directed chart and aspects.

    Parameters
    ----------
    birth_jd : float
        Julian Day of birth moment.
    jd_prog : float
        Progressed Julian Day (birth_jd + age_years).
    natal_points : list of (name, natal_lon)
        Natal positions to direct: 7 planets + ASC + MC.
    max_orb : float
        Maximum orb in degrees for directed-to-natal aspects (default 2°).

    Returns
    -------
    SolarArcResult
    """
    # ── Compute solar arc ──────────────────────────────────────────────────
    r_natal_sun, _ = swe.calc_ut(birth_jd, swe.SUN, _FLAGS)
    r_prog_sun,  _ = swe.calc_ut(jd_prog,  swe.SUN, _FLAGS)
    natal_sun_lon = r_natal_sun[0]
    solar_arc = (r_prog_sun[0] - natal_sun_lon) % 360.0

    # ── Build directed points ──────────────────────────────────────────────
    directed_points: list[DirectedPoint] = []
    for name, natal_lon in natal_points:
        dir_lon = (natal_lon + solar_arc) % 360.0
        sign, sign_lon = _lon_to_sign(dir_lon)
        directed_points.append(DirectedPoint(
            name=name,
            natal_lon=round(natal_lon, 4),
            directed_lon=round(dir_lon, 4),
            sign=sign,
            sign_lon=sign_lon,
        ))

    # ── Directed-to-natal aspects ──────────────────────────────────────────
    aspects: list[DirectedAspect] = []

    for dir_pt in directed_points:
        for nat_name, nat_lon in natal_points:
            # Skip self-to-self
            if dir_pt.name == nat_name:
                continue

            arc = _arc(dir_pt.directed_lon, nat_lon)
            max_o = min(max_orb, _combined_orb(dir_pt.name, nat_name))

            for asp_type, angle in ASPECT_ANGLES.items():
                orb = abs(arc - angle)
                if orb > max_o:
                    continue

                # Exact arc: how many degrees the solar arc needs to be
                # for this exact aspect (considering both sinister directions)
                # directed_lon = natal_lon_directed + arc_exact = nat_lon ± angle
                arc_exact_1 = (nat_lon + angle - dir_pt.natal_lon) % 360.0
                arc_exact_2 = (nat_lon - angle - dir_pt.natal_lon) % 360.0

                # Pick the one closest to the current solar arc
                def _proximity(a):
                    d = (a - solar_arc) % 360.0
                    return d if d <= 180 else d - 360

                p1, p2 = _proximity(arc_exact_1), _proximity(arc_exact_2)
                arc_exact = arc_exact_1 if abs(p1) <= abs(p2) else arc_exact_2

                # Applying: solar arc has not yet reached arc_exact
                # proximity < 0 → we haven't arrived yet (applying)
                proximity = _proximity(arc_exact)
                applying = proximity < 0

                # Find exact hit date
                exact_jd = _find_exact_hit_jd(birth_jd, natal_sun_lon, arc_exact)

                aspects.append(DirectedAspect(
                    directed_name=dir_pt.name,
                    directed_lon=dir_pt.directed_lon,
                    natal_name=nat_name,
                    natal_lon=round(nat_lon, 4),
                    aspect_type=asp_type,
                    aspect_name=ASPECT_NAMES[asp_type],
                    orb=round(orb, 4),
                    max_orb=round(max_o, 2),
                    applying=applying,
                    exact_jd=round(exact_jd, 6) if exact_jd is not None else None,
                ))

    # Sort tightest orb first
    aspects.sort(key=lambda a: a.orb)

    return SolarArcResult(
        solar_arc=round(solar_arc, 6),
        directed_points=directed_points,
        aspects=aspects,
    )
