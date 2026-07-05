"""
POST /chart/decennials — Decennials (Paulus Alexandrinus) endpoint.

Epic 7.2: 129-year Chaldean time-lord system.
Starting planet = lord of birth planetary hour.
7 major periods (minor years) × 7 sub-periods each.
"""

import swisseph as swe
from fastapi import APIRouter, HTTPException
from models.chart import (
    DecennialsRequest, DecennialsResponse,
    DecennialSubData, DecennialPeriodData,
    DatePointData,
)
from core.decennials import calc_decennials

router = APIRouter()


def _dp(d) -> DatePointData:
    return DatePointData(jd=d.jd, year=d.year, month=d.month, day=d.day)


def _sub(s) -> DecennialSubData:
    return DecennialSubData(
        planet_id=s.planet_id, planet_name=s.planet_name,
        duration_years=s.duration_years,
        start=_dp(s.start), end=_dp(s.end),
        is_current=s.is_current,
    )


def _period(p) -> DecennialPeriodData:
    return DecennialPeriodData(
        planet_id=p.planet_id, planet_name=p.planet_name,
        duration_years=p.duration_years,
        start=_dp(p.start), end=_dp(p.end),
        is_current=p.is_current,
        sub_periods=[_sub(s) for s in p.sub_periods],
    )


@router.post("/chart/decennials", response_model=DecennialsResponse)
def chart_decennials(req: DecennialsRequest):
    try:
        hour_ut = req.hour + req.minute / 60.0 - req.ut_offset
        jd = swe.julday(req.year, req.month, req.day, hour_ut, swe.GREG_CAL)

        raw = calc_decennials(jd, req.lat, req.lon)

        return DecennialsResponse(
            birth_hour_lord_id=raw.birth_hour_lord_id,
            birth_hour_lord_name=raw.birth_hour_lord_name,
            birth_jd=raw.birth_jd,
            cycle_start_jd=raw.cycle_start_jd,
            periods=[_period(p) for p in raw.periods],
            current_period=_period(raw.current_period) if raw.current_period else None,
            current_sub=_sub(raw.current_sub) if raw.current_sub else None,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
