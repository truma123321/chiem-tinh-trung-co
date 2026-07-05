"""
Solar Return — find the exact Julian Day when the Sun returns to its natal longitude.

Method: Newton-Raphson iteration on the solar longitude function.
  JD_new = JD_old − (sun_lon(JD_old) − natal_lon) / sun_speed(JD_old)

The Sun has no retrograde motion, so the function is monotone and N-R converges
in 3–5 iterations to sub-arcsecond (< 1 second of time) accuracy.
"""

from __future__ import annotations
import swisseph as swe

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED


def find_solar_return_jd(
    natal_sun_lon: float,
    return_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour_ut: float = 12.0,
) -> float:
    """
    Return the Julian Day (UT) of the solar return in `return_year`.

    Starting estimate: same calendar date as birth but in `return_year`.
    Converges to < 1e-8° accuracy (< 0.001 second of time) in ≤ 8 iterations.

    Args:
        natal_sun_lon  : ecliptic longitude of natal Sun (degrees)
        return_year    : calendar year of the desired solar return
        birth_month    : birth month (used as starting estimate)
        birth_day      : birth day (used as starting estimate)
        birth_hour_ut  : birth hour in UT (used as starting estimate)

    Returns:
        Julian Day (UT) of the exact solar return moment.
    """
    # Initial estimate: same date/time in the target year
    jd = swe.julday(return_year, birth_month, birth_day, birth_hour_ut, swe.GREG_CAL)

    for _ in range(20):
        r, _ = swe.calc_ut(jd, swe.SUN, _FLAGS)
        sun_lon = r[0]
        sun_speed = r[3]  # degrees/day (always positive for Sun, ~0.9856 °/day)

        diff = (sun_lon - natal_sun_lon) % 360.0
        if diff > 180.0:
            diff -= 360.0  # take the short path (-180 to +180)

        if abs(diff) < 1e-9:  # ~0.003 ms of time — far beyond needed accuracy
            break

        jd -= diff / sun_speed

    return jd


def jd_to_gregorian(jd: float) -> dict:
    """
    Convert a Julian Day to a Gregorian calendar dict with fractional seconds.

    Returns:
        {"year": int, "month": int, "day": int,
         "hour": int, "minute": int, "second": float, "utc_iso": str}
    """
    year, month, day, hour_frac = swe.revjul(jd, swe.GREG_CAL)
    hour = int(hour_frac)
    minute_frac = (hour_frac - hour) * 60
    minute = int(minute_frac)
    second = (minute_frac - minute) * 60

    utc_iso = (
        f"{year:04d}-{month:02d}-{day:02d}T"
        f"{hour:02d}:{minute:02d}:{second:06.3f}Z"
    )
    return {
        "year": year, "month": month, "day": day,
        "hour": hour, "minute": minute, "second": round(second, 3),
        "utc_iso": utc_iso,
    }
