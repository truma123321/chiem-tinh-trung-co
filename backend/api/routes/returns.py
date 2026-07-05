"""
Return chart endpoints: Solar Return, Lunar Return.
"""

import swisseph as swe
from fastapi import APIRouter, HTTPException

from models.chart import (
    SolarReturnRequest, SolarReturnResponse,
    LunarReturnRequest, LunarReturnEntry, LunarReturnsResponse,
    ReturnDatetime,
    PlanetPosition, HouseCusps,
    PlanetDignity, AlmutenPoint, AlmutenResponse, ArabicPart,
    AspectData, CollectionOfLight, TranslationOfLight, AspectsResponse,
    PlanetConditionData, MoonConditionData, ConditionsResponse,
    PlanetSectData, SectResponse,
    StarAspectData, StarPositionData, FixedStarsResponse,
    AntisciaPointData, AntisciaAspectData, AntisciaResponse,
    NatalPlanetPlacement, ReturnToNatalAspect, ReturnNatalOverlay,
)
from core.dignities import calc_dignities, is_day_chart
from core.almuten import calc_almuten
from core.arabic_parts import calc_arabic_parts
from core.aspects import calc_aspects
from core.conditions import calc_conditions
from core.sect import calc_sect
from core.fixed_stars import calc_fixed_stars
from core.antiscia import calc_antiscia
from core.solar_return import find_solar_return_jd, jd_to_gregorian
from core.lunar_return import find_all_lunar_returns_in_year
from core.return_overlay import calc_return_natal_overlay

router = APIRouter()

# Traditional 7 planets (same order as natal route)
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


def _calc_natal_planets(
    year: int, month: int, day: int, hour: int, minute: int,
    ut_offset: float, flags: int,
) -> list[PlanetPosition]:
    """Compute the 7 traditional planets at the birth moment."""
    hour_ut = hour + minute / 60.0 - ut_offset
    jd_birth = swe.julday(year, month, day, hour_ut, swe.GREG_CAL)
    return [_calc_planet(jd_birth, pid, name, flags) for pid, name in _TRADITIONAL[:7]]


def _build_natal_overlay(
    natal_planets: list[PlanetPosition],
    return_chart: dict,
) -> ReturnNatalOverlay:
    """Build the ReturnNatalOverlay Pydantic model from raw overlay data."""
    raw = calc_return_natal_overlay(
        return_planets=return_chart["planets"],
        natal_planets=natal_planets,
        return_cusps=return_chart["houses"].cusps,
    )
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


