"""
POST /chart/horary — Horary Judgment Framework endpoint (Epic 9.1).

Evaluates whether a horary chart is radical (fit for judgment) by checking
six classical impediments per William Lilly / Anthony Louis.
"""

import swisseph as swe
from fastapi import APIRouter, HTTPException
from models.chart import HoraryRequest, HoraryResponse, HoraryCheckData
from core.horary import calc_horary

router = APIRouter()

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED


@router.post("/chart/horary", response_model=HoraryResponse)
def chart_horary(req: HoraryRequest):
    try:
        hour_ut = req.hour + req.minute / 60.0 - req.ut_offset
        jd = swe.julday(req.year, req.month, req.day, hour_ut, swe.GREG_CAL)

        planet_lons:   dict[int, float] = {}
        planet_speeds: dict[int, float] = {}
        for pid in range(7):
            r, _ = swe.calc_ut(jd, pid, _FLAGS)
            planet_lons[pid]   = r[0]
            planet_speeds[pid] = r[3]

        cusps_raw, ascmc = swe.houses(jd, req.lat, req.lon, req.hsys.encode())
        cusps = list(cusps_raw)
        asc   = ascmc[0]

        raw = calc_horary(planet_lons, planet_speeds, asc, cusps)

        return HoraryResponse(
            asc=raw.asc,
            asc_sign=raw.asc_sign,
            asc_degree=raw.asc_degree,
            moon_lon=raw.moon_lon,
            moon_sign=raw.moon_sign,
            moon_voc=raw.moon_voc,
            next_aspect_planet=raw.next_aspect_planet,
            next_aspect_name=raw.next_aspect_name,
            next_aspect_orb=raw.next_aspect_orb,
            saturn_lon=raw.saturn_lon,
            saturn_house=raw.saturn_house,
            via_combusta=raw.via_combusta,
            checks=[
                HoraryCheckData(
                    factor=c.factor,
                    label=c.label,
                    present=c.present,
                    description=c.description,
                )
                for c in raw.checks
            ],
            radicality=raw.radicality,
            negative_count=raw.negative_count,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
