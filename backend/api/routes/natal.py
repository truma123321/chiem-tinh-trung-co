"""
Natal chart endpoint.
Currently: planetary positions + house cusps + essential dignities.
Future stories will add: lots, almuten, firdaria, etc.
"""

import swisseph as swe
from fastapi import APIRouter, HTTPException
from models.chart import (
    NatalChartRequest, NatalChartResponse, PlanetPosition, HouseCusps,
    PlanetDignity, AlmutenPoint, AlmutenResponse, ArabicPart,
    AspectData, CollectionOfLight, TranslationOfLight, AspectsResponse,
    PlanetConditionData, MoonConditionData, ConditionsResponse,
    PlanetSectData, SectResponse,
    StarAspectData, StarPositionData, FixedStarsResponse,
    AntisciaPointData, AntisciaAspectData, AntisciaResponse,
    DatePointData, FirdariaSubData, FirdariaPeriodData, FirdariaResponse,
    ProfectionYearData, ProfectionResponse, MonthlyProfectionData,
    PrimaryDirectionData, PrimaryDirectionsResponse,
    AccidentalDignityData,
    DoryphoryBearerData, DoryphoryResponse,
    TemperamentContributionData, TemperamentResponse,
    DecennialSubData, DecennialPeriodData, DecennialsResponse,
    CircumambulationEventData, CircumambulationsResponse,
)
from core.dignities import calc_dignities, is_day_chart
from core.almuten import calc_almuten, calc_lot_of_fortune, calc_prenatal_syzygy
from core.arabic_parts import calc_arabic_parts
from core.aspects import calc_aspects
from core.conditions import calc_conditions
from core.sect import calc_sect
from core.fixed_stars import calc_fixed_stars
from core.antiscia import calc_antiscia
from core.firdaria import calc_firdaria
from core.profections import calc_profections, calc_monthly_profection
from core.primary_directions import calc_primary_directions
from core.accidental_dignities import calc_accidental_dignities
from core.doryphory import calc_doryphory
from core.temperament import calc_temperament
from core.decennials import calc_decennials
from core.circumambulations import calc_circumambulations

router = APIRouter()

