"""
POST /chart/horary/perfection — Horary Perfection Analysis endpoint (Epic 9.2).

Determines whether a horary question is perfected by analysing the relationship
between the querent significator (H1 lord) and the quesited significator
(lord of the relevant house).
"""

import swisseph as swe
from fastapi import APIRouter, HTTPException
from models.chart import (
    HoraryPerfectionRequest, HoraryPerfectionResponse,
    HorarySignificatorData, HoraryAspectRelationData,
    HoraryPerfectionData, HoraryProhibitionData,
    HoraryRefranationData, HoraryFrustrationData,
    HoraryReceptionData, HoraryTimingData,
)
from core.horary_perfection import calc_horary_perfection

router = APIRouter()

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED


@router.post("/chart/horary/perfection", response_model=HoraryPerfectionResponse)
def chart_horary_perfection(req: HoraryPerfectionRequest):
    try:
        hour_ut = req.hour + req.minute / 60.0 - req.ut_offset
        jd = swe.julday(req.year, req.month, req.day, hour_ut, swe.GREG_CAL)

        planet_lons:   dict[int, float] = {}
        planet_speeds: dict[int, float] = {}
        for pid in range(7):
            r, _ = swe.calc_ut(jd, pid, _FLAGS)
            planet_lons[pid]   = r[0]
            planet_speeds[pid] = r[3]

        cusps_raw, _ = swe.houses(jd, req.lat, req.lon, req.hsys.encode())
        cusps = list(cusps_raw)

        raw = calc_horary_perfection(
            planet_lons, planet_speeds, cusps,
            querent_house=req.querent_house,
            quesited_house=req.quesited_house,
        )

        def _sig(s):
            return HorarySignificatorData(
                planet_id=s.planet_id, planet_name=s.planet_name,
                lon=s.lon, sign=s.sign, sign_lon=s.sign_lon,
                retrograde=s.retrograde, house=s.house,
            )

        return HoraryPerfectionResponse(
            querent_house=raw.querent_house,
            quesited_house=raw.quesited_house,
            querent_significator=_sig(raw.querent_significator),
            quesited_significator=_sig(raw.quesited_significator),
            same_lord=raw.same_lord,
            direct_aspect=(
                HoraryAspectRelationData(
                    angle=raw.direct_aspect.angle,
                    aspect_name=raw.direct_aspect.aspect_name,
                    orb=raw.direct_aspect.orb,
                    applying=raw.direct_aspect.applying,
                ) if raw.direct_aspect else None
            ),
            perfection=HoraryPerfectionData(
                perfected=raw.perfection.perfected,
                method=raw.perfection.method,
                translator=raw.perfection.translator,
                collector=raw.perfection.collector,
                description=raw.perfection.description,
            ),
            prohibition=HoraryProhibitionData(
                prohibited=raw.prohibition.prohibited,
                prohibitor_name=raw.prohibition.prohibitor_name,
                prohibitor_aspect=raw.prohibition.prohibitor_aspect,
                description=raw.prohibition.description,
            ),
            refranation=HoraryRefranationData(
                refranation=raw.refranation.refranation,
                planet_name=raw.refranation.planet_name,
                description=raw.refranation.description,
            ),
            frustration=HoraryFrustrationData(
                frustrated=raw.frustration.frustrated,
                frustrator_name=raw.frustration.frustrator_name,
                description=raw.frustration.description,
            ),
            reception=HoraryReceptionData(
                querent_in_quesited_domicile=raw.reception.querent_in_quesited_domicile,
                quesited_in_querent_domicile=raw.reception.quesited_in_querent_domicile,
                querent_in_quesited_exaltation=raw.reception.querent_in_quesited_exaltation,
                quesited_in_querent_exaltation=raw.reception.quesited_in_querent_exaltation,
                mutual_reception=raw.reception.mutual_reception,
            ),
            timing=(
                HoraryTimingData(
                    days_raw=raw.timing.days_raw,
                    unit=raw.timing.unit,
                    value=raw.timing.value,
                    modality=raw.timing.modality,
                    note=raw.timing.note,
                ) if raw.timing else None
            ),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
