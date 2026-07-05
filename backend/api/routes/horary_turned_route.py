"""
POST /chart/horary/turned — Horary Turned Charts endpoint (Epic 10.4).

Turns the horary chart to view it from the perspective of a particular house,
enabling questions about third parties (siblings, parents, friends, enemies).
"""

import swisseph as swe
from fastapi import APIRouter, HTTPException

from models.chart import HoraryTurnedRequest, HoraryTurnedResponse, TurnedHouseData
from core.horary_turned import calc_horary_turned

router = APIRouter()

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED


@router.post("/chart/horary/turned", response_model=HoraryTurnedResponse)
def chart_horary_turned(req: HoraryTurnedRequest):
    """
    Turn the horary chart to view from 'from_house' perspective.

    Examples:
    - Sibling's career: from_house=3, quesited_house=10 → natal H12
    - Mother's illness: from_house=10, quesited_house=6  → natal H3
    - Friend's money:   from_house=11, quesited_house=2  → natal H12
    - Identity:         from_house=1,  quesited_house=7  → natal H7 (unchanged)
    """
    try:
        hour_ut = req.hour + req.minute / 60.0 - req.ut_offset
        jd = swe.julday(req.year, req.month, req.day, hour_ut, swe.GREG_CAL)

        cusps_raw, _ = swe.houses(jd, req.lat, req.lon, req.hsys.encode())
        cusps = list(cusps_raw)

        raw = calc_horary_turned(
            cusps=cusps,
            from_house=req.from_house,
            quesited_house=req.quesited_house,
            querent_house=req.querent_house,
        )

        return HoraryTurnedResponse(
            from_house=raw.from_house,
            from_house_topic=raw.from_house_topic,
            querent_house=raw.querent_house,
            original_quesited_house=raw.original_quesited_house,
            turned_quesited_house=raw.turned_quesited_house,
            turned_lord_id=raw.turned_lord_id,
            turned_lord_name=raw.turned_lord_name,
            explanation=raw.explanation,
            all_turned_houses=[
                TurnedHouseData(
                    turned_house=h.turned_house,
                    natal_house=h.natal_house,
                    cusp_lon=h.cusp_lon,
                    lord_id=h.lord_id,
                    lord_name=h.lord_name,
                )
                for h in raw.all_turned_houses
            ],
        )

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Horary turned error: {exc}")
