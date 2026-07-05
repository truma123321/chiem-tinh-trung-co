"""
Horary Judgment Framework — radicality assessment (Epic 9.1).

Evaluates whether a horary chart is "fit for judgment" by checking six classical
impediments. Returns a radicality verdict: Radical / Doubt / Non-radical.

Checks:
  1. early_asc    — ASC degree within sign < 3° (matter not yet ripe)
  2. late_asc     — ASC degree within sign > 27° (matter already concluded)
  3. saturn_h1    — Saturn in house 1 (querent's will is obstructed)
  4. saturn_h7    — Saturn in house 7 (astrologer or quesited is hindered)
  5. moon_voc     — Moon Void of Course (makes no more aspects before leaving sign)
  6. via_combusta — Moon between 15° Libra and 15° Scorpio (weakened Moon)

Radicality verdict:
  0 negative factors → Radical
  1 negative factor  → Doubt
  2+ negative factors → Non-radical

References:
  William Lilly, Christian Astrology, Book 1.
  Anthony Louis, Horary Astrology Plain & Simple.

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

_ASPECT_NAMES: dict[int, str] = {
    0: "Conjunction", 60: "Sextile", 90: "Square",
    120: "Trine", 180: "Opposition",
}

VIA_COMBUSTA_START = 195.0   # 15° Libra
VIA_COMBUSTA_END   = 225.0   # 15° Scorpio

EARLY_ASC_THRESHOLD = 3.0    # degree within sign
LATE_ASC_THRESHOLD  = 27.0   # degree within sign


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class HoraryCheck:
    factor:      str    # identifier: "early_asc" | "late_asc" | ...
    label:       str    # human-readable label
    present:     bool   # True = this impediment is active
    description: str    # detail / reason text


@dataclass
class HoraryResult:
    # Ascendant
    asc:        float
    asc_sign:   str
    asc_degree: float           # degrees within sign [0°, 30°)

    # Moon
    moon_lon:              float
    moon_sign:             str
    moon_voc:              bool
    next_aspect_planet:    str   | None   # None if Moon is VOC
    next_aspect_name:      str   | None
    next_aspect_orb:       float | None   # degrees to exact contact

    # Saturn
    saturn_lon:   float
    saturn_house: int     # 1–12

    # Via Combusta
    via_combusta: bool

    # Six checks
    checks: list[HoraryCheck]

    # Overall verdict
    radicality:     str   # "Radical" | "Doubt" | "Non-radical"
    negative_count: int   # number of checks that are present


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _find_house(lon: float, cusps: list[float]) -> int:
    """Return 1-based house number; cusps is a list of 12 cusp longitudes."""
    for h in range(12):
        c1 = cusps[h]
        c2 = cusps[(h + 1) % 12]
        if c2 > c1:
            if c1 <= lon < c2:
                return h + 1
        else:
            if lon >= c1 or lon < c2:
                return h + 1
    return 1


def _voc_and_next(
    moon_lon: float,
    planet_lons: dict[int, float],
) -> tuple[bool, str | None, str | None, float | None]:
    """
    Determine if Moon is Void of Course.

    Returns (voc, next_planet_name, next_aspect_name, degrees_to_exact).
    If voc: the last three items are None.
    """
    sign_idx = int(moon_lon / 30)
    sign_end = (sign_idx + 1) * 30.0   # e.g. Aries → 30.0, Pisces → 360.0

    best: tuple[float, int, int] | None = None   # (degrees_to_exact, pid, angle)

    for pid, p_lon in sorted(planet_lons.items()):
        if pid == 1:   # skip Moon itself
            continue
        seen: set[float] = set()
        for angle in (0, 60, 90, 120, 180):
            for contact in (
                round((p_lon - angle) % 360.0, 6),
                round((p_lon + angle) % 360.0, 6),
            ):
                if contact in seen:
                    continue
                seen.add(contact)
                if moon_lon < contact < sign_end:
                    deg = contact - moon_lon
                    if best is None or deg < best[0]:
                        best = (round(deg, 4), pid, angle)

    if best is None:
        return True, None, None, None
    _, pid, angle = best
    return False, _PLANET_NAMES[pid], _ASPECT_NAMES[angle], best[0]


# ─── Core calculation ──────────────────────────────────────────────────────────

def calc_horary(
    planet_lons:   dict[int, float],
    planet_speeds: dict[int, float],
    asc:           float,
    cusps:         list[float],   # 12 house cusp longitudes
) -> HoraryResult:
    """
    Assess horary chart radicality.

    planet_lons  : {planet_id: ecliptic_longitude}
    planet_speeds: {planet_id: daily motion in degrees}
    asc          : Ascendant longitude
    cusps        : 12 cusp longitudes (house 1 first)
    """
    # ── Ascendant ─────────────────────────────────────────────────────────────
    asc_degree = round(asc % 30.0, 4)
    asc_sign   = _SIGNS[int(asc / 30) % 12]

    # ── Moon ──────────────────────────────────────────────────────────────────
    moon_lon  = planet_lons[1]
    moon_sign = _SIGNS[int(moon_lon / 30) % 12]

    moon_voc, next_planet, next_aspect, next_orb = _voc_and_next(moon_lon, planet_lons)

    # ── Saturn ────────────────────────────────────────────────────────────────
    saturn_lon   = planet_lons[6]
    saturn_house = _find_house(saturn_lon, cusps)

    # ── Via Combusta ──────────────────────────────────────────────────────────
    via_combusta = VIA_COMBUSTA_START <= moon_lon <= VIA_COMBUSTA_END

    # ── Six checks ────────────────────────────────────────────────────────────
    checks: list[HoraryCheck] = [
        HoraryCheck(
            factor="early_asc",
            label="Early Ascending Degree",
            present=asc_degree < EARLY_ASC_THRESHOLD,
            description=(
                f"ASC at {asc_degree:.2f}° in {asc_sign} — "
                "< 3°: chart not yet developed, question premature"
                if asc_degree < EARLY_ASC_THRESHOLD
                else f"ASC at {asc_degree:.2f}° in {asc_sign} — within normal range"
            ),
        ),
        HoraryCheck(
            factor="late_asc",
            label="Late Ascending Degree",
            present=asc_degree > LATE_ASC_THRESHOLD,
            description=(
                f"ASC at {asc_degree:.2f}° in {asc_sign} — "
                "> 27°: matter already concluded or beyond remedy"
                if asc_degree > LATE_ASC_THRESHOLD
                else f"ASC at {asc_degree:.2f}° in {asc_sign} — within normal range"
            ),
        ),
        HoraryCheck(
            factor="saturn_h1",
            label="Saturn in House 1",
            present=saturn_house == 1,
            description=(
                f"Saturn in house 1 — querent's will is impeded or there is fear/doubt"
                if saturn_house == 1
                else f"Saturn in house {saturn_house}"
            ),
        ),
        HoraryCheck(
            factor="saturn_h7",
            label="Saturn in House 7",
            present=saturn_house == 7,
            description=(
                f"Saturn in house 7 — astrologer or quesited party is hindered"
                if saturn_house == 7
                else f"Saturn in house {saturn_house}"
            ),
        ),
        HoraryCheck(
            factor="moon_voc",
            label="Moon Void of Course",
            present=moon_voc,
            description=(
                f"Moon at {moon_lon:.2f}° {moon_sign} — VOC: no applying aspects "
                "before leaving sign; 'nothing will come of the matter'"
                if moon_voc
                else f"Moon applies to {next_planet} ({next_aspect}) "
                     f"in {next_orb:.2f}°"
            ),
        ),
        HoraryCheck(
            factor="via_combusta",
            label="Moon in Via Combusta",
            present=via_combusta,
            description=(
                f"Moon at {moon_lon:.2f}° — in Via Combusta "
                "(15° Libra – 15° Scorpio): Moon's judgment is weakened"
                if via_combusta
                else f"Moon at {moon_lon:.2f}° — outside Via Combusta"
            ),
        ),
    ]

    negative_count = sum(1 for c in checks if c.present)

    if negative_count == 0:
        radicality = "Radical"
    elif negative_count == 1:
        radicality = "Doubt"
    else:
        radicality = "Non-radical"

    return HoraryResult(
        asc=round(asc, 4),
        asc_sign=asc_sign,
        asc_degree=asc_degree,
        moon_lon=round(moon_lon, 4),
        moon_sign=moon_sign,
        moon_voc=moon_voc,
        next_aspect_planet=next_planet,
        next_aspect_name=next_aspect,
        next_aspect_orb=next_orb,
        saturn_lon=round(saturn_lon, 4),
        saturn_house=saturn_house,
        via_combusta=via_combusta,
        checks=checks,
        radicality=radicality,
        negative_count=negative_count,
    )
