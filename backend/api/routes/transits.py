"""
Transits Overlay endpoint.

POST /chart/transits
"""

import swisseph as swe
from fastapi import APIRouter, HTTPException

from models.chart import (
    TransitRequest, TransitsResponse,
    PlanetPosition, TransitNatalAspect, CuspConjunction,
)
from core.transits import calc_transits_full

router = APIRouter()

_TRADITIONAL = [
    (swe.SUN,       "Sun"),
    (swe.MOON,      "Moon"),
    (swe.MERCURY,   "Mercury"),
    (swe.VENUS,     "Venus"),
    (swe.MARS,      "Mars"),
    (swe.JUPITER,   "Jupiter"),
    (swe.SATURN,    "Saturn"),
    (swe.TRUE_NODE, "True Node"),
    (swe.MEAN_NODE, "Mean Node"),
]

_OUTER = [
    (swe.URANUS,  "Uranus"),
    (swe.NEPTUNE, "Neptune"),
    (swe.PLUTO,   "Pluto"),
    (swe.CHIRON,  "Chiron"),
]

_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

_HOUSE_NAMES = {
    "B": "Alcabitius", "R": "Regiomontanus", "P": "Placidus",
    "W": "Whole Sign",  "E": "Equal",         "K": "Koch",
    "O": "Porphyry",    "C": "Campanus",       "A": "Equal (Asc)",
    "T": "Polich/Page (Topocentric)", "V": "Vehlow Equal", "X": "Axial Rotation",
}


def _lon_to_sign(lon: float) -> tuple[str, float]:
    return _SIGNS[int(lon / 30) % 12], round(lon % 30, 4)


def _calc_planet(jd: float, pid: int, name: str, flags: int) -> PlanetPosition:
    r, _ = swe.calc_ut(jd, pid, flags)
    sign, sign_lon = _lon_to_sign(r[0])
    return PlanetPosition(
        id=pid, name=name,
        lon=round(r[0], 4), lat=round(r[1], 4),
        speed=round(r[3], 6), retrograde=r[3] < 0,
        sign=sign, sign_lon=sign_lon,
    )


@router.post("/chart/transits", response_model=TransitsResponse)
def calculate_transits(req: TransitRequest):
    """
    Compute the transit overlay for a given date against the natal chart.

    Returns:
    - Transit planet positions at the transit date
    - Transit-to-natal aspects (all 5 Ptolemaic, within combined orb)
      including the exact calendar JD when each orb reaches 0
    - Transit-to-natal cusp conjunctions (each transit planet within
      cusp_orb of any of the 12 natal house cusps)
    """
    try:
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED

        # ── Natal JD ──────────────────────────────────────────────────────────
        hour_ut = req.hour + req.minute / 60.0 - req.ut_offset
        natal_jd = swe.julday(req.year, req.month, req.day, hour_ut, swe.GREG_CAL)

        # ── Transit JD (noon UTC) ─────────────────────────────────────────────
        transit_jd = swe.julday(
            req.transit_year, req.transit_month, req.transit_day,
            12.0, swe.GREG_CAL
        )

        # ── Natal planets (7 traditional) ─────────────────────────────────────
        natal_planets = [
            _calc_planet(natal_jd, pid, name, flags)
            for pid, name in _TRADITIONAL[:7]
        ]

        # ── Natal houses ──────────────────────────────────────────────────────
        hsys_byte = req.hsys.encode("utf-8")
        cusps_raw, _ = swe.houses(natal_jd, req.lat, req.lon, hsys_byte)
        natal_cusps = list(cusps_raw)

        # ── Transit planets ───────────────────────────────────────────────────
        planet_set = _TRADITIONAL[:]
        if req.include_outer:
            planet_set += _OUTER

        transit_planets = [
            _calc_planet(transit_jd, pid, name, flags)
            for pid, name in planet_set
        ]

        # ── Compute overlay ───────────────────────────────────────────────────
        result = calc_transits_full(
            transit_jd=transit_jd,
            transit_planets=transit_planets,
            natal_planets=natal_planets,
            natal_cusps=natal_cusps if req.include_cusp_conjunctions else [],
            max_orb=req.orb,
            cusp_orb=req.cusp_orb,
            exact_max_days=req.exact_max_days,
        )

        return TransitsResponse(
            natal_jd=round(natal_jd, 6),
            transit_jd=round(transit_jd, 6),
            transit_planets=transit_planets,
            natal_planets=natal_planets,
            aspects=[
                TransitNatalAspect(
                    transit_planet_id=a.transit_planet_id,
                    transit_planet_name=a.transit_planet_name,
                    transit_lon=a.transit_lon,
                    natal_planet_id=a.natal_planet_id,
                    natal_planet_name=a.natal_planet_name,
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
            cusp_conjunctions=[
                CuspConjunction(
                    transit_planet_id=c.transit_planet_id,
                    transit_planet_name=c.transit_planet_name,
                    transit_lon=c.transit_lon,
                    cusp_number=c.cusp_number,
                    cusp_lon=c.cusp_lon,
                    orb=c.orb,
                    applying=c.applying,
                    exact_jd=c.exact_jd,
                )
                for c in result.cusp_conjunctions
            ],
        )

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transits error: {exc}")
