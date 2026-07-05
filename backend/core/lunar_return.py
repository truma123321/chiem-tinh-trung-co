"""
Lunar Return — find all moments in a year when the Moon returns to its natal longitude.

The Moon completes one sidereal revolution in ~27.32158 days, giving 12–13 returns/year.

Method: Newton-Raphson iteration on the lunar longitude function.
  JD_new = JD_old − (moon_lon(JD_old) − natal_lon) / moon_speed(JD_old)

Moon speed ~13.2 °/day → converges in 3–5 iterations to sub-arcsecond accuracy.
"""

from __future__ import annotations
import swisseph as swe

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
LUNAR_SIDEREAL_PERIOD = 27.32158   # days — used as step between search windows


def find_next_lunar_return(natal_moon_lon: float, after_jd: float) -> float:
    """
    Find the next moment AFTER `after_jd` when Moon = `natal_moon_lon`.

    Uses a forward arc estimate to seed N-R so the result is always
    strictly after the start point.
    """
    # Current Moon position at start
    r, _ = swe.calc_ut(after_jd, swe.MOON, _FLAGS)
    current_lon  = r[0]
    current_speed = abs(r[3]) or 13.2   # fallback if speed missing

    # Forward arc: degrees Moon needs to travel to reach natal_moon_lon
    forward_arc = (natal_moon_lon - current_lon) % 360.0
    if forward_arc < 1e-6:
        forward_arc = 360.0   # already at target — skip ahead one full revolution

    jd_est = after_jd + forward_arc / current_speed

    # Newton-Raphson refinement
    for _ in range(20):
        r, _ = swe.calc_ut(jd_est, swe.MOON, _FLAGS)
        moon_lon  = r[0]
        moon_speed = r[3]
        if moon_speed <= 0:
            moon_speed = 13.2   # Moon rarely retrogrades; use mean speed fallback

        diff = (moon_lon - natal_moon_lon) % 360.0
        if diff > 180.0:
            diff -= 360.0

        if abs(diff) < 1e-9:
            break
        jd_est -= diff / moon_speed

    # Safety: result must be strictly after the search start
    if jd_est <= after_jd:
        jd_est = after_jd + LUNAR_SIDEREAL_PERIOD
        for _ in range(10):
            r, _ = swe.calc_ut(jd_est, swe.MOON, _FLAGS)
            moon_lon  = r[0]
            moon_speed = r[3] or 13.2
            diff = (moon_lon - natal_moon_lon) % 360.0
            if diff > 180.0:
                diff -= 360.0
            if abs(diff) < 1e-9:
                break
            jd_est -= diff / moon_speed

    return jd_est


def find_all_lunar_returns_in_year(natal_moon_lon: float, year: int) -> list[float]:
    """
    Return sorted list of Julian Days for every lunar return in `year`.

    Typically 12–13 returns (one per sidereal month ≈ 27.32 days).
    """
    jd_year_start = swe.julday(year,     1,  1, 0.0, swe.GREG_CAL)
    jd_year_end   = swe.julday(year + 1, 1,  1, 0.0, swe.GREG_CAL)

    returns: list[float] = []

    # Start the search one period before the year so we don't miss a return near Jan 1
    jd_cursor = jd_year_start - LUNAR_SIDEREAL_PERIOD

    while True:
        jd_ret = find_next_lunar_return(natal_moon_lon, jd_cursor)

        if jd_ret >= jd_year_end:
            break

        if jd_ret >= jd_year_start:
            returns.append(jd_ret)

        # Advance cursor past this return to find the next one
        jd_cursor = jd_ret + LUNAR_SIDEREAL_PERIOD * 0.9

    return sorted(returns)
