"""
Secondary and Tertiary Progressions endpoints.

POST /chart/secondary-progressions
POST /chart/tertiary-progressions
"""

import swisseph as swe
from fastapi import APIRouter, HTTPException

from models.chart import (
    SecondaryProgressionRequest, SecondaryProgressionsResponse,
    TertiaryProgressionRequest, TertiaryProgressionsResponse,
    PlanetPosition, HouseCusps, ArabicPart,
    ProgressedLunation,
    NatalPlanetPlacement, ReturnToNatalAspect, ReturnNatalOverlay,
)
from core.secondary_progressions import (
    progressed_jd as calc_progressed_jd,
    tertiary_jd as calc_tertiary_jd,
    calc_progressed_lunation,
)
from core.return_overlay import calc_return_natal_overlay
from core.arabic_parts import calc_arabic_parts
from core.dignities import is_day_chart

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


def _build_overlay(progressed_planets, natal_planets, cusps) -> ReturnNatalOverlay:
    raw = calc_return_natal_overlay(progressed_planets, natal_planets, cusps)
    return ReturnNatalOverlay(
        natal_planets=raw.natal_planets,
        placements=[
            NatalPlanetPlacement(
                planet_id=p.planet_id, planet_name=p.planet_name,
                natal_lon=p.natal_lon, return_house=p.return_house,
            )
            for p in raw.placements
        ],
        cross_aspects=[
            ReturnToNatalAspect(
                return_planet_id=a.return_planet_id,
                return_planet_name=a.return_planet_name,
                natal_planet_id=a.natal_planet_id,
                natal_planet_name=a.natal_planet_name,
                aspect_type=a.aspect_type, aspect_name=a.aspect_name,
                orb=a.orb, max_orb=a.max_orb,
                applying=a.applying, exact=a.exact,
            )
            for a in raw.cross_aspects
        ],
    )


@router.post("/chart/secondary-progressions", response_model=SecondaryProgressionsResponse)
def calculate_secondary_progressions(req: SecondaryProgressionRequest):
    """
    Compute the secondary progressed chart for a given target date.

    Method: day-for-a-year.
    - age_years    = (target_date_jd − birth_jd) / 365.25
    - progressed_jd = birth_jd + age_years  (days after birth)

    Returns progressed planet positions, optional house cusps (at birth
    location), progressed-to-natal aspects, and the progressed lunation phase.
    """
    try:
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED

        # ── Birth JD ──────────────────────────────────────────────────────────
        hour_ut = req.hour + req.minute / 60.0 - req.ut_offset
        birth_jd = swe.julday(req.year, req.month, req.day, hour_ut, swe.GREG_CAL)

        # ── Target date JD (noon UTC as canonical reference) ──────────────────
        target_jd = swe.julday(req.prog_year, req.prog_month, req.prog_day, 12.0, swe.GREG_CAL)

        if target_jd <= birth_jd:
            raise ValueError("Progression date must be after birth date.")

        # ── Progressed JD (symbolic) ──────────────────────────────────────────
        age_years, jd_prog = calc_progressed_jd(birth_jd, target_jd)

        # ── Progressed planets ────────────────────────────────────────────────
        prog_planets = [_calc_planet(jd_prog, pid, name, flags)
                        for pid, name in _TRADITIONAL]
        if req.include_outer:
            prog_planets += [_calc_planet(jd_prog, pid, name, flags)
                             for pid, name in _OUTER]

        # ── Progressed houses (birth location, progressed sidereal time) ──────
        prog_houses = None
        if req.include_progressed_houses:
            hsys_byte = req.hsys.encode("utf-8")
            cusps_raw, ascmc = swe.houses(jd_prog, req.lat, req.lon, hsys_byte)
            prog_houses = HouseCusps(
                cusps=[round(c, 4) for c in cusps_raw],
                asc=round(ascmc[0], 4), mc=round(ascmc[1], 4),
                armc=round(ascmc[2], 4), vertex=round(ascmc[3], 4),
                system=_HOUSE_NAMES.get(req.hsys, req.hsys),
            )
        else:
            # Compute cusps anyway for overlay placement (use but don't return)
            hsys_byte = req.hsys.encode("utf-8")
            cusps_raw, _ = swe.houses(jd_prog, req.lat, req.lon, hsys_byte)

        # ── Natal planets (for overlay) ───────────────────────────────────────
        natal_overlay = None
        if req.include_natal_overlay:
            natal_planets = [_calc_planet(birth_jd, pid, name, flags)
                             for pid, name in _TRADITIONAL[:7]]
            natal_overlay = _build_overlay(
                prog_planets, natal_planets, list(cusps_raw)
            )

        # ── Progressed lunation ───────────────────────────────────────────────
        lun_raw = calc_progressed_lunation(birth_jd, jd_prog)
        lunation = ProgressedLunation(
            phase_angle=lun_raw.phase_angle,
            phase_name=lun_raw.phase_name,
            last_new_moon_jd=lun_raw.last_new_moon_jd,
            last_new_moon_age=lun_raw.last_new_moon_age,
            last_full_moon_jd=lun_raw.last_full_moon_jd,
            last_full_moon_age=lun_raw.last_full_moon_age,
        )

        # ── Arabic Parts (optional) ───────────────────────────────────────────
        arabic_parts = None
        if req.include_lots:
            _, ascmc_prog = swe.houses(jd_prog, req.lat, req.lon, req.hsys.encode("utf-8"))
            prog_asc = ascmc_prog[0]
            prog_lons = {pid: prog_planets[i].lon for i, (pid, _) in enumerate(_TRADITIONAL[:7])}
            prog_sun  = prog_planets[0].lon
            prog_moon = prog_planets[1].lon
            prog_day  = is_day_chart(prog_sun, prog_asc)
            parts_raw = calc_arabic_parts(prog_lons, prog_asc, prog_sun, prog_moon,
                                          prog_day, jd_prog, list(cusps_raw))
            arabic_parts = [
                ArabicPart(name=p.name, lon=p.lon, sign=p.sign, sign_lon=p.sign_lon,
                           formula=p.formula, diurnal=p.diurnal)
                for p in parts_raw
            ]

        return SecondaryProgressionsResponse(
            birth_jd=round(birth_jd, 6),
            target_jd=round(target_jd, 6),
            progressed_jd=round(jd_prog, 6),
            age_years=round(age_years, 6),
            progressed_planets=prog_planets,
            progressed_houses=prog_houses,
            natal_overlay=natal_overlay,
            lunation=lunation,
            arabic_parts=arabic_parts,
        )

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Secondary progressions error: {exc}")