def _compute_return_chart(
    jd_return: float,
    return_lat: float,
    return_lon: float,
    hsys: str,
    include_outer: bool,
    flags: int,
) -> dict:
    """
    Compute the full chart at `jd_return` at the specified location.
    Returns a dict of all chart components (planets, houses, dignities, …).
    Shared by solar-return and lunar-return endpoints.
    """
    planets = [_calc_planet(jd_return, pid, name, flags) for pid, name in _TRADITIONAL]
    if include_outer:
        planets += [_calc_planet(jd_return, pid, name, flags) for pid, name in _OUTER]

    hsys_byte = hsys.encode("utf-8")
    cusps_raw, ascmc = swe.houses(jd_return, return_lat, return_lon, hsys_byte)

    houses = HouseCusps(
        cusps=[round(c, 4) for c in cusps_raw],
        asc=round(ascmc[0], 4), mc=round(ascmc[1], 4),
        armc=round(ascmc[2], 4), vertex=round(ascmc[3], 4),
        system=_HOUSE_NAMES.get(hsys, hsys),
    )

    sun_lon  = planets[0].lon
    moon_lon = planets[1].lon
    day      = is_day_chart(sun_lon, houses.asc)

    dignities = [
        PlanetDignity(**vars(calc_dignities(pid, planets[i].lon, day)))
        for i, (pid, _) in enumerate(_TRADITIONAL[:7])
    ]

    planet_lons   = {pid: planets[i].lon   for i, (pid, _) in enumerate(_TRADITIONAL[:7])}
    planet_speeds = {pid: planets[i].speed for i, (pid, _) in enumerate(_TRADITIONAL[:7])}

    alm = calc_almuten(planet_lons, houses.asc, sun_lon, moon_lon, day, jd_return)
    almuten = AlmutenResponse(
        winner=alm.winner, winner_id=alm.winner_id,
        total_scores=alm.total_scores,
        points=[AlmutenPoint(name=p.name, lon=p.lon, scores=p.scores) for p in alm.points],
        lot_of_fortune=alm.lot_of_fortune,
        syzygy_lon=alm.syzygy_lon,
        syzygy_is_new_moon=alm.syzygy_is_new_moon,
        dead_heat=alm.dead_heat,
    )

    asp_raw = calc_aspects(planet_lons, planet_speeds)
    aspects_resp = AspectsResponse(
        aspects=[
            AspectData(
                planet_a=a.planet_a, planet_b=a.planet_b,
                name_a=a.name_a, name_b=a.name_b,
                aspect_type=a.aspect_type, aspect_name=a.aspect_name,
                orb=a.orb, max_orb=a.max_orb,
                applying=a.applying, exact=a.exact,
                sinister=a.sinister, whole_sign=a.whole_sign,
                mutual_reception=a.mutual_reception,
            )
            for a in asp_raw.aspects
        ],
        collections=[
            CollectionOfLight(
                collector=c.collector, collector_name=c.collector_name,
                from_a=c.from_a, from_b=c.from_b,
                name_a=c.name_a, name_b=c.name_b,
                orb_a=c.orb_a, orb_b=c.orb_b,
            )
            for c in asp_raw.collections
        ],
        translations=[
            TranslationOfLight(
                translator=t.translator, translator_name=t.translator_name,
                from_planet=t.from_planet, to_planet=t.to_planet,
                from_name=t.from_name, to_name=t.to_name,
                sep_orb=t.sep_orb, app_orb=t.app_orb,
            )
            for t in asp_raw.translations
        ],
    )

    parts_raw = calc_arabic_parts(
        planet_lons, houses.asc, sun_lon, moon_lon, day, jd_return, cusps_raw
    )
    arabic_parts = [
        ArabicPart(name=p.name, lon=p.lon, sign=p.sign, sign_lon=p.sign_lon,
                   formula=p.formula, diurnal=p.diurnal)
        for p in parts_raw
    ]

    cond_raw = calc_conditions(planet_lons, planet_speeds)
    conditions = ConditionsResponse(
        planet_conditions=[
            PlanetConditionData(
                planet_id=c.planet_id, planet_name=c.planet_name,
                sun_distance=c.sun_distance,
                cazimi=c.cazimi, combust=c.combust,
                under_beams=c.under_beams, free_from_beams=c.free_from_beams,
                oriental=c.oriental, occidental=c.occidental,
                elongation=c.elongation,
            )
            for c in cond_raw.planet_conditions
        ],
        moon=MoonConditionData(
            void_of_course=cond_raw.moon.void_of_course,
            next_aspect_planet=cond_raw.moon.next_aspect_planet,
            next_aspect_planet_name=cond_raw.moon.next_aspect_planet_name,
            next_aspect_type=cond_raw.moon.next_aspect_type,
            next_aspect_orb=cond_raw.moon.next_aspect_orb,
        ),
    )

    sect_raw = calc_sect(planet_lons, houses.asc, day, list(cusps_raw))
    sect_resp = SectResponse(
        day_chart=sect_raw.day_chart,
        planet_sects=[
            PlanetSectData(
                planet_id=s.planet_id, planet_name=s.planet_name,
                sect=s.sect, in_sect=s.in_sect,
                above_horizon=s.above_horizon, sign_masculine=s.sign_masculine,
                in_hayz=s.in_hayz,
                in_joy=s.in_joy, joy_house=s.joy_house,
            )
            for s in sect_raw.planet_sects
        ],
    )

    fs_raw = calc_fixed_stars(planet_lons, jd_return)
    fixed_stars_resp = FixedStarsResponse(
        aspects=[
            StarAspectData(
                star_name=a.star_name, star_lon=a.star_lon,
                star_nature=a.star_nature,
                planet_id=a.planet_id, planet_name=a.planet_name,
                orb=a.orb,
                aspect_angle=a.aspect_angle, aspect_name=a.aspect_name,
            )
            for a in fs_raw.aspects
        ],
        star_positions=[
            StarPositionData(name=s[0], lon=s[1], nature=s[2])
            for s in fs_raw.star_positions
        ],
    )

    anti_raw = calc_antiscia(planet_lons)
    antiscia_resp = AntisciaResponse(
        points=[
            AntisciaPointData(
                planet_id=p.planet_id, planet_name=p.planet_name,
                lon=p.lon, antiscion=p.antiscion,
                contra_antiscion=p.contra_antiscion,
            )
            for p in anti_raw.points
        ],
        aspects=[
            AntisciaAspectData(
                planet_a=a.planet_a, name_a=a.name_a,
                planet_b=a.planet_b, name_b=a.name_b,
                aspect_type=a.aspect_type,
                aspect_angle=a.aspect_angle, aspect_name=a.aspect_name,
                orb=a.orb,
            )
            for a in anti_raw.aspects
        ],
    )

    return dict(
        planets=planets, houses=houses, dignities=dignities,
        day_chart=day, almuten=almuten, arabic_parts=arabic_parts,
        aspects=aspects_resp, conditions=conditions, sect=sect_resp,
        fixed_stars=fixed_stars_resp, antiscia=antiscia_resp,
    )


