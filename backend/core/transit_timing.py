"""
Transit Timing (Epic 5.2).

Finds all exact transit-to-natal aspect hits in a date range by scanning
planet longitudes and using Newton-Raphson to pinpoint zero-orb moments.
Also finds retrograde station events near natal planets.

Algorithm
---------
For each (transit planet, natal planet, aspect angle):
  Two target longitudes exist — sinister (natal + angle) and dexter
  (natal - angle), except for conjunction (one target) and opposition
  (one target, since +180 ≡ −180).

  Scan the date range in planet-specific day steps, tracking sign changes
  of  g(jd) = (planet_lon(jd) - target_lon + 180) % 360 − 180.
  Each sign change locates a root; N-R refines it to < 0.001°.

Stations
--------
Scan speed sign changes for retrograde-capable planets. Report any
station falling within `station_orb` degrees of a natal planet.
"""

from __future__ import annotations
from dataclasses import dataclass
import swisseph as swe

from core.transits import ASPECT_ANGLES, ASPECT_NAMES, _arc

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

# Scan step size per planet (days).  Smaller = more accurate, slower.
_STEP: dict[int, float] = {
    swe.MOON:      0.5,
    swe.SUN:       1.0,
    swe.MERCURY:   1.0,
    swe.VENUS:     1.0,
    swe.MARS:      2.0,
    swe.JUPITER:   5.0,
    swe.SATURN:    5.0,
    swe.TRUE_NODE: 1.0,
    swe.MEAN_NODE: 1.0,
    swe.URANUS:   10.0,
    swe.NEPTUNE:  10.0,
    swe.PLUTO:    10.0,
    swe.CHIRON:    7.0,
}
_DEFAULT_STEP = 3.0

# Planets that never station (Sun and Moon don't retrograde)
_NO_STATION = {swe.SUN, swe.MOON}


# ── Low-level helpers ──────────────────────────────────────────────────────────

def _g(lon: float, target: float) -> float:
    """Signed angular difference (lon − target) in (−180, +180]."""
    return (lon - target + 180.0) % 360.0 - 180.0


def _nr_refine(jd_lo: float, jd_hi: float, pid: int, target_lon: float) -> float | None:
    """
    Newton-Raphson: find JD where planet pid is exactly at target_lon.
    Returns None if convergence fails (residual > 0.01°).
    """
    jd_est = (jd_lo + jd_hi) / 2.0
    for _ in range(30):
        r, _ = swe.calc_ut(jd_est, pid, _FLAGS)
        diff = _g(r[0], target_lon)
        if abs(diff) < 1e-8:
            break
        speed = r[3] if abs(r[3]) > 1e-4 else 1e-4
        jd_est -= diff / speed
        # Prevent runaway divergence
        jd_est = max(jd_lo - 5.0, min(jd_hi + 5.0, jd_est))
    r_check, _ = swe.calc_ut(jd_est, pid, _FLAGS)
    if abs(_g(r_check[0], target_lon)) > 0.01:
        return None
    return round(jd_est, 6)


def _find_hits_for_target(
    start_jd: float,
    end_jd: float,
    pid: int,
    target_lon: float,
    step: float,
) -> list[float]:
    """Return all JDs in [start_jd, end_jd] where planet pid is at target_lon."""
    hits: list[float] = []
    r, _ = swe.calc_ut(start_jd, pid, _FLAGS)
    g_prev = _g(r[0], target_lon)
    jd = start_jd

    while jd < end_jd:
        jd_next = min(jd + step, end_jd)
        r_next, _ = swe.calc_ut(jd_next, pid, _FLAGS)
        g_next = _g(r_next[0], target_lon)

        if g_prev * g_next < 0:
            jd_root = _nr_refine(jd, jd_next, pid, target_lon)
            if jd_root is not None and start_jd <= jd_root <= end_jd:
                if not hits or jd_root - hits[-1] > 0.5:   # skip near-duplicates
                    hits.append(jd_root)

        g_prev = g_next
        jd = jd_next

    return hits


