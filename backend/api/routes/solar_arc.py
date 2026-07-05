"""
Solar Arc Directions endpoint.

POST /chart/solar-arc-directions
"""

import swisseph as swe
from fastapi import APIRouter, HTTPException

from models.chart import (
    SolarArcRequest, SolarArcResponse,
    DirectedPoint, DirectedAspect,
)
from core.solar_arc import calc_solar_arc_directions
from core.secondary_progressions import progressed_jd as calc_progressed_jd

router = APIRouter()

_TRADITIONAL = [
    (swe.SUN,       "Sun"),
    (swe.MOON,      "Moon"),
    (swe.MERCURY,   "Mercury"),
    (swe.VENUS,     "Venus"),
    (swe.MARS,      "Mars"),
    (swe.JUPITER,   "Jupiter"),
    (swe.SATURN,    "Saturn"),
]

_OUTER = [
    (swe.URANUS,  "Uranus"),
    (swe.NEPTUNE, "Neptune"),
    (swe.PLUTO,   "Pluto"),
    (swe.CHIRON,  "Chiron"),
]

_HOUSE_NAMES = {
    "B": "Alcabitius", "R": "Regiomontanus", "P": "Placidus",
    "W": "Whole Sign",  "E": "Equal",         "K": "Koch",
    "O": "Porphyry",    "C": "Campanus",       "A": "Equal (Asc)",
    "T": "Polich/Page (Topocentric)", "V": "Vehlow Equal", "X": "Axial Rotation",
}


@router.post("/chart/solar-arc-directions", response_model=SolarArcResponse)
def calculate_solar_arc_directions(req: SolarArcRequest):
    """
    Compute solar arc directed chart for a given target date.

    The solar arc = progressed Sun longitude − natal Sun longitude.
    Every natal point is shifted forward by this arc.

    Returns directed positions for 7 planets + ASC + MC, plus all
    directed-to-natal aspects within the specified orb, each with the
    exact calendar date (JD) when the orb reaches 0.
    """
    try:
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED

        # ── Birth JD ──────────────────────────────────────────────────────────
        hour_ut = req.hour + req.minute / 60.0 - req.ut_offset
        birth_jd = swe.julday(req.year, req.month, req.day, hour_ut, swe.GREG_CAL)

        # ── Target date JD ────────────────────────────────────────────────────
        target_jd = swe.julday(req.prog_year, req.prog_month, req.prog_day, 12.0, swe.GREG_CAL)

        if target_jd <= birth_jd:
            raise ValueError("Progression date must be after birth date.")

        # ── Progressed JD (day-for-a-year) ───────────────────────────────────
        _, jd_prog = calc_progressed_jd(birth_jd, target_jd)

        # ── Natal planets ─────────────────────────────────────────────────────
        planet_set = _TRADITIONAL[:]
        if req.include_outer:
            planet_set += _OUTER

        natal_points: list[tuple[str, float]] = []
        for pid, name in planet_set:
            r, _ = swe.calc_ut(birth_jd, pid, flags)
            natal_points.append((name, r[0]))

        # ── Natal ASC / MC ────────────────────────────────────────────────────
        hsys_byte = req.hsys.encode("utf-8")
        _, ascmc = swe.houses(birth_jd, req.lat, req.lon, hsys_byte)
        natal_points.append(("ASC", ascmc[0]))
        natal_points.append(("MC",  ascmc[1]))

        # ── Solar arc computation ─────────────────────────────────────────────
        result = calc_solar_arc_directions(
            birth_jd=birth_jd,
            jd_prog=jd_prog,
            natal_points=natal_points,
            max_orb=req.orb,
        )

        return SolarArcResponse(
            birth_jd=round(birth_jd, 6),
            target_jd=round(target_jd, 6),
            solar_arc=result.solar_arc,
            directed_points=[
                DirectedPoint(
                    name=p.name,
                    natal_lon=p.natal_lon,
                    directed_lon=p.directed_lon,
                    sign=p.sign,
                    sign_lon=p.sign_lon,
                )
                for p in result.directed_points
            ],
            aspects=[
                DirectedAspect(
                    directed_name=a.directed_name,
                    directed_lon=a.directed_lon,
                    natal_name=a.natal_name,
                    natal_lon=a.natal_lon,
                    aspect_type=a.aspect_type,
                    aspect_name=a.aspect_name,
                    orb=a.orb,
                    max_orb=a.max_orb,
                    applying=a.applying,
                    exact_jd=a.exact_jd,
                )
                for a in result.aspects
            ],
        )

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Solar arc error: {exc}")