@router.post("/chart/solar-return", response_model=SolarReturnResponse)
def calculate_solar_return(req: SolarReturnRequest):
    """
    Compute the solar return chart for a given birth date and target year.

    Finds the exact moment the Sun returns to its natal longitude (accurate
    to < 1 second), then computes the full chart at that moment using the
    specified return location.
    """
    try:
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED

        # ── Step 1: natal Sun longitude ──────────────────────────────────────
        hour_ut = req.hour + req.minute / 60.0 - req.ut_offset
        jd_birth = swe.julday(req.year, req.month, req.day, hour_ut, swe.GREG_CAL)
        r_natal, _ = swe.calc_ut(jd_birth, swe.SUN, flags)
        natal_sun_lon = r_natal[0]

        # ── Step 2: find exact return JD ─────────────────────────────────────
        jd_return = find_solar_return_jd(
            natal_sun_lon,
            return_year=req.return_year,
            birth_month=req.month,
            birth_day=req.day,
            birth_hour_ut=hour_ut,
        )

        # ── Step 3: verify accuracy (Sun at return JD should match natal lon) ─
        r_check, _ = swe.calc_ut(jd_return, swe.SUN, flags)
        diff = abs((r_check[0] - natal_sun_lon + 180) % 360 - 180)
        if diff > 0.001:
            raise ValueError(
                f"Solar return convergence failed: diff={diff:.6f}° "
                f"(natal={natal_sun_lon:.4f}°, got={r_check[0]:.4f}°)"
            )

        # ── Step 4: compute return chart ─────────────────────────────────────
        chart = _compute_return_chart(
            jd_return, req.return_lat, req.return_lon, req.hsys, req.include_outer, flags
        )

        # ── Step 5: optional natal overlay ────────────────────────────────────
        natal_overlay = None
        if req.include_natal_overlay:
            natal_planets = _calc_natal_planets(
                req.year, req.month, req.day, req.hour, req.minute, req.ut_offset, flags
            )
            natal_overlay = _build_natal_overlay(natal_planets, chart)

        # ── Step 6: build response ────────────────────────────────────────────
        dt = jd_to_gregorian(jd_return)
        return SolarReturnResponse(
            return_datetime=ReturnDatetime(
                jd=round(jd_return, 6),
                year=dt["year"], month=dt["month"], day=dt["day"],
                hour=dt["hour"], minute=dt["minute"], second=dt["second"],
                utc_iso=dt["utc_iso"],
            ),
            natal_sun_lon=round(natal_sun_lon, 6),
            natal_overlay=natal_overlay,
            **chart,
        )

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Solar return error: {exc}")


@router.post("/chart/lunar-return", response_model=LunarReturnsResponse)
def calculate_lunar_return(req: LunarReturnRequest):
    """
    Compute all lunar return charts for a given birth date and target year.

    Finds every moment (~12–13 times/year) when the Moon returns to its natal
    longitude. Returns a full chart for each return using the specified location.
    """
    try:
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED

        # ── Step 1: natal Moon longitude ─────────────────────────────────────
        hour_ut = req.hour + req.minute / 60.0 - req.ut_offset
        jd_birth = swe.julday(req.year, req.month, req.day, hour_ut, swe.GREG_CAL)
        r_natal, _ = swe.calc_ut(jd_birth, swe.MOON, flags)
        natal_moon_lon = r_natal[0]

        # ── Step 2: find all return JDs in the target year ───────────────────
        return_jds = find_all_lunar_returns_in_year(natal_moon_lon, req.return_year)

        if not return_jds:
            raise ValueError(
                f"No lunar returns found for year {req.return_year} "
                f"(natal Moon {natal_moon_lon:.4f}°)"
            )

        # ── Step 3: compute natal planets once (for overlay) ─────────────────
        natal_planets = None
        if req.include_natal_overlay:
            natal_planets = _calc_natal_planets(
                req.year, req.month, req.day, req.hour, req.minute, req.ut_offset, flags
            )

        # ── Step 4: compute chart for each return ────────────────────────────
        entries: list[LunarReturnEntry] = []
        for jd_return in return_jds:
            chart = _compute_return_chart(
                jd_return, req.return_lat, req.return_lon,
                req.hsys, req.include_outer, flags
            )
            natal_overlay = (
                _build_natal_overlay(natal_planets, chart) if natal_planets else None
            )
            dt = jd_to_gregorian(jd_return)
            entries.append(LunarReturnEntry(
                return_datetime=ReturnDatetime(
                    jd=round(jd_return, 6),
                    year=dt["year"], month=dt["month"], day=dt["day"],
                    hour=dt["hour"], minute=dt["minute"], second=dt["second"],
                    utc_iso=dt["utc_iso"],
                ),
                natal_moon_lon=round(natal_moon_lon, 6),
                natal_overlay=natal_overlay,
                **chart,
            ))

        return LunarReturnsResponse(
            natal_moon_lon=round(natal_moon_lon, 6),
            return_year=req.return_year,
            count=len(entries),
            returns=entries,
        )

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lunar return error: {exc}")