def _bisect_station(jd1: float, jd2: float, pid: int) -> float:
    """Binary search for the zero-speed moment between jd1 and jd2."""
    r1, _ = swe.calc_ut(jd1, pid, _FLAGS)
    spd1 = r1[3]
    for _ in range(50):
        jd_mid = (jd1 + jd2) / 2.0
        r_mid, _ = swe.calc_ut(jd_mid, pid, _FLAGS)
        if spd1 * r_mid[3] < 0:
            jd2 = jd_mid
        else:
            jd1 = jd_mid
            spd1 = r_mid[3]
        if jd2 - jd1 < 1e-6:
            break
    return (jd1 + jd2) / 2.0


def _find_stations(
    start_jd: float,
    end_jd: float,
    pid: int,
    step: float,
) -> list[tuple[float, str, float]]:
    """
    Return (jd, station_type, lon) for every station of pid in [start_jd, end_jd].
    station_type is "SR" (goes retrograde) or "SD" (resumes direct).
    """
    if pid in _NO_STATION:
        return []

    results: list[tuple[float, str, float]] = []
    r, _ = swe.calc_ut(start_jd, pid, _FLAGS)
    spd_prev = r[3]
    jd = start_jd

    while jd < end_jd:
        jd_next = min(jd + step, end_jd)
        r_next, _ = swe.calc_ut(jd_next, pid, _FLAGS)
        spd_next = r_next[3]

        if spd_prev * spd_next < 0:
            jd_stat = _bisect_station(jd, jd_next, pid)
            r_stat, _ = swe.calc_ut(jd_stat, pid, _FLAGS)
            stype = "SR" if spd_prev > 0 else "SD"
            results.append((round(jd_stat, 6), stype, round(r_stat[0], 4)))

        spd_prev = spd_next
        jd = jd_next

    return results


# ── Result dataclasses ─────────────────────────────────────────────────────────

@dataclass
class ExactHit:
    transit_planet_id:   int
    transit_planet_name: str
    natal_planet_id:     int
    natal_planet_name:   str
    natal_lon:           float
    aspect_type:         int
    aspect_name:         str
    exact_jd:            float
    exact_date:          str    # YYYY-MM-DD
    hit_number:          int    # ordinal within this (planet, natal, aspect) group
    total_hits:          int    # total in the date range for this group
    retrograde_at_exact: bool


@dataclass
class StationEvent:
    transit_planet_id:    int
    transit_planet_name:  str
    station_jd:           float
    station_date:         str
    station_type:         str   # "SR" or "SD"
    station_lon:          float
    nearest_natal_planet: str | None
    nearest_natal_lon:    float | None
    orb_to_nearest:       float | None


@dataclass
class TransitTimingResult:
    exact_hits: list[ExactHit]
    stations:   list[StationEvent]


# ── Utility ───────────────────────────────────────────────────────────────────

def _jd_to_date(jd: float) -> str:
    y, m, d, _ = swe.revjul(jd, swe.GREG_CAL)
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


# ── Main entry point ───────────────────────────────────────────────────────────

