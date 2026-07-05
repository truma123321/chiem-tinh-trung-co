"""
POST /chart/profections — Annual, Monthly, Daily profections endpoint.

Epic 7.1: extend profections beyond annual to monthly (2.5°/month)
and daily (30°/30.4375 per day) sub-divisions.
"""

import swisseph as swe
from fastapi import APIRouter, HTTPException
from models.chart import (
    ProfectionsRequest, ProfectionsEndpointResponse,
    ProfectionYearData, ProfectionResponse,
    MonthlyProfectionData, MonthlyProfectionResult,
    DailyProfectionData, DailyProfectionResult,
    DatePointData,
)
from core.profections import (
    calc_profections, calc_monthly_profection, calc_daily_profection,
)

router = APIRouter()

_TRADITIONAL = [
    swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS,
    swe.MARS, swe.JUPITER, swe.SATURN,
]
_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED


def _dp(d) -> DatePointData:
    return DatePointData(jd=d.jd, year=d.year, month=d.month, day=d.day)


def _build_annual(prof_raw) -> ProfectionResponse:
    def _year(y):
        return ProfectionYearData(
            age=y.age, house=y.house,
            profected_sign_idx=y.profected_sign_idx,
            profected_sign=y.profected_sign,
            profected_asc=y.profected_asc,
            lord_id=y.lord_id, lord_name=y.lord_name,
            start=_dp(y.start), end=_dp(y.end),
            is_current=y.is_current,
            activated_planet_ids=y.activated_planet_ids,
        )
    return ProfectionResponse(
        current_age=prof_raw.current_age,
        birth_jd=prof_raw.birth_jd,
        years=[_year(y) for y in prof_raw.years],
        current_year=_year(prof_raw.current_year) if prof_raw.current_year else None,
    )


def _build_monthly(mon_raw) -> MonthlyProfectionResult:
    def _m(m):
        return MonthlyProfectionData(
            age_months=m.age_months, month_in_year=m.month_in_year,
            profected_asc=m.profected_asc,
            profected_sign_idx=m.profected_sign_idx,
            profected_sign=m.profected_sign,
            lord_id=m.lord_id, lord_name=m.lord_name,
            start=_dp(m.start), end=_dp(m.end),
            is_current=m.is_current,
            activated_planet_ids=m.activated_planet_ids,
        )
    return MonthlyProfectionResult(
        total_months=mon_raw.total_months,
        total_years=mon_raw.total_years,
        month_in_year=mon_raw.month_in_year,
        entries=[_m(e) for e in mon_raw.entries],
        current_entry=_m(mon_raw.current_entry) if mon_raw.current_entry else None,
        birth_jd=mon_raw.birth_jd,
    )


def _build_daily(day_raw) -> DailyProfectionResult:
    def _d(d):
        return DailyProfectionData(
            age_days=d.age_days, day_in_month=d.day_in_month,
            profected_asc=d.profected_asc,
            profected_sign_idx=d.profected_sign_idx,
            profected_sign=d.profected_sign,
            lord_id=d.lord_id, lord_name=d.lord_name,
            start=_dp(d.start), end=_dp(d.end),
            is_current=d.is_current,
            activated_planet_ids=d.activated_planet_ids,
        )
    return DailyProfectionResult(
        total_days=day_raw.total_days,
        total_months=day_raw.total_months,
        day_in_month=day_raw.day_in_month,
        entries=[_d(e) for e in day_raw.entries],
        current_entry=_d(day_raw.current_entry) if day_raw.current_entry else None,
        birth_jd=day_raw.birth_jd,
    )


@router.post("/chart/profections", response_model=ProfectionsEndpointResponse)
def chart_profections(req: ProfectionsRequest):
    if req.period not in ("annual", "monthly", "daily"):
        raise HTTPException(
            status_code=422,
            detail=f"period must be 'annual', 'monthly', or 'daily', got '{req.period}'"
        )

    try:
        hour_ut = req.hour + req.minute / 60.0 - req.ut_offset
        jd = swe.julday(req.year, req.month, req.day, hour_ut, swe.GREG_CAL)

        # Compute planet longitudes for activated-planet detection
        planet_lons: dict[int, float] = {}
        for pid in range(7):
            r, _ = swe.calc_ut(jd, _TRADITIONAL[pid], _FLAGS)
            planet_lons[pid] = r[0]

        # ASC from house system
        cusps, ascmc = swe.houses(jd, req.lat, req.lon, req.hsys.encode())
        asc = ascmc[0]

        birth_jd = round(jd, 6)

        if req.period == "annual":
            prof_raw = calc_profections(jd, asc, planet_lons)
            return ProfectionsEndpointResponse(
                period="annual",
                birth_jd=birth_jd,
                annual=_build_annual(prof_raw),
            )

        elif req.period == "monthly":
            mon_raw = calc_monthly_profection(jd, asc, planet_lons)
            return ProfectionsEndpointResponse(
                period="monthly",
                birth_jd=birth_jd,
                monthly=_build_monthly(mon_raw),
            )

        else:  # daily
            day_raw = calc_daily_profection(jd, asc, planet_lons)
            return ProfectionsEndpointResponse(
                period="daily",
                birth_jd=birth_jd,
                daily=_build_daily(day_raw),
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
