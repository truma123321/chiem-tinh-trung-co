"""
Ingresses endpoint — Epic 5.3.

POST /chart/ingresses
"""

import swisseph as swe
from fastapi import APIRouter, HTTPException

from models.chart import IngressRequest, IngressResponse, IngressEventModel
from core.ingresses import calc_ingresses

router = APIRouter()

_TRADITIONAL_NO_MOON = [
    (swe.SUN,     "Sun"),
    (swe.MERCURY, "Mercury"),
    (swe.VENUS,   "Venus"),
    (swe.MARS,    "Mars"),
    (swe.JUPITER, "Jupiter"),
    (swe.SATURN,  "Saturn"),
]

_MOON   = [(swe.MOON, "Moon")]
_NODES  = [(swe.TRUE_NODE, "True Node"), (swe.MEAN_NODE, "Mean Node")]
_OUTER  = [
    (swe.URANUS,  "Uranus"),
    (swe.NEPTUNE, "Neptune"),
    (swe.PLUTO,   "Pluto"),
    (swe.CHIRON,  "Chiron"),
]


@router.post("/chart/ingresses", response_model=IngressResponse)
def calculate_ingresses(req: IngressRequest):
    """
    Return all sign ingresses (planet enters a new zodiac sign) in the
    requested date range, sorted chronologically.

    Includes retrograde ingresses: a planet moving backwards across a
    sign boundary is flagged `retrograde=True` and the `sign` field
    reflects the sign actually entered (the one the planet moves into).

    Moon ingresses every ~2.5 days; enable with include_moon=True.
    """
    try:
        start_jd = swe.julday(
            req.start_year, req.start_month, req.start_day, 0.0, swe.GREG_CAL
        )
        end_jd = swe.julday(
            req.end_year, req.end_month, req.end_day, 24.0, swe.GREG_CAL
        )

        if end_jd <= start_jd:
            raise ValueError("end date must be after start date")

        planet_list = list(_TRADITIONAL_NO_MOON)
        if req.include_moon:
            planet_list = [*_MOON, *planet_list]
        if req.include_nodes:
            planet_list.extend(_NODES)
        if req.include_outer:
            planet_list.extend(_OUTER)

        events = calc_ingresses(start_jd, end_jd, planet_list)

        return IngressResponse(
            start_jd=round(start_jd, 6),
            end_jd=round(end_jd, 6),
            ingresses=[
                IngressEventModel(
                    planet_id=e.planet_id,
                    planet_name=e.planet_name,
                    sign=e.sign,
                    from_sign=e.from_sign,
                    boundary_lon=e.boundary_lon,
                    ingress_jd=e.ingress_jd,
                    ingress_date=e.ingress_date,
                    ingress_time=e.ingress_time,
                    retrograde=e.retrograde,
                )
                for e in events
            ],
        )

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingresses error: {exc}")
