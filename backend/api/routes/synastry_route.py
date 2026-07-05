"""
POST /chart/synastry — Synastry comparison endpoint (Epic 8.1).

Compares two natal charts:
  - Cross-aspects between A and B planets
  - Overlay houses (A planets in B's houses, B planets in A's houses)
  - Antiscia synastry aspects
"""

import swisseph as swe
from fastapi import APIRouter, HTTPException
from models.chart import (
    SynastryRequest, SynastryResponse,
    SynastryAspectData, OverlayPlanetData, SynastryAntisciaAspectData,
)
from core.synastry import calc_synastry

router = APIRouter()

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED


def _compute_chart(c):
    """Return (planet_lons, cusps_12) for a BirthDataInput."""
    hour_ut = c.hour + c.minute / 60.0 - c.ut_offset
    jd = swe.julday(c.year, c.month, c.day, hour_ut, swe.GREG_CAL)
    planet_lons: dict[int, float] = {}
    for pid in range(7):
        r, _ = swe.calc_ut(jd, pid, _FLAGS)
        planet_lons[pid] = r[0]
    cusps_raw, _ = swe.houses(jd, c.lat, c.lon, c.hsys.encode())
    return planet_lons, list(cusps_raw)  # 12 cusp longitudes


@router.post("/chart/synastry", response_model=SynastryResponse)
def chart_synastry(req: SynastryRequest):
    try:
        lons_a, cusps_a = _compute_chart(req.chart_a)
        lons_b, cusps_b = _compute_chart(req.chart_b)

        raw = calc_synastry(lons_a, lons_b, cusps_a, cusps_b)

        return SynastryResponse(
            cross_aspects=[
                SynastryAspectData(
                    planet_a_id=a.planet_a_id, planet_a_name=a.planet_a_name,
                    planet_b_id=a.planet_b_id, planet_b_name=a.planet_b_name,
                    aspect_angle=a.aspect_angle, aspect_name=a.aspect_name,
                    orb=a.orb, max_orb=a.max_orb,
                )
                for a in raw.cross_aspects
            ],
            a_planets_in_b_houses=[
                OverlayPlanetData(
                    planet_id=p.planet_id, planet_name=p.planet_name,
                    planet_lon=p.planet_lon, house=p.house,
                )
                for p in raw.a_planets_in_b_houses
            ],
            b_planets_in_a_houses=[
                OverlayPlanetData(
                    planet_id=p.planet_id, planet_name=p.planet_name,
                    planet_lon=p.planet_lon, house=p.house,
                )
                for p in raw.b_planets_in_a_houses
            ],
            antiscia_aspects=[
                SynastryAntisciaAspectData(
                    source=a.source,
                    planet_id=a.planet_id, planet_name=a.planet_name,
                    shadow_type=a.shadow_type, shadow_lon=a.shadow_lon,
                    target_id=a.target_id, target_name=a.target_name,
                    target_lon=a.target_lon,
                    aspect_angle=a.aspect_angle, aspect_name=a.aspect_name,
                    orb=a.orb,
                )
                for a in raw.antiscia_aspects
            ],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