def calc_transit_timing(
    start_jd: float,
    end_jd: float,
    transit_planet_ids: list[tuple[int, str]],   # [(pid, name), ...]
    natal_planets,                                # list[PlanetPosition]
    station_orb: float = 1.0,
    include_stations: bool = True,
) -> TransitTimingResult:
    """
    Find all exact transit-to-natal aspect hits in [start_jd, end_jd]
    and station events of transit planets near natal planets.

    Parameters
    ----------
    start_jd, end_jd
        Julian Day range (inclusive).
    transit_planet_ids
        List of (planet_id, name) pairs to evaluate as transit planets.
    natal_planets
        Natal planet positions (PlanetPosition objects, 7 traditional).
    station_orb
        Max orb (°) to a natal planet for a station to be included.
    include_stations
        When False, skip station computation.
    """
    trad_ids = {0, 1, 2, 3, 4, 5, 6}

    # ── Exact hits ──────────────────────────────────────────────────────────
    # Group by (transit_pid, natal_pid, asp_type) → list of exact JDs
    hits_by_group: dict[tuple[int, int, int], list[float]] = {}
    meta_by_group: dict[tuple[int, int, int], tuple] = {}
    # meta tuple: (tr_name, na_name, na_lon, asp_name)

    for pid, tr_name in transit_planet_ids:
        step = _STEP.get(pid, _DEFAULT_STEP)

        for na in natal_planets:
            if na.id not in trad_ids:
                continue

            for asp_type, angle in ASPECT_ANGLES.items():
                # sinister target; add dexter only for 0 < angle < 180
                targets = [(na.lon + angle) % 360.0]
                if 0.0 < angle < 180.0:
                    targets.append((na.lon - angle) % 360.0)

                all_jds: list[float] = []
                for tgt in targets:
                    all_jds.extend(
                        _find_hits_for_target(start_jd, end_jd, pid, tgt, step)
                    )

                # Sort + dedup (hits from sinister and dexter targets may interleave)
                all_jds.sort()
                deduped: list[float] = []
                for h in all_jds:
                    if not deduped or h - deduped[-1] > 0.5:
                        deduped.append(h)

                if deduped:
                    key = (pid, na.id, asp_type)
                    hits_by_group[key] = deduped
                    meta_by_group[key] = (tr_name, na.name, round(na.lon, 4), ASPECT_NAMES[asp_type])

    # Materialise ExactHit objects
    exact_hits: list[ExactHit] = []
    for (pid, na_id, asp_type), jds in hits_by_group.items():
        tr_name, na_name, na_lon, asp_name = meta_by_group[(pid, na_id, asp_type)]
        total = len(jds)
        for i, jd in enumerate(jds, 1):
            r, _ = swe.calc_ut(jd, pid, _FLAGS)
            exact_hits.append(ExactHit(
                transit_planet_id=pid,
                transit_planet_name=tr_name,
                natal_planet_id=na_id,
                natal_planet_name=na_name,
                natal_lon=na_lon,
                aspect_type=asp_type,
                aspect_name=asp_name,
                exact_jd=jd,
                exact_date=_jd_to_date(jd),
                hit_number=i,
                total_hits=total,
                retrograde_at_exact=(r[3] < 0),
            ))

    exact_hits.sort(key=lambda h: h.exact_jd)

    # ── Stations ────────────────────────────────────────────────────────────
    stations: list[StationEvent] = []
    if include_stations:
        for pid, tr_name in transit_planet_ids:
            step = _STEP.get(pid, _DEFAULT_STEP)
            for jd_stat, stype, stat_lon in _find_stations(start_jd, end_jd, pid, step):
                # Find nearest natal planet
                nearest_name: str | None = None
                nearest_lon:  float | None = None
                nearest_orb:  float | None = None

                for na in natal_planets:
                    if na.id not in trad_ids:
                        continue
                    orb = _arc(stat_lon, na.lon)
                    if nearest_orb is None or orb < nearest_orb:
                        nearest_orb = round(orb, 4)
                        nearest_name = na.name
                        nearest_lon = round(na.lon, 4)

                # Only include stations within station_orb of any natal planet
                if nearest_orb is not None and nearest_orb <= station_orb:
                    stations.append(StationEvent(
                        transit_planet_id=pid,
                        transit_planet_name=tr_name,
                        station_jd=jd_stat,
                        station_date=_jd_to_date(jd_stat),
                        station_type=stype,
                        station_lon=stat_lon,
                        nearest_natal_planet=nearest_name,
                        nearest_natal_lon=nearest_lon,
                        orb_to_nearest=nearest_orb,
                    ))

        stations.sort(key=lambda s: s.station_jd)

    return TransitTimingResult(exact_hits=exact_hits, stations=stations)
