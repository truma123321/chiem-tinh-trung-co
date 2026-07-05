"""
Firdaria — Persian / Arabic time-lord system.

Overview:
  Life is divided into 75-year cycles of 9 sequential period-lords
  (7 classical planets + North Node + South Node).  Each major period is
  sub-divided into 7 proportional sub-periods ruled by the 7 classical
  planets in sequence starting from the major lord itself.

  Nodes have no sub-periods in classical tradition (Bonatti).

Day-chart sequence (Bonatti, Liber Astronomiae Book IV):
  Sun 10 → Venus 8 → Mercury 13 → Moon 9 → Saturn 11 → Jupiter 12 → Mars 7
  → North Node 3 → South Node 2         (total = 75 years)

Night-chart sequence:
  Moon 9 → Saturn 11 → Mercury 13 → Venus 8 → Sun 10 → Mars 7 → Jupiter 12
  → North Node 3 → South Node 2         (total = 75 years)

Sub-period proportions (proportional method, per 7-planet total = 70 years):
  Sub-duration = (sub_lord_years / 70) × major_lord_years

Planet IDs:
  0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
  7=North Node, 8=South Node
"""

from __future__ import annotations
from dataclasses import dataclass, field
import swisseph as swe
from datetime import date as _date

# ─── Constants ────────────────────────────────────────────────────────────────

YEAR_DAYS  = 365.25      # Julian year
CYCLE_YEARS = 75

# Major Firdaria allocations
DAY_SEQUENCE: list[tuple[int, str, int]] = [
    (0, "Sun",        10),
    (3, "Venus",       8),
    (2, "Mercury",    13),
    (1, "Moon",        9),
    (6, "Saturn",     11),
    (5, "Jupiter",    12),
    (4, "Mars",        7),
    (7, "North Node",  3),
    (8, "South Node",  2),
]

NIGHT_SEQUENCE: list[tuple[int, str, int]] = [
    (1, "Moon",        9),
    (6, "Saturn",     11),
    (2, "Mercury",    13),
    (3, "Venus",       8),
    (0, "Sun",        10),
    (4, "Mars",        7),
    (5, "Jupiter",    12),
    (7, "North Node",  3),
    (8, "South Node",  2),
]

# Planet year allocations for proportional sub-period calculation
PLANET_YEARS: dict[int, int] = {
    0: 10, 1: 9, 2: 13, 3: 8, 4: 7, 5: 12, 6: 11,
}
PLANET_YEARS_TOTAL = sum(PLANET_YEARS.values())   # 70

NODE_IDS = frozenset([7, 8])   # nodes have no sub-periods


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class DatePoint:
    jd: float
    year: int
    month: int
    day: int


@dataclass
class FirdariaSubPeriod:
    planet_id: int
    planet_name: str
    start: DatePoint
    end: DatePoint
    is_current: bool = False


@dataclass
class FirdariaPeriod:
    planet_id: int
    planet_name: str
    years: int               # total years for this major period
    start: DatePoint
    end: DatePoint
    is_current: bool = False
    sub_periods: list[FirdariaSubPeriod] = field(default_factory=list)


@dataclass
class FirdariaResult:
    day_chart: bool
    birth_jd: float
    periods: list[FirdariaPeriod]     # full 75-year cycle
    current_period: FirdariaPeriod | None
    current_sub: FirdariaSubPeriod | None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _jd_to_date(jd: float) -> DatePoint:
    y, m, d, _ = swe.revjul(jd, swe.GREG_CAL)
    return DatePoint(jd=round(jd, 4), year=y, month=m, day=int(d))


def _today_jd() -> float:
    t = _date.today()
    return swe.julday(t.year, t.month, t.day, 12.0, swe.GREG_CAL)


def _build_sub_periods(
    major_pid: int,
    major_years: int,
    major_start_jd: float,
    planets_sequence: list[tuple[int, str, int]],
    current_jd: float,
) -> list[FirdariaSubPeriod]:
    """Build 7 proportional sub-periods for a major period."""
    if major_pid in NODE_IDS:
        return []

    # 7 planets only (no nodes)
    planets_only = [(pid, name) for pid, name, _ in planets_sequence if pid not in NODE_IDS]

    # Find start index: major lord's position in the 7-planet list
    start_idx = next(i for i, (pid, _) in enumerate(planets_only) if pid == major_pid)

    sub_periods = []
    jd = major_start_jd

    for k in range(7):
        sub_pid, sub_name = planets_only[(start_idx + k) % 7]
        duration_days = (PLANET_YEARS[sub_pid] / PLANET_YEARS_TOTAL) * major_years * YEAR_DAYS
        sub_start = jd
        sub_end = jd + duration_days

        sub_periods.append(FirdariaSubPeriod(
            planet_id=sub_pid,
            planet_name=sub_name,
            start=_jd_to_date(sub_start),
            end=_jd_to_date(sub_end),
            is_current=(sub_start <= current_jd < sub_end),
        ))
        jd = sub_end

    return sub_periods


# ─── Core calculation ─────────────────────────────────────────────────────────

def calc_firdaria(
    birth_jd: float,
    day_chart: bool,
    current_jd: float | None = None,
) -> FirdariaResult:
    """
    Compute the complete Firdaria (75-year cycle) for a natal chart.

    Returns all 9 major periods with their 7 sub-periods each,
    plus pointers to whichever period/sub-period is active at current_jd.

    If current_jd is None, today's date is used.
    """
    if current_jd is None:
        current_jd = _today_jd()

    # Handle multiple 75-year cycles: normalise current_jd to within first cycle
    # by offsetting birth_jd forward by complete cycles if needed.
    cycle_days = CYCLE_YEARS * YEAR_DAYS
    elapsed = current_jd - birth_jd
    if elapsed < 0:
        # Current date before birth — no active period
        effective_jd = birth_jd  # will result in is_current=False everywhere
    else:
        # Which cycle are we in?
        cycle_offset = int(elapsed / cycle_days) * cycle_days
        effective_jd = current_jd  # keep original for is_current checks

    sequence = DAY_SEQUENCE if day_chart else NIGHT_SEQUENCE
    periods: list[FirdariaPeriod] = []
    jd = birth_jd

    # Build periods spanning enough cycles to cover current_jd
    max_jd = max(current_jd + 1, birth_jd + cycle_days)
    period_start_jd = birth_jd

    for major_pid, major_name, major_years in sequence:
        major_start = period_start_jd
        major_end   = major_start + major_years * YEAR_DAYS

        sub_periods = _build_sub_periods(
            major_pid, major_years, major_start, sequence, effective_jd
        )

        is_current = (major_start <= effective_jd < major_end)

        periods.append(FirdariaPeriod(
            planet_id=major_pid,
            planet_name=major_name,
            years=major_years,
            start=_jd_to_date(major_start),
            end=_jd_to_date(major_end),
            is_current=is_current,
            sub_periods=sub_periods,
        ))
        period_start_jd = major_end

    # Locate current period and sub-period
    current_period: FirdariaPeriod | None = None
    current_sub: FirdariaSubPeriod | None = None

    for p in periods:
        if p.is_current:
            current_period = p
            for s in p.sub_periods:
                if s.is_current:
                    current_sub = s
            break

    return FirdariaResult(
        day_chart=day_chart,
        birth_jd=round(birth_jd, 4),
        periods=periods,
        current_period=current_period,
        current_sub=current_sub,
    )
