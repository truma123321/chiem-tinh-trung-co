"""
POST /chart/composite — Composite Chart (midpoint method) endpoint (Epic 8.2).

Computes the composite chart from two natal charts by taking the near midpoint
of each pair of corresponding planetary positions and angles.
"""

import swisseph as swe
from fastapi import APIRouter, HTTPException
from models.chart import (
    CompositeRequest, CompositeResponse,
    CompositePlanetData, CompositeAspectData,
)
from core.composite import calc_composite

router = APIRouter()

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED


def _compute_chart(c):
    """Return (planet_lons, planet_speeds, asc, mc) for a BirthDataInput."""
    hour_ut = c.hour + c.minute / 60.0 - c.ut_offset
    jd = swe.julday(c.year, c.month, c.day, hour_ut, swe.GREG_CAL)
    planet_lons:   dict[int, float] = {}
    planet_speeds: dict[int, float] = {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, _FLAGS)
        planet_lons[pid]   = r[0]
        planet_speeds[pid] = r[3]
    _, ascmc = swe.houses(jd, c.lat, c.lon, c.hsys.encode())
    return planet_lons, planet_speeds, ascmc[0], ascmc[1]


@router.post("/chart/composite", response_model=CompositeResponse)
def chart_composite(req: CompositeRequest):
    try:
        lons_a, speeds_a, asc_a, mc_a = _compute_chart(req.chart_a)
        lons_b, speeds_b, asc_b, mc_b = _compute_chart(req.chart_b)

        raw = calc_composite(
            lons_a, lons_b, speeds_a, speeds_b,
            asc_a, asc_b, mc_a, mc_b,
        )

        return CompositeResponse(
            planets=[
                CompositePlanetData(
                    planet_id=p.planet_id, planet_name=p.planet_name,
                    lon=p.lon, sign=p.sign, sign_lon=p.sign_lon,
                    retrograde=p.retrograde,
                )
                for p in raw.planets
            ],
            asc=raw.asc,
            asc_sign=raw.asc_sign,
            mc=raw.mc,
            mc_sign=raw.mc_sign,
            aspects=[
                CompositeAspectData(
                    planet_a_id=a.planet_a_id, planet_a_name=a.planet_a_name,
                    planet_b_id=a.planet_b_id, planet_b_name=a.planet_b_name,
                    aspect_angle=a.aspect_angle, aspect_name=a.aspect_name,
                    orb=a.orb, max_orb=a.max_orb,
                )
                for a in raw.aspects
            ],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
