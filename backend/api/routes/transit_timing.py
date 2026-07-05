"""
Transit Timing endpoint — Epic 5.2.

POST /chart/transit-timing
"""

import swisseph as swe
from fastapi import APIRouter, HTTPException

from models.chart import (
    TransitTimingRequest, TransitTimingResponse,
    ExactHit, StationEvent, PlanetPosition,
)
from core.transit_timing import calc_transit_timing

router = APIRouter()

_TRADITIONAL = [
    (swe.SUN,     "Sun"),
    (swe.MOON,    "Moon"),
    (swe.MERCURY, "Mercury"),
    (swe.VENUS,   "Venus"),
    (swe.MARS,    "Mars"),
    (swe.JUPITER, "Jupiter"),
    (swe.SATURN,  "Saturn"),
]

_NODES = [
    (swe.TRUE_NODE, "True Node"),
    (swe.MEAN_NODE, "Mean Node"),
]

_OUTER = [
    (swe.URANUS,  "Uranus"),
    (swe.NEPTUNE, "Neptune"),
    (swe.PLUTO,   "Pluto"),
    (swe.CHIRON,  "Chiron"),
]

_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


def _calc_planet(jd: float, pid: int, name: str) -> PlanetPosition:
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    r, _ = swe.calc_ut(jd, pid, flags)
    sign = _SIGNS[int(r[0] / 30) % 12]
    return PlanetPosition(
        id=pid, name=name,
        lon=round(r[0], 4), lat=round(r[1], 4),
        speed=round(r[3], 6), retrograde=r[3] < 0,
        sign=sign, sign_lon=round(r[0] % 30, 4),
    )


@router.post("/chart/transit-timing", response_model=TransitTimingResponse)
def calculate_transit_timing(req: TransitTimingRequest):
    """
    Compute all exact transit-to-natal aspect hits in a date range.

    Returns a chronological list of every moment each transit planet
    forms an exact Ptolemaic aspect to each natal planet, plus station
    events (SR / SD) of retrograde planets that occur near natal planets.
    """
    try:
        # ── Natal JD ──────────────────────────────────────────────────────
        hour_ut = req.hour + req.minute / 60.0 - req.ut_offset
        natal_jd = swe.julday(req.year, req.month, req.day, hour_ut, swe.GREG_CAL)

        # ── Date-range JDs (noon UTC boundaries) ───────────────────────────
        start_jd = swe.julday(req.start_year, req.start_month, req.start_day, 0.0, swe.GREG_CAL)
        end_jd   = swe.julday(req.end_year,   req.end_month,   req.end_day,  24.0, swe.GREG_CAL)

        if end_jd <= start_jd:
            raise ValueError("end date must be after start date")

        # ── Natal planets at birth (7 traditional) ─────────────────────────
        natal_planets = [
            _calc_planet(natal_jd, pid, name)
            for pid, name in _TRADITIONAL
        ]

        # ── Transit planet set ─────────────────────────────────────────────
        planet_list: list[tuple[int, str]] = []

        for pid, name in _TRADITIONAL:
            if pid == swe.MOON and not req.include_moon:
                continue
            planet_list.append((pid, name))

        if req.include_nodes:
            planet_list.extend(_NODES)

        if req.include_outer:
            planet_list.extend(_OUTER)

        # ── Core computation ───────────────────────────────────────────────
        result = calc_transit_timing(
            start_jd=start_jd,
            end_jd=end_jd,
            transit_planet_ids=planet_list,
            natal_planets=natal_planets,
            station_orb=req.station_orb,
            include_stations=req.include_stations,
        )

        return TransitTimingResponse(
            natal_jd=round(natal_jd, 6),
            start_jd=round(start_jd, 6),
            end_jd=round(end_jd, 6),
            exact_hits=[
                ExactHit(
                    transit_planet_id=h.transit_planet_id,
                    transit_planet_name=h.transit_planet_name,
                    natal_planet_id=h.natal_planet_id,
                    natal_planet_name=h.natal_planet_name,
                    natal_lon=h.natal_lon,
                    aspect_type=h.aspect_type,
                    aspect_name=h.aspect_name,
                    exact_jd=h.exact_jd,
                    exact_date=h.exact_date,
                    hit_number=h.hit_number,
                    total_hits=h.total_hits,
                    retrograde_at_exact=h.retrograde_at_exact,
                )
                for h in result.exact_hits
            ],
            stations=[
                StationEvent(
                    transit_planet_id=s.transit_planet_id,
                    transit_planet_name=s.transit_planet_name,
                    station_jd=s.station_jd,
                    station_date=s.station_date,
                    station_type=s.station_type,
                    station_lon=s.station_lon,
                    nearest_natal_planet=s.nearest_natal_planet,
                    nearest_natal_lon=s.nearest_natal_lon,
                    orb_to_nearest=s.orb_to_nearest,
                )
                for s in result.stations
            ],
        )

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transit timing error: {exc}")
