"""
Circumambulations (Valens / Firmicus Maternus) — Hellenistic time-lord technique.

The significator (Ascending degree or sect light) "circumambulates" the zodiac
at the rate of its Oblique Ascension (equatorial degrees rising at birth latitude).

When the significator's accumulated OA reaches the OA of a promittor (planet body
or aspect point), that year of life is marked as significant.

Algorithm:
  1. Significators: ASC (primary) + sect light (Sun for day, Moon for night).
  2. Promittors: 7 classical planets × 5 Ptolemaic aspects (0°/60°/90°/120°/180°).
  3. Aspect point longitude = (planet_lon + aspect_angle) % 360 on the ecliptic.
  4. OA of a point = RA − Ascensional Difference at birth latitude.
  5. Arc (degrees of OA) = (OA_promittor − OA_significator) % 360.
  6. Age at event = arc years (Ptolemy key: 1° OA = 1 Julian year).

References:
  Vettius Valens, Anthology, Books II, IV (tr. Schmidt).
  Firmicus Maternus, Mathesis, Book II.
  Robert Hand, "Whole Sign Houses" (ascensional time background).

Planet IDs: 0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date as _date

import swisseph as swe

# ─── Constants ────────────────────────────────────────────────────────────────

_YEAR_DAYS = 365.25

_PLANET_NAMES: dict[int, str] = {
    0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
    4: "Mars", 5: "Jupiter", 6: "Saturn",
}

# Ptolemaic aspects: angle → name
ASPECTS: dict[int, str] = {
    0:   "Conjunction",
    60:  "Sextile",
    90:  "Square",
    120: "Trine",
    180: "Opposition",
}

# ── Valens extensions ─────────────────────────────────────────────────────────

# Minor (smallest) years per planet (Ptolemy/Paulus)
MINOR_YEARS: dict[int, float] = {
    0: 19.0,   # Sun
    1: 25.0,   # Moon
    2: 20.0,   # Mercury
    3:  8.0,   # Venus
    4: 15.0,   # Mars
    5: 12.0,   # Jupiter
    6: 30.0,   # Saturn
}
_MINOR_TOTAL = sum(MINOR_YEARS.values())   # 129

# Chaldean order: Saturn → Jupiter → Mars → Sun → Venus → Mercury → Moon
_CHALDEAN_ORDER = [6, 5, 4, 0, 3, 2, 1]

# Bonification: benefic planet + aspect
_BENEFICS  = {5: "Jupiter", 3: "Venus"}
_MALEFICS  = {4: "Mars",    6: "Saturn"}
_BONIF_ANGLES = {60, 120}    # sextile, trine
_MALT_ANGLES  = {90, 180}    # square, opposition
_BONIF_ORB = 10.0
_MALT_ORB  = 10.0

# Loosing of the bond: events within this many degrees of MC OA arc
_LOOSING_ORB = 3.0


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class DatePoint:
    jd: float
    year: int
    month: int
    day: int


@dataclass
class SubPeriod:
    """One of 7 sub-periods within a main circumambulation period."""
    planet_id:     int
    planet_name:   str
    start_date:    DatePoint
    end_date:      DatePoint
    duration_days: float


@dataclass
class CircumambulationEvent:
    significator: str       # "ASC" | "Sun" | "Moon"
    promittor_id: int       # 0–6 classical planet
    promittor_name: str
    aspect_angle: int       # 0, 60, 90, 120, 180
    aspect_name: str
    arc: float              # OA arc in degrees = age in years (Ptolemy key)
    age_years: float        # same as arc
    event_date: DatePoint   # birth_date + arc × 365.25 days
    is_past: bool           # event_date < today
    # Valens extensions
    is_loosing_of_bond: bool = False     # arc ≈ OA distance to natal MC
    bonification: str | None = None      # e.g. "Jupiter trine"
    maltreatment: str | None = None      # e.g. "Saturn square"
    sub_periods: list[SubPeriod] | None = None   # None unless include_sub_periods=True


@dataclass
class CircumambulationsResult:
    birth_jd: float
    significators: list[str]                     # ordered list of significator names
    events: list[CircumambulationEvent]          # sorted by (significator, arc)
    obliquity: float                             # true obliquity of ecliptic at birth
    armc: float                                  # Right Ascension of MC at birth (= OA of ASC)
    mc_lon: float = 0.0                          # natal MC ecliptic longitude
    mc_oa: float = 0.0                           # OA of natal MC (for reference)


# ─── Math helpers ─────────────────────────────────────────────────────────────

def _ra(ecl_lon: float, eps: float) -> float:
    """
    Right Ascension of an ecliptic point (with latitude 0) in degrees [0, 360).
    Formula: RA = atan2(sin(λ)·cos(ε), cos(λ))
    """
    lon_r = math.radians(ecl_lon)
    eps_r = math.radians(eps)
    return math.degrees(
        math.atan2(math.sin(lon_r) * math.cos(eps_r), math.cos(lon_r))
    ) % 360


def _dec(ecl_lon: float, eps: float) -> float:
    """
    Declination of an ecliptic point (with latitude 0) in degrees [-90, 90].
    Formula: dec = arcsin(sin(ε)·sin(λ))
    """
    lon_r = math.radians(ecl_lon)
    eps_r = math.radians(eps)
    return math.degrees(math.asin(math.sin(eps_r) * math.sin(lon_r)))


def _oa(ecl_lon: float, eps: float, geo_lat: float) -> float:
    """
    Oblique Ascension (OA) of an ecliptic point at geographic latitude φ.
    OA = RA − AD, where AD = arcsin(−tan(φ)·tan(dec)).
    Returns [0, 360).
    For circumpolar points (|AD_arg| > 1), returns RA as fallback.
    """
    ra = _ra(ecl_lon, eps)
    d  = _dec(ecl_lon, eps)
    phi_r = math.radians(geo_lat)
    ad_arg = -math.tan(phi_r) * math.tan(math.radians(d))
    if abs(ad_arg) > 1.0:
        return ra   # circumpolar: OA undefined, use RA
    ad = math.degrees(math.asin(ad_arg))
    return (ra - ad) % 360


# ─── Valens helpers ──────────────────────────────────────────────────────────

def _arc_between(lon_a: float, lon_b: float) -> float:
    """Shortest arc (0–180°) between two ecliptic longitudes."""
    d = abs(lon_a - lon_b) % 360
    return d if d <= 180 else 360 - d


def _check_bonification(planet_lons: dict[int, float], promittor_id: int) -> str | None:
    """
    Return 'Jupiter trine', 'Venus sextile', etc. if a benefic makes a
    trine or sextile to the promittor in the natal chart.  Returns None otherwise.
    """
    p_lon = planet_lons[promittor_id]
    for bid, bname in _BENEFICS.items():
        arc = _arc_between(planet_lons[bid], p_lon)
        for angle in _BONIF_ANGLES:
            if abs(arc - angle) <= _BONIF_ORB:
                asp = "trine" if angle == 120 else "sextile"
                return f"{bname} {asp}"
    return None


def _check_maltreatment(planet_lons: dict[int, float], promittor_id: int) -> str | None:
    """
    Return 'Saturn square', 'Mars opposition', etc. if a malefic makes a
    square or opposition to the promittor in the natal chart.  Returns None otherwise.
    """
    p_lon = planet_lons[promittor_id]
    for mid, mname in _MALEFICS.items():
        arc = _arc_between(planet_lons[mid], p_lon)
        for angle in _MALT_ANGLES:
            if abs(arc - angle) <= _MALT_ORB:
                asp = "square" if angle == 90 else "opposition"
                return f"{mname} {asp}"
    return None


def _build_sub_periods(start_jd: float, promittor_id: int) -> list[SubPeriod]:
    """
    Divide the main period (minor_years of promittor) into 7 sub-periods in
    Chaldean order starting from the promittor's position in that order.

    Duration formula (Valens):
        sub_duration_days = (minor_years[sub_planet] / MINOR_TOTAL)
                            × minor_years[promittor] × YEAR_DAYS
    Sub-periods sum to minor_years[promittor] × YEAR_DAYS (= major period length).
    """
    major_years = MINOR_YEARS[promittor_id]
    total_days  = major_years * _YEAR_DAYS

    start_idx = _CHALDEAN_ORDER.index(promittor_id)
    subs: list[SubPeriod] = []
    current_jd = start_jd

    for i in range(7):
        pid = _CHALDEAN_ORDER[(start_idx + i) % 7]
        dur_days = (MINOR_YEARS[pid] / _MINOR_TOTAL) * total_days
        end_jd = current_jd + dur_days
        y0, m0, d0, _ = swe.revjul(current_jd, swe.GREG_CAL)
        y1, m1, d1, _ = swe.revjul(end_jd,     swe.GREG_CAL)
        subs.append(SubPeriod(
            planet_id=pid,
            planet_name=_PLANET_NAMES[pid],
            start_date=DatePoint(jd=round(current_jd, 4),
                                 year=int(y0), month=int(m0), day=int(d0)),
            end_date=DatePoint(jd=round(end_jd, 4),
                               year=int(y1), month=int(m1), day=int(d1)),
            duration_days=round(dur_days, 2),
        ))
        current_jd = end_jd
    return subs


# ─── Core calculation ──────────────────────────────────────────────────────────

def calc_circumambulations(
    birth_jd: float,
    lat: float,
    lon: float,
    planet_lons: dict[int, float],
    day_chart: bool,
    current_jd: float | None = None,
    include_sub_periods: bool = False,
) -> CircumambulationsResult:
    """
    Compute circumambulation events for the birth chart.

    Significators: ASC + sect light (Sun for day charts, Moon for night charts).
    Promittors: 7 classical planets × 5 aspects.
    Arc = (OA(aspect_point) − OA(significator)) mod 360 degrees.
    Age at event = arc years (Ptolemy key).

    Valens extensions:
    - is_loosing_of_bond: event arc ≈ OA distance from sig to natal MC
    - bonification: benefic (Jupiter/Venus) trine/sextile to promittor natally
    - maltreatment: malefic (Mars/Saturn) square/opposition to promittor natally
    - sub_periods: 7 sub-divisions of the major period by Chaldean minor years

    Returns events sorted by (significator, arc ascending).
    """
    if current_jd is None:
        t = _date.today()
        current_jd = swe.julday(t.year, t.month, t.day, 12.0, swe.GREG_CAL)

    # True obliquity of ecliptic at birth
    eps_data, _ = swe.calc_ut(birth_jd, swe.ECL_NUT, swe.FLG_SWIEPH)
    eps = eps_data[0]

    # ARMC, ASC, MC from Swiss Ephemeris (Placidus for consistency)
    _, ascmc = swe.houses(birth_jd, lat, lon, b"P")
    armc   = ascmc[2]   # Right Ascension of MC = OA of ASC by definition
    mc_lon = ascmc[1]   # natal MC ecliptic longitude

    # OA of natal MC (for loosing of the bond detection)
    mc_oa = _oa(mc_lon, eps, lat)

    # Significators: ASC (OA = ARMC), sect light
    sig_light_id   = 0 if day_chart else 1
    sig_light_name = _PLANET_NAMES[sig_light_id]
    sig_light_oa   = _oa(planet_lons[sig_light_id], eps, lat)

    sig_oas: dict[str, float] = {
        "ASC": armc,
        sig_light_name: sig_light_oa,
    }
    significators = list(sig_oas.keys())

    # Loosing-of-bond arc per significator
    loosing_arcs: dict[str, float] = {
        sig_name: (mc_oa - sig_oa) % 360
        for sig_name, sig_oa in sig_oas.items()
    }

    # Build events
    events: list[CircumambulationEvent] = []

    for sig_name, sig_oa in sig_oas.items():
        loosing_arc = loosing_arcs[sig_name]
        for pid in range(7):
            p_lon = planet_lons[pid]
            for angle, asp_name in ASPECTS.items():
                asp_lon = (p_lon + angle) % 360
                asp_oa  = _oa(asp_lon, eps, lat)
                arc     = (asp_oa - sig_oa) % 360
                event_jd = birth_jd + arc * _YEAR_DAYS
                y, m, d, _ = swe.revjul(event_jd, swe.GREG_CAL)

                is_loosing = abs(arc - loosing_arc) < _LOOSING_ORB
                bonif      = _check_bonification(planet_lons, pid)
                malt       = _check_maltreatment(planet_lons, pid)
                subs       = _build_sub_periods(event_jd, pid) if include_sub_periods else None

                events.append(CircumambulationEvent(
                    significator=sig_name,
                    promittor_id=pid,
                    promittor_name=_PLANET_NAMES[pid],
                    aspect_angle=angle,
                    aspect_name=asp_name,
                    arc=round(arc, 4),
                    age_years=round(arc, 4),
                    event_date=DatePoint(
                        jd=round(event_jd, 4),
                        year=int(y), month=int(m), day=int(d),
                    ),
                    is_past=(event_jd < current_jd),
                    is_loosing_of_bond=is_loosing,
                    bonification=bonif,
                    maltreatment=malt,
                    sub_periods=subs,
                ))

    events.sort(key=lambda e: (e.significator, e.arc))

    return CircumambulationsResult(
        birth_jd=round(birth_jd, 4),
        significators=significators,
        events=events,
        obliquity=round(eps, 4),
        armc=round(armc, 4),
        mc_lon=round(mc_lon, 4),
        mc_oa=round(mc_oa, 4),
    )