@router.post("/chart/tertiary-progressions", response_model=TertiaryProgressionsResponse)
def calculate_tertiary_progressions(req: TertiaryProgressionRequest):
    """
    Compute the tertiary progressed chart for a given target date.

    Method: day-for-a-month.
    - age_months   = (target_date_jd − birth_jd) / month_days
    - progressed_jd = birth_jd + age_months  (days after birth)

    month_type:
        "sidereal" → month_days = 27.32158  (default)
        "synodic"  → month_days = 29.53059

    Returns progressed planet positions, optional house cusps,
    progressed-to-natal aspects, and the progressed lunation phase.
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

        # ── Tertiary progressed JD ────────────────────────────────────────────
        age_months, jd_prog, month_days = calc_tertiary_jd(
            birth_jd, target_jd, req.month_type
        )

        # ── Progressed planets ────────────────────────────────────────────────
        prog_planets = [_calc_planet(jd_prog, pid, name, flags)
                        for pid, name in _TRADITIONAL]
        if req.include_outer:
            prog_planets += [_calc_planet(jd_prog, pid, name, flags)
                             for pid, name in _OUTER]

        # ── Progressed houses ─────────────────────────────────────────────────
        prog_houses = None
        hsys_byte = req.hsys.encode("utf-8")
        if req.include_progressed_houses:
            cusps_raw, ascmc = swe.houses(jd_prog, req.lat, req.lon, hsys_byte)
            prog_houses = HouseCusps(
                cusps=[round(c, 4) for c in cusps_raw],
                asc=round(ascmc[0], 4), mc=round(ascmc[1], 4),
                armc=round(ascmc[2], 4), vertex=round(ascmc[3], 4),
                system=_HOUSE_NAMES.get(req.hsys, req.hsys),
            )
        else:
            cusps_raw, _ = swe.houses(jd_prog, req.lat, req.lon, hsys_byte)

        # ── Natal overlay ─────────────────────────────────────────────────────
        natal_overlay = None
        if req.include_natal_overlay:
            natal_planets = [_calc_planet(birth_jd, pid, name, flags)
                             for pid, name in _TRADITIONAL[:7]]
            natal_overlay = _build_overlay(prog_planets, natal_planets, list(cusps_raw))

        # ── Progressed lunation ───────────────────────────────────────────────
        lun_raw = calc_progressed_lunation(birth_jd, jd_prog)
        lunation = ProgressedLunation(
            phase_angle=lun_raw.phase_angle,
            phase_name=lun_raw.phase_name,
            last_new_moon_jd=lun_raw.last_new_moon_jd,
            last_new_moon_age=lun_raw.last_new_moon_age,
            last_full_moon_jd=lun_raw.last_full_moon_jd,
            last_full_moon_age=lun_raw.last_full_moon_age,
        )

        # ── Arabic Parts (optional) ───────────────────────────────────────────
        arabic_parts = None
        if req.include_lots:
            _, ascmc_prog = swe.houses(jd_prog, req.lat, req.lon, hsys_byte)
            prog_asc = ascmc_prog[0]
            prog_lons = {pid: prog_planets[i].lon for i, (pid, _) in enumerate(_TRADITIONAL[:7])}
            prog_sun  = prog_planets[0].lon
            prog_moon = prog_planets[1].lon
            prog_day  = is_day_chart(prog_sun, prog_asc)
            parts_raw = calc_arabic_parts(prog_lons, prog_asc, prog_sun, prog_moon,
                                          prog_day, jd_prog, list(cusps_raw))
            arabic_parts = [
                ArabicPart(name=p.name, lon=p.lon, sign=p.sign, sign_lon=p.sign_lon,
                           formula=p.formula, diurnal=p.diurnal)
                for p in parts_raw
            ]

        return TertiaryProgressionsResponse(
            birth_jd=round(birth_jd, 6),
            target_jd=round(target_jd, 6),
            progressed_jd=round(jd_prog, 6),
            age_months=round(age_months, 6),
            month_type=req.month_type,
            month_days=round(month_days, 5),
            progressed_planets=prog_planets,
            progressed_houses=prog_houses,
            natal_overlay=natal_overlay,
            lunation=lunation,
            arabic_parts=arabic_parts,
        )

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Tertiary progressions error: {exc}")
