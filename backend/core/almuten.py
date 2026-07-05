"""
Almuten Figuris (Lord of the Geniture) — ported from Morinus almutens.py

Method: Bonatti / Zoller
  For each of the 7 classical planets, sum the essential dignity score
  (domicile=5, exaltation=4, triplicity=3, term=2, face=1) evaluated at
  5 significator points:
    1. Sun longitude
    2. Moon longitude
    3. ASC longitude
    4. Lot of Fortune longitude
    5. Prenatal Syzygy (last New or Full Moon) longitude

  Planet with highest total = Almuten Figuris.

Lot of Fortune (Bonatti/classical):
  Day chart:  (ASC + Moon - Sun)  % 360
  Night chart: (ASC + Sun - Moon) % 360

Prenatal Syzygy:
  Last New Moon (conjunction) or Full Moon (opposition) before birth.
  The longitude used is the Moon's position at that moment.
"""

import swisseph as swe
from dataclasses import dataclass

from core.dignities import calc_dignities, PLANET_NAMES


# ─── Lot of Fortune ───────────────────────────────────────────────────────

def calc_lot_of_fortune(asc: float, moon_lon: float, sun_lon: float, daytime: bool) -> float:
    """
    Bonatti formula:
      Day:   ASC + Moon - Sun
      Night: ASC + Sun  - Moon
    Result normalised to [0, 360).
    """
    if daytime:
        lon = asc + moon_lon - sun_lon
    else:
        lon = asc + sun_lon - moon_lon
    return lon % 360


# ─── Prenatal Syzygy ──────────────────────────────────────────────────────

def _phase_angle(jd: float) -> float:
    """Moon - Sun ecliptic longitude difference, 0–360°."""
    FLAGS = swe.FLG_SWIEPH
    sun, _ = swe.calc_ut(jd, swe.SUN, FLAGS)
    moon, _ = swe.calc_ut(jd, swe.MOON, FLAGS)
    return (moon[0] - sun[0]) % 360


def _bisect_phase(t_lo: float, t_hi: float, target: float) -> float:
    """Binary search: find t in [t_lo, t_hi] where phase_angle == target."""
    for _ in range(60):
        if t_hi - t_lo < 1e-7:
            break
        t_mid = (t_lo + t_hi) / 2
        p_lo  = _phase_angle(t_lo)
        p_mid = _phase_angle(t_mid)
        if (p_lo - target) * (p_mid - target) <= 0:
            t_hi = t_mid
        else:
            t_lo = t_mid
    return (t_lo + t_hi) / 2


def _bisect_wrap(t_lo: float, t_hi: float) -> float:
    """Binary search for 0°/360° crossing (New Moon).
    At t_lo: phase is large (>300°); at t_hi: phase is small (<60°).
    """
    def signed(t: float) -> float:
        p = _phase_angle(t)
        return p - 360 if p > 180 else p

    for _ in range(60):
        if t_hi - t_lo < 1e-7:
            break
        t_mid = (t_lo + t_hi) / 2
        s_lo  = signed(t_lo)
        s_mid = signed(t_mid)
        if s_lo * s_mid <= 0:
            t_hi = t_mid
        else:
            t_lo = t_mid
    return (t_lo + t_hi) / 2


def calc_prenatal_syzygy(jd: float) -> tuple[float, bool]:
    """
    Find the last New Moon (conjunction) or Full Moon (opposition) before jd.
    Returns (moon_longitude_at_syzygy, is_new_moon).

    Searches backwards by 1-hour steps (max 30 days).
    """
    FLAGS   = swe.FLG_SWIEPH
    STEP    = 1.0 / 24          # 1 hour in Julian Days
    MAX_ITR = 30 * 24           # 30 days × 24 hours

    prev_ph = _phase_angle(jd)
    t       = jd - STEP

    for _ in range(MAX_ITR):
        cur_ph = _phase_angle(t)

        # Full Moon crossing going backward: phase falls from just-above-180 to just-below-180
        if prev_ph > 180.0 and cur_ph < 180.0:
            t_syz = _bisect_phase(t, t + STEP, 180.0)
            moon, _ = swe.calc_ut(t_syz, swe.MOON, FLAGS)
            return moon[0], False

        # New Moon crossing going backward: phase wraps from ~360 back through 0
        if prev_ph < 20.0 and cur_ph > 340.0:
            t_syz = _bisect_wrap(t, t + STEP)
            moon, _ = swe.calc_ut(t_syz, swe.MOON, FLAGS)
            return moon[0], True

        prev_ph = cur_ph
        t      -= STEP

    # Fallback: return current Moon position (should never happen in practice)
    moon, _ = swe.calc_ut(jd, swe.MOON, FLAGS)
    return moon[0], True


# ─── Almuten score ────────────────────────────────────────────────────────

@dataclass
class AlmutenPoint:
    name: str
    lon: float
    scores: dict[str, int]   # planet_name → score at this point


@dataclass
class AlmutenResult:
    winner: str              # planet_name with highest total
    winner_id: int
    total_scores: dict[str, int]   # planet_name → total across all 5 points
    points: list[AlmutenPoint]     # detail per significator
    lot_of_fortune: float
    syzygy_lon: float
    syzygy_is_new_moon: bool
    dead_heat: bool          # True if 2+ planets share the highest score


def calc_almuten(
    planet_lons: dict[int, float],   # {planet_id: longitude} for 0–6
    asc: float,
    sun_lon: float,
    moon_lon: float,
    daytime: bool,
    jd: float,
) -> AlmutenResult:
    """
    Calculate Almuten Figuris.

    planet_lons: {0: sun_lon, 1: moon_lon, ..., 6: saturn_lon}
    """
    lof = calc_lot_of_fortune(asc, moon_lon, sun_lon, daytime)
    syz_lon, syz_is_new = calc_prenatal_syzygy(jd)

    significators = [
        ("Sun",     sun_lon),
        ("Moon",    moon_lon),
        ("ASC",     asc),
        ("Fortune", lof),
        ("Syzygy",  syz_lon),
    ]

    # Accumulate scores
    totals: dict[int, int] = {pid: 0 for pid in range(7)}
    points: list[AlmutenPoint] = []

    for sig_name, sig_lon in significators:
        pt_scores: dict[str, int] = {}
        for pid in range(7):
            d = calc_dignities(pid, sig_lon, daytime)
            totals[pid] += d.score
            pt_scores[PLANET_NAMES[pid]] = d.score
        points.append(AlmutenPoint(name=sig_name, lon=round(sig_lon, 4), scores=pt_scores))

    # Find winner
    max_score = max(totals.values())
    winners   = [pid for pid, s in totals.items() if s == max_score]
    dead_heat = len(winners) > 1
    winner_id = winners[0]

    return AlmutenResult(
        winner=PLANET_NAMES[winner_id],
        winner_id=winner_id,
        total_scores={PLANET_NAMES[pid]: totals[pid] for pid in range(7)},
        points=points,
        lot_of_fortune=round(lof, 4),
        syzygy_lon=round(syz_lon, 4),
        syzygy_is_new_moon=syz_is_new,
        dead_heat=dead_heat,
    )