# Traditional 7 planets (medieval) + nodes
TRADITIONAL_PLANETS = [
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

# Outer planets (modern, optional)
OUTER_PLANETS = [
    (swe.URANUS,  "Uranus"),
    (swe.NEPTUNE, "Neptune"),
    (swe.PLUTO,   "Pluto"),
    (swe.CHIRON,  "Chiron"),
]

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

HOUSE_SYSTEM_NAMES = {
    "B": "Alcabitius",
    "R": "Regiomontanus",
    "P": "Placidus",
    "W": "Whole Sign",
    "E": "Equal",
    "K": "Koch",
    "O": "Porphyry",
    "C": "Campanus",
    "A": "Equal (Asc)",
    "T": "Polich/Page (Topocentric)",
    "V": "Vehlow Equal",
    "X": "Axial Rotation",
}


def lon_to_sign(lon: float) -> tuple[str, float]:
    """Convert ecliptic longitude to sign name and degree within sign."""
    sign_idx = int(lon / 30) % 12
    sign_lon = lon % 30
    return SIGNS[sign_idx], round(sign_lon, 4)


def calc_planet(jd: float, planet_id: int, planet_name: str, flags: int) -> PlanetPosition:
    result, _ = swe.calc_ut(jd, planet_id, flags)
    lon = result[0]
    lat = result[1]
    speed = result[3]
    sign, sign_lon = lon_to_sign(lon)
    return PlanetPosition(
        id=planet_id,
        name=planet_name,
        lon=round(lon, 4),
        lat=round(lat, 4),
        speed=round(speed, 6),
        retrograde=speed < 0,
        sign=sign,
        sign_lon=sign_lon,
    )


@router.post("/chart/natal", response_model=NatalChartResponse)
def calculate_natal_chart(req: NatalChartRequest):
    try:
        # Convert local time to UT
        hour_ut = req.hour + req.minute / 60.0 - req.ut_offset

        # Julian Day (UT)
        jd = swe.julday(req.year, req.month, req.day, hour_ut, swe.GREG_CAL)

        # Flags: Swiss Ephemeris + speed
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED

        # Always calculate traditional planets
        planets = [calc_planet(jd, pid, pname, flags) for pid, pname in TRADITIONAL_PLANETS]

        # Optionally include outer planets
        if req.include_outer:
            planets += [calc_planet(jd, pid, pname, flags) for pid, pname in OUTER_PLANETS]

        # Calculate houses
        hsys_byte = req.hsys.encode("utf-8")
        cusps_raw, ascmc = swe.houses(jd, req.lat, req.lon, hsys_byte)

        houses = HouseCusps(
            cusps=[round(c, 4) for c in cusps_raw],
            asc=round(ascmc[0], 4),
            mc=round(ascmc[1], 4),
            armc=round(ascmc[2], 4),
            vertex=round(ascmc[3], 4),
            system=HOUSE_SYSTEM_NAMES.get(req.hsys, req.hsys),
        )

        # Essential dignities for 7 traditional planets
        sun_lon  = planets[0].lon  # Sun is always first in TRADITIONAL_PLANETS
        moon_lon = planets[1].lon
        day      = is_day_chart(sun_lon, houses.asc)

        dignities = [
            PlanetDignity(**vars(calc_dignities(pid, planets[i].lon, day)))
            for i, (pid, _) in enumerate(TRADITIONAL_PLANETS[:7])
        ]

        # Almuten Figuris
        planet_lons = {pid: planets[i].lon for i, (pid, _) in enumerate(TRADITIONAL_PLANETS[:7])}
        alm = calc_almuten(planet_lons, houses.asc, sun_lon, moon_lon, day, jd)
        almuten = AlmutenResponse(
            winner=alm.winner,
            winner_id=alm.winner_id,
            total_scores=alm.total_scores,
            points=[AlmutenPoint(name=p.name, lon=p.lon, scores=p.scores) for p in alm.points],
            lot_of_fortune=alm.lot_of_fortune,
            syzygy_lon=alm.syzygy_lon,
            syzygy_is_new_moon=alm.syzygy_is_new_moon,
            dead_heat=alm.dead_heat,
        )

        # Aspects
        planet_speeds = {pid: planets[i].speed for i, (pid, _) in enumerate(TRADITIONAL_PLANETS[:7])}
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

        # Arabic Parts
        parts_raw = calc_arabic_parts(
            planet_lons, houses.asc, sun_lon, moon_lon, day, jd, cusps_raw
        )
        arabic_parts = [
            ArabicPart(name=p.name, lon=p.lon, sign=p.sign, sign_lon=p.sign_lon,
                       formula=p.formula, diurnal=p.diurnal)
            for p in parts_raw
        ]

        # Planetary Conditions
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

        # Sect (pass cusps for joy calculation)
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

        # Fixed Stars
        fs_raw = calc_fixed_stars(planet_lons, jd)
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

        # Antiscia & Contra-antiscia
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

        # Firdaria
        def _dp(dp):
            return DatePointData(jd=dp.jd, year=dp.year, month=dp.month, day=dp.day)

        def _sub(s):
            return FirdariaSubData(
                planet_id=s.planet_id, planet_name=s.planet_name,
                start=_dp(s.start), end=_dp(s.end), is_current=s.is_current,
            )

        def _period(p):
            return FirdariaPeriodData(
                planet_id=p.planet_id, planet_name=p.planet_name,
                years=p.years,
                start=_dp(p.start), end=_dp(p.end),
                is_current=p.is_current,
                sub_periods=[_sub(s) for s in p.sub_periods],
            )

        fird_raw = calc_firdaria(jd, day)
        firdaria_resp = FirdariaResponse(
            day_chart=fird_raw.day_chart,
            birth_jd=fird_raw.birth_jd,
            periods=[_period(p) for p in fird_raw.periods],
            current_period=_period(fird_raw.current_period) if fird_raw.current_period else None,
            current_sub=_sub(fird_raw.current_sub) if fird_raw.current_sub else None,
        )

        # Annual Profections
        prof_raw = calc_profections(jd, houses.asc, planet_lons)

        def _prof_year(y):
            return ProfectionYearData(
                age=y.age, house=y.house,
                profected_sign_idx=y.profected_sign_idx,
                profected_sign=y.profected_sign,
                profected_asc=y.profected_asc,
                lord_id=y.lord_id, lord_name=y.lord_name,
                start=DatePointData(jd=y.start.jd, year=y.start.year,
                                    month=y.start.month, day=y.start.day),
                end=DatePointData(jd=y.end.jd, year=y.end.year,
                                  month=y.end.month, day=y.end.day),
                is_current=y.is_current,
                activated_planet_ids=y.activated_planet_ids,
            )

        # Monthly profection — add current month to natal response
        mon_raw = calc_monthly_profection(jd, houses.asc, planet_lons)

        def _mon(m):
            return MonthlyProfectionData(
                age_months=m.age_months, month_in_year=m.month_in_year,
                profected_asc=m.profected_asc,
                profected_sign_idx=m.profected_sign_idx,
                profected_sign=m.profected_sign,
                lord_id=m.lord_id, lord_name=m.lord_name,
                start=DatePointData(jd=m.start.jd, year=m.start.year,
                                    month=m.start.month, day=m.start.day),
                end=DatePointData(jd=m.end.jd, year=m.end.year,
                                  month=m.end.month, day=m.end.day),
                is_current=m.is_current,
                activated_planet_ids=m.activated_planet_ids,
            )

        profections_resp = ProfectionResponse(
            current_age=prof_raw.current_age,
            birth_jd=prof_raw.birth_jd,
            years=[_prof_year(y) for y in prof_raw.years],
            current_year=_prof_year(prof_raw.current_year) if prof_raw.current_year else None,
            current_month=_mon(mon_raw.current_entry) if mon_raw.current_entry else None,
        )

        # Accidental Dignities
        acc_raw = calc_accidental_dignities(
            planet_lons, planet_speeds, list(cusps_raw), cond_raw, sect_raw
        )
        # essential_score comes from calc_dignities (already in `dignities` list)
        ess_scores = {pid: dignities[i].score for i, (pid, _) in enumerate(TRADITIONAL_PLANETS[:7])}
        accidental_dignities_resp = [
            AccidentalDignityData(
                planet_id=a.planet_id,
                planet_name=a.planet_name,
                house=a.house,
                is_angular=a.is_angular,
                is_succedent=a.is_succedent,
                is_cadent=a.is_cadent,
                fast_in_motion=a.fast_in_motion,
                slow_in_motion=a.slow_in_motion,
                direct=a.direct,
                retrograde=a.retrograde,
                increasing_light=a.increasing_light,
                decreasing_light=a.decreasing_light,
                cazimi=a.cazimi,
                free_from_beams=a.free_from_beams,
                under_beams=a.under_beams,
                combust=a.combust,
                in_hayz=a.in_hayz,
                in_joy=a.in_joy,
                house_score=a.house_score,
                motion_score=a.motion_score,
                direction_score=a.direction_score,
                light_score=a.light_score,
                solar_score=a.solar_score,
                hayz_score=a.hayz_score,
                joy_score=a.joy_score,
                accidental_score=a.accidental_score,
                essential_score=ess_scores[a.planet_id],
                total_dignity_score=ess_scores[a.planet_id] + a.accidental_score,
            )
            for a in acc_raw
        ]

        # Doryphory (Spear-Bearers)
        dory_raw = calc_doryphory(planet_lons)
        doryphory_resp = DoryphoryResponse(
            morning_bearers=[
                DoryphoryBearerData(
                    planet_id=b.planet_id, planet_name=b.planet_name,
                    elongation=b.elongation, sun_distance=b.sun_distance,
                    bearer_type=b.bearer_type,
                )
                for b in dory_raw.morning_bearers
            ],
            evening_bearers=[
                DoryphoryBearerData(
                    planet_id=b.planet_id, planet_name=b.planet_name,
                    elongation=b.elongation, sun_distance=b.sun_distance,
                    bearer_type=b.bearer_type,
                )
                for b in dory_raw.evening_bearers
            ],
            has_doryphory=dory_raw.has_doryphory,
            bearer_count=dory_raw.bearer_count,
        )

        # Temperament
        temp_raw = calc_temperament(planet_lons, houses.asc, alm.winner_id)
        temperament_resp = TemperamentResponse(
            primary=temp_raw.primary,
            secondary=temp_raw.secondary,
            primary_quality_1=temp_raw.primary_quality_1,
            primary_quality_2=temp_raw.primary_quality_2,
            hot_score=temp_raw.hot_score,
            cold_score=temp_raw.cold_score,
            wet_score=temp_raw.wet_score,
            dry_score=temp_raw.dry_score,
            scores=temp_raw.scores,
            contributions=[
                TemperamentContributionData(
                    factor=c.factor, temperament=c.temperament,
                    quality_1=c.quality_1, quality_2=c.quality_2,
                )
                for c in temp_raw.contributions
            ],
        )

        # Decennials (Paulus Alexandrinus)
        dec_raw = calc_decennials(jd, req.lat, req.lon)

        def _dec_sub(s):
            return DecennialSubData(
                planet_id=s.planet_id, planet_name=s.planet_name,
                duration_years=s.duration_years,
                start=_dp(s.start), end=_dp(s.end),
                is_current=s.is_current,
            )

        def _dec_period(p):
            return DecennialPeriodData(
                planet_id=p.planet_id, planet_name=p.planet_name,
                duration_years=p.duration_years,
                start=_dp(p.start), end=_dp(p.end),
                is_current=p.is_current,
                sub_periods=[_dec_sub(s) for s in p.sub_periods],
            )

        decennials_resp = DecennialsResponse(
            birth_hour_lord_id=dec_raw.birth_hour_lord_id,
            birth_hour_lord_name=dec_raw.birth_hour_lord_name,
            birth_jd=dec_raw.birth_jd,
            cycle_start_jd=dec_raw.cycle_start_jd,
            periods=[_dec_period(p) for p in dec_raw.periods],
            current_period=_dec_period(dec_raw.current_period) if dec_raw.current_period else None,
            current_sub=_dec_sub(dec_raw.current_sub) if dec_raw.current_sub else None,
        )

        # Circumambulations (Valens/Firmicus)
        circ_raw = calc_circumambulations(jd, req.lat, req.lon, planet_lons, day)
        circumambulations_resp = CircumambulationsResponse(
            birth_jd=circ_raw.birth_jd,
            significators=circ_raw.significators,
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
                )
                for e in circ_raw.events
            ],
            obliquity=circ_raw.obliquity,
            armc=circ_raw.armc,
        )

        # Primary Directions
        pd_raw = calc_primary_directions(
            planet_lons, houses.armc, req.lat, jd, key=req.pd_timing_key
        )
        primary_dirs_resp = PrimaryDirectionsResponse(
            directions=[
                PrimaryDirectionData(
                    significator=d.significator,
                    promittor_planet=d.promittor_planet,
                    promittor_planet_id=d.promittor_planet_id,
                    promittor_aspect=d.promittor_aspect,
                    direction=d.direction,
                    arc=d.arc,
                    direction_type=d.direction_type,
                    date_exact=d.date_exact,
                )
                for d in pd_raw.directions
            ],
            ramc=pd_raw.ramc,
            obliquity=pd_raw.obliquity,
            geo_lat=pd_raw.geo_lat,
            timing_key=req.pd_timing_key,
        )

        return NatalChartResponse(
            julian_day=round(jd, 6),
            planets=planets,
            houses=houses,
            dignities=dignities,
            day_chart=day,
            almuten=almuten,
            arabic_parts=arabic_parts,
            aspects=aspects_resp,
            conditions=conditions,
            sect=sect_resp,
            fixed_stars=fixed_stars_resp,
            antiscia=antiscia_resp,
            firdaria=firdaria_resp,
            profections=profections_resp,
            primary_directions=primary_dirs_resp,
            accidental_dignities=accidental_dignities_resp,
            doryphory=doryphory_resp,
            temperament=temperament_resp,
            decennials=decennials_resp,
            circumambulations=circumambulations_resp,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
