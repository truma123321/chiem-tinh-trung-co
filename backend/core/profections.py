"""
Annual, Monthly, and Daily Profections — classical time-lord technique.

The Ascendant advances through the zodiac at exactly one sign (30°) per year
of life.  The sign it reaches each year activates that house's themes and
its domicile lord becomes the "Lord of the Year" (Hyleg Profectionis).

Monthly sub-division (Epic 7.1):
  ASC advances 2.5° per month (= 30° per year).
  profected_ASC = natal_ASC + age_months × 2.5°

Daily sub-division (Epic 7.1):
  ASC advances 30°/30.4375 ≈ 0.9856° per day.
  profected_ASC = natal_ASC + age_days × (30° / MONTH_DAYS)

Age 0  (birth year)  → 1st house  (ASC sign)
Age 1                → 2nd house
Age 2                → 3rd house
...
Age 11               → 12th house
Age 12               → 1st house again (cycle repeats every 12 years)

Profected ASC = (natal_ASC + age_years × 30°) % 360°

Activated planets: natal planets in the same sign as the profected ASC are
"activated" or "triggered" for that profection year.

Planet IDs: 0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
"""

from __future__ import annotations
from dataclasses import dataclass, field
import swisseph as swe
from datetime import date as _date
from core.dignities import DOMICILE, PLANET_NAMES

# ─── Constants ────────────────────────────────────────────────────────────────

YEAR_DAYS    = 365.25
MONTH_DAYS   = YEAR_DAYS / 12   # 30.4375 days per average month
DEG_PER_MON  = 2.5              # degrees per month (30° / 12)
DEG_PER_DAY  = 30.0 / MONTH_DAYS  # ≈ 0.9856°/day

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class DatePoint:
    jd: float
    year: int
    month: int
    day: int


@dataclass
class ProfectionYear:
    age: int                   # whole years of life at start of this year
    house: int                 # profected house number (1–12)
    profected_sign_idx: int    # 0=Aries … 11=Pisces
    profected_sign: str        # e.g. "Leo"
    profected_asc: float       # ecliptic longitude of profected ASC
    lord_id: int               # domicile ruler of profected sign
    lord_name: str
    start: DatePoint           # birthday when this profection year begins
    end: DatePoint             # next birthday
    is_current: bool           # True if this is the currently active year
    activated_planet_ids: list[int] = field(default_factory=list)


@dataclass
class ProfectionResult:
    current_age: int                # whole years completed at current_jd
    years: list[ProfectionYear]     # one full 12-year cycle (current cycle)
    current_year: ProfectionYear | None  # the active ProfectionYear
    birth_jd: float


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _jd_to_date(jd: float) -> DatePoint:
    y, m, d, _ = swe.revjul(jd, swe.GREG_CAL)
    return DatePoint(jd=round(jd, 4), year=y, month=m, day=int(d))


def _today_jd() -> float:
    t = _date.today()
    return swe.julday(t.year, t.month, t.day, 12.0, swe.GREG_CAL)


# ─── Core calculation ─────────────────────────────────────────────────────────

def calc_profections(
    birth_jd: float,
    asc: float,                  # natal Ascendant longitude
    planet_lons: dict,           # {0..6: ecliptic longitude}
    current_jd: float | None = None,
) -> ProfectionResult:
    """
    Compute annual profections for the current 12-year cycle.

    Returns the 12-entry table for the cycle containing current_jd,
    with the active year flagged and activated natal planets listed.
    """
    if current_jd is None:
        current_jd = _today_jd()

    elapsed_days  = current_jd - birth_jd
    elapsed_years = max(elapsed_days / YEAR_DAYS, 0.0)
    current_age   = int(elapsed_years)   # whole years completed

    # Which 12-year cycle contains current_age?
    cycle_number    = current_age // 12
    cycle_start_age = cycle_number * 12  # first age in this cycle

    years: list[ProfectionYear] = []

    for i in range(12):
        age      = cycle_start_age + i
        house    = i + 1                              # 1-based house number
        p_asc    = (asc + i * 30.0) % 360.0          # profected ASC longitude
        sign_idx = int(p_asc / 30.0) % 12

        lord_id   = DOMICILE[sign_idx]
        lord_name = PLANET_NAMES[lord_id]

        # Actual calendar dates: birthday at age N
        year_start_jd = birth_jd + age * YEAR_DAYS
        year_end_jd   = birth_jd + (age + 1) * YEAR_DAYS

        is_current = (age == current_age)

        # Activated planets: in the same sign as the profected ASC
        activated = []
        if is_current:
            activated = [
                pid for pid, lon in planet_lons.items()
                if int(lon / 30.0) % 12 == sign_idx
            ]

        years.append(ProfectionYear(
            age=age,
            house=house,
            profected_sign_idx=sign_idx,
            profected_sign=SIGNS[sign_idx],
            profected_asc=round(p_asc, 4),
            lord_id=lord_id,
            lord_name=lord_name,
            start=_jd_to_date(year_start_jd),
            end=_jd_to_date(year_end_jd),
            is_current=is_current,
            activated_planet_ids=activated,
        ))

    current_year = next((y for y in years if y.is_current), None)

    return ProfectionResult(
        current_age=current_age,
        years=years,
        current_year=current_year,
        birth_jd=round(birth_jd, 4),
    )


# ─── Monthly profection ───────────────────────────────────────────────────────

