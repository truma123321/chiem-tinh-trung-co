"""
POST /chart/horary/dignities — Essential Dignities endpoint (Epic 9.3).

Computes the five essential dignities and three essential debilities for
the querent significator, quesited significator, and Moon co-significator.
"""

import swisseph as swe
from fastapi import APIRouter, HTTPException
from models.chart import (
    HoraryDignityRequest, HoraryDignityResponse,
    SignificatorDignityData, DignityDetailData,
)
from core.horary_dignities import calc_horary_dignities

router = APIRouter()

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED


def _dignity_data(d) -> DignityDetailData:
    return DignityDetailData(
        domicile=d.domicile, exaltation=d.exaltation,
        triplicity=d.triplicity, term=d.term, face=d.face,
        detriment=d.detriment, fall=d.fall,
        peregrine=d.peregrine, score=d.score, strength=d.strength,
    )


@router.post("/chart/horary/dignities", response_model=HoraryDignityResponse)
def chart_horary_dignities(req: HoraryDignityRequest):
    try:
        hour_ut = req.hour + req.minute / 60.0 - req.ut_offset
        jd = swe.julday(req.year, req.month, req.day, hour_ut, swe.GREG_CAL)

        planet_lons: dict[int, float] = {}
        for pid in range(7):
            r, _ = swe.calc_ut(jd, pid, _FLAGS)
            planet_lons[pid] = r[0]

        cusps_raw, _ = swe.houses(jd, req.lat, req.lon, req.hsys.encode())
        cusps = list(cusps_raw)

        raw = calc_horary_dignities(
            planet_lons, cusps,
            querent_house=req.querent_house,
            quesited_house=req.quesited_house,
        )

        def _sig(sd) -> SignificatorDignityData:
            return SignificatorDignityData(
                planet_id=sd.planet_id, planet_name=sd.planet_name,
                lon=sd.lon, sign=sd.sign, sign_lon=sd.sign_lon,
                dignity=_dignity_data(sd.dignity),
            )

        return HoraryDignityResponse(
            day_chart=raw.day_chart,
            querent_house=raw.querent_house,
            quesited_house=raw.quesited_house,
            querent_significator=_sig(raw.querent_significator),
            quesited_significator=_sig(raw.quesited_significator),
            moon_dignity=_dignity_data(raw.moon_dignity),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
