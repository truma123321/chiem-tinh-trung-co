"""
POST /chart/circumambulations — Circumambulations (Valens/Firmicus) endpoint.

Epic 7.3: Hellenistic time-lord system.
Significator (ASC + sect light) circumambulates the zodiac by oblique ascension.
Arc in degrees of OA = years of life at event (Ptolemy key).
"""

import swisseph as swe
from fastapi import APIRouter, HTTPException
from models.chart import (
    CircumambulationsRequest, CircumambulationsResponse,
    CircumambulationEventData, DatePointData, SubPeriodData,
)
from core.circumambulations import calc_circumambulations
from core.dignities import is_day_chart

router = APIRouter()

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED


@router.post("/chart/circumambulations", response_model=CircumambulationsResponse)
def chart_circumambulations(req: CircumambulationsRequest):
    try:
        hour_ut = req.hour + req.minute / 60.0 - req.ut_offset
        jd = swe.julday(req.year, req.month, req.day, hour_ut, swe.GREG_CAL)

        planet_lons: dict[int, float] = {}
        for pid in range(7):
            r, _ = swe.calc_ut(jd, pid, _FLAGS)
            planet_lons[pid] = r[0]

        cusps, ascmc = swe.houses(jd, req.lat, req.lon, req.hsys.encode())
        asc = ascmc[0]
        day = is_day_chart(planet_lons[0], asc)

        raw = calc_circumambulations(
            jd, req.lat, req.lon, planet_lons, day,
            include_sub_periods=req.include_sub_periods,
        )

        def _dp(d) -> DatePointData:
            return DatePointData(jd=d.jd, year=d.year, month=d.month, day=d.day)

        def _subs(sub_list) -> list[SubPeriodData] | None:
            if sub_list is None:
                return None
            return [
                SubPeriodData(
                    planet_id=s.planet_id,
                    planet_name=s.planet_name,
                    start_date=_dp(s.start_date),
                    end_date=_dp(s.end_date),
                    duration_days=s.duration_days,
                )
                for s in sub_list
            ]

        return CircumambulationsResponse(
            birth_jd=raw.birth_jd,
            significators=raw.significators,
            events=[
                CircumambulationEventData(
                    significator=e.significator,
                    promittor_id=e.promittor_id,
                    promittor_name=e.promittor_name,
                    aspect_angle=e.aspect_angle,
                    aspect_name=e.aspect_name,
                    arc=e.arc,
                    age_years=e.age_years,
                    event_date=_dp(e.event_date),
                    is_past=e.is_past,
                    is_loosing_of_bond=e.is_loosing_of_bond,
                    bonification=e.bonification,
                    maltreatment=e.maltreatment,
                    sub_periods=_subs(e.sub_periods),
                )
                for e in raw.events
            ],
            obliquity=raw.obliquity,
            armc=raw.armc,
            mc_lon=raw.mc_lon,
            mc_oa=raw.mc_oa,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
