"""
Decennials (Decades) — Paulus Alexandrinus time-lord system.

Each of the 7 classical planets rules a major period equal to its
"minor years" in the Chaldean order.  Total cycle = 129 years.

  Minor years: Sun=19, Moon=25, Saturn=30, Jupiter=12, Mars=15,
               Venus=8,  Mercury=20.  Sum = 129.

Sequence: Chaldean order —
  Saturn(30) → Jupiter(12) → Mars(15) → Sun(19) →
  Venus(8) → Mercury(20) → Moon(25) → (repeat)

Starting planet: lord of the birth planetary hour.
  - Day of week determines the day-ruler (traditional planetary days).
  - Planetary hours use seasonal (unequal) hours calculated from
    sunrise/sunset for the birth location.
  - Each of the 24 hours (12 day + 12 night) follows the Chaldean
    repeating sequence starting from the day ruler.

Sub-periods (within each major period):
  - Follow the same 7-planet Chaldean sequence starting from the
    major lord.
  - Each sub-period = (major_years × sub_planet_years) / 129 years.

References:
  Paulus Alexandrinus, Introduction to Astrology, ch. 25.
  Vettius Valens, Anthology, Book IV.

Planet IDs: 0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date as _date
import swisseph as swe

# ─── Constants ────────────────────────────────────────────────────────────────

# Chaldean order (planet IDs): Saturn → Jupiter → Mars → Sun → Venus → Mercury → Moon
_CHALDEAN = [6, 5, 4, 0, 3, 2, 1]

# Minor years keyed by planet ID
MINOR_YEARS: dict[int, int] = {
    0: 19,   # Sun
    1: 25,   # Moon
    2: 20,   # Mercury
    3: 8,    # Venus
    4: 15,   # Mars
    5: 12,   # Jupiter
    6: 30,   # Saturn
}
TOTAL_YEARS = sum(MINOR_YEARS.values())   # 129

# Day-of-week → day ruler (Python weekday(): 0=Mon … 6=Sun)
_DAY_RULER = {0: 1, 1: 4, 2: 2, 3: 5, 4: 3, 5: 6, 6: 0}
# Mon→Moon, Tue→Mars, Wed→Mercury, Thu→Jupiter, Fri→Venus, Sat→Saturn, Sun→Sun

_PLANET_NAMES = {
    0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
    4: "Mars", 5: "Jupiter", 6: "Saturn",
}

_YEAR_DAYS = 365.25


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class DatePoint:
    jd: float
    year: int
    month: int
    day: int


@dataclass
class DecennialSub:
    planet_id: int
    planet_name: str
    duration_years: float   # (major_years × sub_years) / 129
    start: DatePoint
    end: DatePoint
    is_current: bool


@dataclass
class DecennialPeriod:
    planet_id: int
    planet_name: str
    duration_years: int     # minor years (8–30)
    start: DatePoint
    end: DatePoint
    is_current: bool
    sub_periods: list[DecennialSub] = field(default_factory=list)


@dataclass
class DecennialsResult:
    birth_hour_lord_id: int
    birth_hour_lord_name: str
    periods: list[DecennialPeriod]      # all 7 major periods in the current cycle
    current_period: DecennialPeriod | None
    current_sub: DecennialSub | None
    birth_jd: float
    cycle_start_jd: float               # start of the current 129-year cycle


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _jd_to_dp(jd: float) -> DatePoint:
    y, m, d, _ = swe.revjul(jd, swe.GREG_CAL)
    return DatePoint(jd=round(jd, 4), year=int(y), month=int(m), day=int(d))


def _today_jd() -> float:
    t = _date.today()
    return swe.julday(t.year, t.month, t.day, 12.0, swe.GREG_CAL)


def _birth_hour_lord(birth_jd: float, lat: float, lon: float) -> int:
    """
    Return the Chaldean lord of the birth planetary hour.
    Uses seasonal (unequal) hours from sunrise/sunset.
    Falls back to equal clock hours if rise_trans fails.
    """
    y, m, d, frac = swe.revjul(birth_jd, swe.GREG_CAL)
    try:
        dt = _date(int(y), int(m), int(d))
    except ValueError:
        dt = _date(max(1, int(y)), int(m), int(d))
    weekday = dt.weekday()          # 0=Mon … 6=Sun
    day_ruler = _DAY_RULER[weekday]
    ruler_idx = _CHALDEAN.index(day_ruler)

    try:
        jd_day_start = swe.julday(int(y), int(m), int(d), 0.0, swe.GREG_CAL)
        geopos = (lon, lat, 0.0)

        _, trise = swe.rise_trans(
            jd_day_start, swe.SUN,
            swe.CALC_RISE | swe.BIT_DISC_CENTER, geopos,
        )
        sunrise = trise[0]

        _, tset = swe.rise_trans(
            jd_day_start, swe.SUN,
            swe.CALC_SET | swe.BIT_DISC_CENTER, geopos,
        )
        sunset = tset[0]

        if sunrise <= 0 or sunset <= 0 or sunset <= sunrise:
            raise ValueError("invalid rise/set")

        day_len   = sunset - sunrise
        night_len = 1.0 - day_len

        if sunrise <= birth_jd <= sunset:
            # Daytime planetary hour
            h = int((birth_jd - sunrise) / (day_len / 12.0))
        elif birth_jd < sunrise:
            # Before sunrise: nighttime (from the previous evening)
            prev_sunset = sunrise - night_len
            raw = (birth_jd - prev_sunset) / (night_len / 12.0)
            h = 12 + max(0, int(raw))
        else:
            # After sunset: nighttime
            raw = (birth_jd - sunset) / (night_len / 12.0)
            h = 12 + max(0, int(raw))

        h = min(h, 23)

    except Exception:
        # Fallback: equal clock hours from midnight UT
        # JD fraction 0.0 = noon, so add 0.5 to align to midnight
        h = int(((birth_jd + 0.5) % 1.0) * 24) % 24

    lord_idx = (ruler_idx + h) % 7
    return _CHALDEAN[lord_idx]


def _chaldean_sequence(start_pid: int) -> list[int]:
    """7-planet sequence starting at start_pid in Chaldean order."""
    idx = _CHALDEAN.index(start_pid)
    return [_CHALDEAN[(idx + i) % 7] for i in range(7)]


# ─── Core calculation ─────────────────────────────────────────────────────────

def calc_decennials(
    birth_jd: float,
    lat: float,
    lon: float,
    current_jd: float | None = None,
) -> DecennialsResult:
    """
    Compute Decennials for the current 129-year cycle.

    Returns all 7 major periods with their 7 sub-periods each,
    with current period and sub-period flagged.
    """
    if current_jd is None:
        current_jd = _today_jd()

    # ── Starting planet ───────────────────────────────────────────────────────
    start_pid = _birth_hour_lord(birth_jd, lat, lon)

    # ── Which 129-year cycle contains current_jd? ─────────────────────────────
    elapsed_years = (current_jd - birth_jd) / _YEAR_DAYS
    cycle_number  = int(elapsed_years / TOTAL_YEARS)
    cycle_start_jd = birth_jd + cycle_number * TOTAL_YEARS * _YEAR_DAYS

    # ── Build major periods ───────────────────────────────────────────────────
    major_sequence = _chaldean_sequence(start_pid)
    periods: list[DecennialPeriod] = []
    cursor = cycle_start_jd

    for pid in major_sequence:
        major_years  = MINOR_YEARS[pid]
        major_end_jd = cursor + major_years * _YEAR_DAYS
        is_major_cur = (cursor <= current_jd < major_end_jd)

        # ── Build sub-periods ─────────────────────────────────────────────────
        sub_sequence = _chaldean_sequence(pid)
        subs: list[DecennialSub] = []
        sub_cursor = cursor

        for spid in sub_sequence:
            sub_years = (major_years * MINOR_YEARS[spid]) / TOTAL_YEARS
            sub_end_jd = sub_cursor + sub_years * _YEAR_DAYS
            is_sub_cur = is_major_cur and (sub_cursor <= current_jd < sub_end_jd)

            subs.append(DecennialSub(
                planet_id=spid,
                planet_name=_PLANET_NAMES[spid],
                duration_years=round(sub_years, 4),
                start=_jd_to_dp(sub_cursor),
                end=_jd_to_dp(sub_end_jd),
                is_current=is_sub_cur,
            ))
            sub_cursor = sub_end_jd

        periods.append(DecennialPeriod(
            planet_id=pid,
            planet_name=_PLANET_NAMES[pid],
            duration_years=major_years,
            start=_jd_to_dp(cursor),
            end=_jd_to_dp(major_end_jd),
            is_current=is_major_cur,
            sub_periods=subs,
        ))
        cursor = major_end_jd

    current_period = next((p for p in periods if p.is_current), None)
    current_sub = None
    if current_period:
        current_sub = next((s for s in current_period.sub_periods if s.is_current), None)

    return DecennialsResult(
        birth_hour_lord_id=start_pid,
        birth_hour_lord_name=_PLANET_NAMES[start_pid],
        periods=periods,
        current_period=current_period,
        current_sub=current_sub,
        birth_jd=round(birth_jd, 4),
        cycle_start_jd=round(cycle_start_jd, 4),
    )