@dataclass
class MonthlyProfection:
    age_months: int          # total months of life at start of this month
    month_in_year: int       # 1–12 within the current annual year
    profected_asc: float     # natal_ASC + age_months × 2.5°
    profected_sign_idx: int
    profected_sign: str
    lord_id: int
    lord_name: str
    start: DatePoint
    end: DatePoint
    is_current: bool
    activated_planet_ids: list[int] = field(default_factory=list)


@dataclass
class MonthlyProfectionResult:
    total_months: int            # total months lived at current_jd
    total_years: int             # total full years lived
    month_in_year: int           # 1–12: which month within current annual year
    entries: list[MonthlyProfection]  # 12 entries for current annual year
    current_entry: MonthlyProfection | None
    birth_jd: float


def calc_monthly_profection(
    birth_jd: float,
    asc: float,
    planet_lons: dict,
    current_jd: float | None = None,
) -> MonthlyProfectionResult:
    """
    Compute monthly sub-profections for the current annual year.
    Returns 12 entries (one per month), with the active month flagged.
    """
    if current_jd is None:
        current_jd = _today_jd()

    elapsed_days  = max(current_jd - birth_jd, 0.0)
    total_months  = int(elapsed_days / MONTH_DAYS)
    total_years   = total_months // 12

    entries: list[MonthlyProfection] = []
    year_start_month = total_years * 12   # first month of the current annual year

    for m in range(12):
        age_m  = year_start_month + m
        p_asc  = (asc + age_m * DEG_PER_MON) % 360.0
        sign_i = int(p_asc / 30.0) % 12
        lord   = DOMICILE[sign_i]

        s_jd = birth_jd + age_m * MONTH_DAYS
        e_jd = birth_jd + (age_m + 1) * MONTH_DAYS
        is_cur = (age_m == total_months)

        activated = (
            [pid for pid, lon in planet_lons.items()
             if int(lon / 30.0) % 12 == sign_i]
            if is_cur else []
        )

        entries.append(MonthlyProfection(
            age_months=age_m,
            month_in_year=m + 1,
            profected_asc=round(p_asc, 4),
            profected_sign_idx=sign_i,
            profected_sign=SIGNS[sign_i],
            lord_id=lord,
            lord_name=PLANET_NAMES[lord],
            start=_jd_to_date(s_jd),
            end=_jd_to_date(e_jd),
            is_current=is_cur,
            activated_planet_ids=activated,
        ))

    current = next((e for e in entries if e.is_current), None)
    return MonthlyProfectionResult(
        total_months=total_months,
        total_years=total_years,
        month_in_year=(total_months % 12) + 1,
        entries=entries,
        current_entry=current,
        birth_jd=round(birth_jd, 4),
    )


# ─── Daily profection ─────────────────────────────────────────────────────────

@dataclass
class DailyProfection:
    age_days: int            # total days of life at start of this day
    day_in_month: int        # 1–31 within the current monthly period
    profected_asc: float     # natal_ASC + age_days × DEG_PER_DAY
    profected_sign_idx: int
    profected_sign: str
    lord_id: int
    lord_name: str
    start: DatePoint
    end: DatePoint
    is_current: bool
    activated_planet_ids: list[int] = field(default_factory=list)


@dataclass
class DailyProfectionResult:
    total_days: int              # total days lived at current_jd
    total_months: int            # approximate total months
    day_in_month: int            # 1-based day position in current monthly period
    entries: list[DailyProfection]  # 31 entries covering current monthly period
    current_entry: DailyProfection | None
    birth_jd: float


def calc_daily_profection(
    birth_jd: float,
    asc: float,
    planet_lons: dict,
    current_jd: float | None = None,
) -> DailyProfectionResult:
    """
    Compute daily sub-profections for the current monthly period (~31 days).
    Returns entries covering the current monthly window, with the active day flagged.
    """
    if current_jd is None:
        current_jd = _today_jd()

    elapsed_days  = max(current_jd - birth_jd, 0.0)
    total_days    = int(elapsed_days)
    total_months  = int(total_days / MONTH_DAYS)

    # Start day of the current monthly period
    month_start_day = int(total_months * MONTH_DAYS)

    entries: list[DailyProfection] = []

    for d in range(31):
        age_d  = month_start_day + d
        p_asc  = (asc + age_d * DEG_PER_DAY) % 360.0
        sign_i = int(p_asc / 30.0) % 12
        lord   = DOMICILE[sign_i]

        s_jd = birth_jd + age_d
        e_jd = birth_jd + age_d + 1
        is_cur = (age_d == total_days)

        activated = (
            [pid for pid, lon in planet_lons.items()
             if int(lon / 30.0) % 12 == sign_i]
            if is_cur else []
        )

        entries.append(DailyProfection(
            age_days=age_d,
            day_in_month=d + 1,
            profected_asc=round(p_asc, 4),
            profected_sign_idx=sign_i,
            profected_sign=SIGNS[sign_i],
            lord_id=lord,
            lord_name=PLANET_NAMES[lord],
            start=_jd_to_date(s_jd),
            end=_jd_to_date(e_jd),
            is_current=is_cur,
            activated_planet_ids=activated,
        ))

    current = next((e for e in entries if e.is_current), None)
    return DailyProfectionResult(
        total_days=total_days,
        total_months=total_months,
        day_in_month=(total_days - month_start_day) + 1,
        entries=entries,
        current_entry=current,
        birth_jd=round(birth_jd, 4),
    )
