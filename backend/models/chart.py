"""Pydantic models for chart input/output."""

from pydantic import BaseModel, Field
from typing import Literal


class NatalChartRequest(BaseModel):
    year: int = Field(..., ge=1, le=3000, example=1990)
    month: int = Field(..., ge=1, le=12, example=6)
    day: int = Field(..., ge=1, le=31, example=15)
    hour: int = Field(..., ge=0, le=23, example=10)
    minute: int = Field(..., ge=0, le=59, example=30)
    lat: float = Field(..., ge=-90, le=90, example=41.9)
    lon: float = Field(..., ge=-180, le=180, example=12.5)
    hsys: Literal["A","B","C","E","K","O","P","R","T","V","W","X"] = Field(
        default="B",
        description="B=Alcabitius, R=Regiomontanus, P=Placidus, W=Whole Sign"
    )
    ut_offset: float = Field(default=0.0, ge=-12, le=14)
    include_outer: bool = Field(default=False, description="Include Uranus, Neptune, Pluto, Chiron")
    pd_timing_key: Literal["ptolemy", "naibod", "van_dam", "solar_arc"] = Field(
        default="ptolemy",
        description="Primary direction timing key"
    )


class PlanetPosition(BaseModel):
    id: int
    name: str
    lon: float
    lat: float
    speed: float
    retrograde: bool
    sign: str
    sign_lon: float


class HouseCusps(BaseModel):
    cusps: list[float]
    asc: float
    mc: float
    armc: float
    vertex: float
    system: str


class PlanetDignity(BaseModel):
    planet_id: int
    planet_name: str
    sign_idx: int
    domicile: bool
    exaltation: bool
    triplicity: bool
    term: bool
    face: bool
    peregrine: bool
    detriment: bool
    fall: bool
    score: int
    # Triplicity lord detail (Epic 6.3)
    triplicity_group:           str
    triplicity_day_lord:        int
    triplicity_night_lord:      int
    triplicity_part_lord:       int
    triplicity_day_lord_name:   str
    triplicity_night_lord_name: str
    triplicity_part_lord_name:  str
    triplicity_role:            str   # "day"|"night"|"participating"|"none"


class AlmutenPoint(BaseModel):
    name: str
    lon: float
    scores: dict[str, int]


class AspectData(BaseModel):
    planet_a: int
    planet_b: int
    name_a: str
    name_b: str
    aspect_type: int
    aspect_name: str
    orb: float
    max_orb: float
    applying: bool
    exact: bool
    sinister: bool
    whole_sign: bool
    mutual_reception: bool


class CollectionOfLight(BaseModel):
    collector: int
    collector_name: str
    from_a: int
    from_b: int
    name_a: str
    name_b: str
    orb_a: float
    orb_b: float


class TranslationOfLight(BaseModel):
    translator: int
    translator_name: str
    from_planet: int
    to_planet: int
    from_name: str
    to_name: str
    sep_orb: float
    app_orb: float


class AspectsResponse(BaseModel):
    aspects: list[AspectData]
    collections: list[CollectionOfLight]
    translations: list[TranslationOfLight]


class PlanetConditionData(BaseModel):
    planet_id: int
    planet_name: str
    sun_distance: float
    cazimi: bool
    combust: bool
    under_beams: bool
    free_from_beams: bool
    oriental: bool
    occidental: bool
    elongation: float


class MoonConditionData(BaseModel):
    void_of_course: bool
    next_aspect_planet: int | None = None
    next_aspect_planet_name: str | None = None
    next_aspect_type: int | None = None
    next_aspect_orb: float | None = None


class ConditionsResponse(BaseModel):
    planet_conditions: list[PlanetConditionData]
    moon: MoonConditionData


class PlanetSectData(BaseModel):
    planet_id: int
    planet_name: str
    sect: str            # "diurnal" | "nocturnal" | "common"
    in_sect: bool
    above_horizon: bool
    sign_masculine: bool
    in_hayz: bool
    in_joy: bool         # planet is in its joy house (Epic 6.4)
    joy_house: int       # 1-based house this planet rejoices in


class SectResponse(BaseModel):
    day_chart: bool
    planet_sects: list[PlanetSectData]


class StarAspectData(BaseModel):
    star_name:    str
    star_lon:     float
    star_nature:  str
    planet_id:    int
    planet_name:  str
    orb:          float
    aspect_angle: int    # 0, 60, 90, 120, or 180
    aspect_name:  str    # "Conjunction" | "Sextile" | "Square" | "Trine" | "Opposition"


class StarPositionData(BaseModel):
    name: str
    lon: float
    nature: str


class FixedStarsResponse(BaseModel):
    aspects:        list[StarAspectData]
    star_positions: list[StarPositionData]


class AntisciaPointData(BaseModel):
    planet_id: int
    planet_name: str
    lon: float
    antiscion: float
    contra_antiscion: float


class AntisciaAspectData(BaseModel):
    planet_a: int
    name_a: str
    planet_b: int
    name_b: str
    aspect_type: str   # "antiscion" | "contra_antiscion"
    aspect_angle: int  # 0, 60, 90, 120, 180
    aspect_name: str   # "Conjunction", "Sextile", "Square", "Trine", "Opposition"
    orb: float


class AntisciaResponse(BaseModel):
    points: list[AntisciaPointData]
    aspects: list[AntisciaAspectData]


class TemperamentContributionData(BaseModel):
    factor: str
    temperament: str
    quality_1: str
    quality_2: str


class TemperamentResponse(BaseModel):
    primary: str
    secondary: str
    primary_quality_1: str
    primary_quality_2: str
    hot_score: int
    cold_score: int
    wet_score: int
    dry_score: int
    scores: dict
    contributions: list[TemperamentContributionData]


class DatePointData(BaseModel):
    jd: float
    year: int
    month: int
    day: int


class FirdariaSubData(BaseModel):
    planet_id: int
    planet_name: str
    start: DatePointData
    end: DatePointData
    is_current: bool


class FirdariaPeriodData(BaseModel):
    planet_id: int
    planet_name: str
    years: int
    start: DatePointData
    end: DatePointData
    is_current: bool
    sub_periods: list[FirdariaSubData]


class FirdariaResponse(BaseModel):
    day_chart: bool
    birth_jd: float
    periods: list[FirdariaPeriodData]
    current_period: FirdariaPeriodData | None = None
    current_sub: FirdariaSubData | None = None


class ProfectionYearData(BaseModel):
    age: int
    house: int
    profected_sign_idx: int
    profected_sign: str
    profected_asc: float
    lord_id: int
    lord_name: str
    start: DatePointData
    end: DatePointData
    is_current: bool
    activated_planet_ids: list[int]


class MonthlyProfectionData(BaseModel):
    age_months: int
    month_in_year: int
    profected_asc: float
    profected_sign_idx: int
    profected_sign: str
    lord_id: int
    lord_name: str
    start: DatePointData
    end: DatePointData
    is_current: bool
    activated_planet_ids: list[int]


class MonthlyProfectionResult(BaseModel):
    total_months: int
    total_years: int
    month_in_year: int
    entries: list[MonthlyProfectionData]
    current_entry: MonthlyProfectionData | None = None
    birth_jd: float


class DailyProfectionData(BaseModel):
    age_days: int
    day_in_month: int
    profected_asc: float
    profected_sign_idx: int
    profected_sign: str
    lord_id: int
    lord_name: str
    start: DatePointData
    end: DatePointData
    is_current: bool
    activated_planet_ids: list[int]


class DailyProfectionResult(BaseModel):
    total_days: int
    total_months: int
    day_in_month: int
    entries: list[DailyProfectionData]
    current_entry: DailyProfectionData | None = None
    birth_jd: float


class ProfectionResponse(BaseModel):
    current_age: int
    birth_jd: float
    years: list[ProfectionYearData]
    current_year: ProfectionYearData | None = None
    current_month: MonthlyProfectionData | None = None


class PrimaryDirectionData(BaseModel):
    significator: str
    promittor_planet: str
    promittor_planet_id: int
    promittor_aspect: str
    direction: str
    arc: float
    direction_type: str = "zodiacal"  # "zodiacal" | "mundane"
    date_exact: float = 0.0           # Julian Day of the direction event


class PrimaryDirectionsResponse(BaseModel):
    directions: list[PrimaryDirectionData]
    ramc: float
    obliquity: float
    geo_lat: float
    timing_key: str = "ptolemy"


class NatalPlanetPlacement(BaseModel):
    """Natal planet located in a return chart's house."""
    planet_id: int
    planet_name: str
    natal_lon: float
    return_house: int   # 1-based


class ReturnToNatalAspect(BaseModel):
    """Aspect between a return chart planet and a natal chart planet."""
    return_planet_id: int
    return_planet_name: str
    natal_planet_id: int
    natal_planet_name: str
    aspect_type: int
    aspect_name: str
    orb: float
    max_orb: float
    applying: bool
    exact: bool


class ReturnNatalOverlay(BaseModel):
    """Overlay of the natal chart onto a return chart."""
    natal_planets: list[PlanetPosition]        # natal positions (7 traditional)
    placements: list[NatalPlanetPlacement]     # natal planets in return houses
    cross_aspects: list[ReturnToNatalAspect]   # return ↔ natal aspects


class ArabicPart(BaseModel):
    name: str
    lon: float
    sign: str
    sign_lon: float
    formula: str
    diurnal: bool


class AlmutenResponse(BaseModel):
    winner: str
    winner_id: int
    total_scores: dict[str, int]
    points: list[AlmutenPoint]
    lot_of_fortune: float
    syzygy_lon: float
    syzygy_is_new_moon: bool
    dead_heat: bool


class AccidentalDignityData(BaseModel):
    planet_id:   int
    planet_name: str
    house:       int

    # Condition flags
    is_angular:       bool
    is_succedent:     bool
    is_cadent:        bool
    fast_in_motion:   bool
    slow_in_motion:   bool
    direct:           bool
    retrograde:       bool
    increasing_light: bool
    decreasing_light: bool
    cazimi:           bool
    free_from_beams:  bool
    under_beams:      bool
    combust:          bool
    in_hayz:          bool
    in_joy:           bool

    # Score breakdown
    house_score:      int
    motion_score:     int
    direction_score:  int
    light_score:      int
    solar_score:      int
    hayz_score:       int
    joy_score:        int

    # Totals
    accidental_score:    int
    essential_score:     int
    total_dignity_score: int


class DoryphoryBearerData(BaseModel):
    planet_id:    int
    planet_name:  str
    elongation:   float   # (planet_lon − sun_lon) % 360, raw (0–360°)
    sun_distance: float   # arc distance from Sun (0–orb degrees)
    bearer_type:  str     # "morning" | "evening"


class DoryphoryResponse(BaseModel):
    morning_bearers: list[DoryphoryBearerData]
    evening_bearers: list[DoryphoryBearerData]
    has_doryphory:   bool
    bearer_count:    int


class NatalChartResponse(BaseModel):
    julian_day: float
    planets: list[PlanetPosition]
    houses: HouseCusps
    dignities: list[PlanetDignity]
    day_chart: bool
    almuten: AlmutenResponse
    arabic_parts: list[ArabicPart]
    aspects: AspectsResponse
    conditions: ConditionsResponse
    sect: SectResponse
    fixed_stars: FixedStarsResponse
    antiscia: AntisciaResponse
    firdaria: FirdariaResponse
    profections: ProfectionResponse
    primary_directions: PrimaryDirectionsResponse
    accidental_dignities: list[AccidentalDignityData]
    doryphory: DoryphoryResponse
    temperament: TemperamentResponse
    decennials: "DecennialsResponse | None" = None
    circumambulations: "CircumambulationsResponse | None" = None


# ── Solar Return models ────────────────────────────────────────────────────────

class SolarReturnRequest(BaseModel):
    # Birth moment (computes natal Sun longitude)
    year: int = Field(..., ge=1, le=3000, example=1990)
    month: int = Field(..., ge=1, le=12, example=6)
    day: int = Field(..., ge=1, le=31, example=15)
    hour: int = Field(..., ge=0, le=23, example=10)
    minute: int = Field(..., ge=0, le=59, example=30)
    ut_offset: float = Field(default=0.0, ge=-12, le=14)
    # Return parameters
    return_year: int = Field(..., ge=1, le=3000, example=2025)
    return_lat: float = Field(..., ge=-90, le=90, example=41.9)
    return_lon: float = Field(..., ge=-180, le=180, example=12.5)
    hsys: Literal["A","B","C","E","K","O","P","R","T","V","W","X"] = Field(
        default="B",
        description="House system for the return chart"
    )
    include_outer: bool = Field(default=False)
    include_natal_overlay: bool = Field(default=False, description="Include return-to-natal aspects and natal house placements")


class ReturnDatetime(BaseModel):
    """UTC calendar breakdown of the exact return moment."""
    jd: float
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: float
    utc_iso: str


class SolarReturnResponse(BaseModel):
    """Full chart computed at the exact solar return moment/location."""
    return_datetime: ReturnDatetime
    natal_sun_lon: float           # reference longitude used for the search
    # Chart data at return moment
    planets: list[PlanetPosition]
    houses: HouseCusps
    dignities: list[PlanetDignity]
    day_chart: bool
    almuten: AlmutenResponse
    arabic_parts: list[ArabicPart]
    aspects: AspectsResponse
    conditions: ConditionsResponse
    sect: SectResponse
    fixed_stars: FixedStarsResponse
    antiscia: AntisciaResponse
    natal_overlay: ReturnNatalOverlay | None = None


# ── Lunar Return models ────────────────────────────────────────────────────────

class LunarReturnRequest(BaseModel):
    # Birth moment (computes natal Moon longitude)
    year: int = Field(..., ge=1, le=3000, example=1990)
    month: int = Field(..., ge=1, le=12, example=6)
    day: int = Field(..., ge=1, le=31, example=15)
    hour: int = Field(..., ge=0, le=23, example=10)
    minute: int = Field(..., ge=0, le=59, example=30)
    ut_offset: float = Field(default=0.0, ge=-12, le=14)
    # Return parameters
    return_year: int = Field(..., ge=1, le=3000, example=2025)
    return_lat: float = Field(..., ge=-90, le=90, example=41.9)
    return_lon: float = Field(..., ge=-180, le=180, example=12.5)
    hsys: Literal["A","B","C","E","K","O","P","R","T","V","W","X"] = Field(
        default="B",
        description="House system for the return charts"
    )
    include_outer: bool = Field(default=False)
    include_natal_overlay: bool = Field(default=False, description="Include return-to-natal aspects and natal house placements")


class LunarReturnEntry(BaseModel):
    """Full chart at one lunar return moment."""
    return_datetime: ReturnDatetime
    natal_moon_lon: float
    planets: list[PlanetPosition]
    houses: HouseCusps
    dignities: list[PlanetDignity]
    day_chart: bool
    almuten: AlmutenResponse
    arabic_parts: list[ArabicPart]
    aspects: AspectsResponse
    conditions: ConditionsResponse
    sect: SectResponse
    fixed_stars: FixedStarsResponse
    antiscia: AntisciaResponse
    natal_overlay: ReturnNatalOverlay | None = None


class LunarReturnsResponse(BaseModel):
    """All lunar returns for the requested year."""
    natal_moon_lon: float
    return_year: int
    count: int                       # number of returns found (typically 12–13)
    returns: list[LunarReturnEntry]


# ── Secondary Progressions models ─────────────────────────────────────────────

# ── Solar Arc Direction models ─────────────────────────────────────────────────

class SolarArcRequest(BaseModel):
    # Birth moment
    year: int = Field(..., ge=1, le=3000, example=1990)
    month: int = Field(..., ge=1, le=12, example=6)
    day: int = Field(..., ge=1, le=31, example=15)
    hour: int = Field(..., ge=0, le=23, example=10)
    minute: int = Field(..., ge=0, le=59, example=30)
    ut_offset: float = Field(default=0.0, ge=-12, le=14)
    # Birth location (for natal ASC/MC)
    lat: float = Field(..., ge=-90, le=90, example=41.9)
    lon: float = Field(..., ge=-180, le=180, example=12.5)
    # Target progression date
    prog_year: int = Field(..., ge=1, le=3000, example=2025)
    prog_month: int = Field(..., ge=1, le=12, example=6)
    prog_day: int = Field(..., ge=1, le=31, example=15)
    # Options
    hsys: Literal["A","B","C","E","K","O","P","R","T","V","W","X"] = Field(default="B")
    include_outer: bool = Field(default=False)
    orb: float = Field(default=2.0, ge=0.0, le=10.0, description="Max orb in degrees (= years)")


class DirectedPoint(BaseModel):
    name: str
    natal_lon: float
    directed_lon: float
    sign: str
    sign_lon: float


class DirectedAspect(BaseModel):
    directed_name: str
    directed_lon: float
    natal_name: str
    natal_lon: float
    aspect_type: int
    aspect_name: str
    orb: float
    max_orb: float
    applying: bool
    exact_jd: float | None = None   # real calendar JD of exact hit


class SolarArcResponse(BaseModel):
    birth_jd: float
    target_jd: float
    solar_arc: float            # degrees of arc applied (= prog_sun - natal_sun)
    directed_points: list[DirectedPoint]   # 9 points: 7 planets + ASC + MC
    aspects: list[DirectedAspect]          # directed-to-natal aspects within orb


class SecondaryProgressionRequest(BaseModel):
    # Birth moment
    year: int = Field(..., ge=1, le=3000, example=1990)
    month: int = Field(..., ge=1, le=12, example=6)
    day: int = Field(..., ge=1, le=31, example=15)
    hour: int = Field(..., ge=0, le=23, example=10)
    minute: int = Field(..., ge=0, le=59, example=30)
    ut_offset: float = Field(default=0.0, ge=-12, le=14)
    # Birth location (for natal chart and default progressed houses)
    lat: float = Field(..., ge=-90, le=90, example=41.9)
    lon: float = Field(..., ge=-180, le=180, example=12.5)
    # Target progression date (the real calendar date to progress TO)
    prog_year: int = Field(..., ge=1, le=3000, example=2025)
    prog_month: int = Field(..., ge=1, le=12, example=6)
    prog_day: int = Field(..., ge=1, le=31, example=15)
    # Options
    hsys: Literal["A","B","C","E","K","O","P","R","T","V","W","X"] = Field(
        default="B",
        description="House system for progressed houses"
    )
    include_outer: bool = Field(default=False)
    include_progressed_houses: bool = Field(default=True)
    include_natal_overlay: bool = Field(default=True, description="Include progressed-to-natal aspects")
    include_lots: bool = Field(default=False, description="Include Arabic Parts computed from progressed chart")


class ProgressedLunation(BaseModel):
    """Progressed lunar phase data."""
    phase_angle: float          # 0-360°: progressed Moon - progressed Sun
    phase_name: str             # e.g. "Full Moon", "First Quarter"
    last_new_moon_jd: float     # progressed JD (= days after birth) of last prog NM
    last_new_moon_age: float    # symbolic age (years of life) at last prog NM
    last_full_moon_jd: float    # progressed JD of last prog FM
    last_full_moon_age: float   # symbolic age at last prog FM


class SecondaryProgressionsResponse(BaseModel):
    """Progressed chart for the target date."""
    birth_jd: float
    target_jd: float            # real JD of the target calendar date
    progressed_jd: float        # symbolic JD (birth_jd + age_years in days)
    age_years: float            # age in years at target date
    progressed_planets: list[PlanetPosition]
    progressed_houses: HouseCusps | None = None
    natal_overlay: ReturnNatalOverlay | None = None
    lunation: ProgressedLunation
    arabic_parts: list[ArabicPart] | None = None   # None unless include_lots=True


# ── Tertiary Progressions models ──────────────────────────────────────────────

class TertiaryProgressionRequest(BaseModel):
    # Birth moment
    year: int = Field(..., ge=1, le=3000, example=1990)
    month: int = Field(..., ge=1, le=12, example=6)
    day: int = Field(..., ge=1, le=31, example=15)
    hour: int = Field(..., ge=0, le=23, example=10)
    minute: int = Field(..., ge=0, le=59, example=30)
    ut_offset: float = Field(default=0.0, ge=-12, le=14)
    # Birth location (for progressed houses)
    lat: float = Field(..., ge=-90, le=90, example=41.9)
    lon: float = Field(..., ge=-180, le=180, example=12.5)
    # Target date
    prog_year: int = Field(..., ge=1, le=3000, example=2025)
    prog_month: int = Field(..., ge=1, le=12, example=6)
    prog_day: int = Field(..., ge=1, le=31, example=15)
    # Options
    month_type: Literal["sidereal", "synodic"] = Field(
        default="sidereal",
        description="sidereal=27.32d (default), synodic=29.53d"
    )
    hsys: Literal["A","B","C","E","K","O","P","R","T","V","W","X"] = Field(default="B")
    include_outer: bool = Field(default=False)
    include_progressed_houses: bool = Field(default=True)
    include_natal_overlay: bool = Field(default=True)
    include_lots: bool = Field(default=False, description="Include Arabic Parts computed from progressed chart")


class TertiaryProgressionsResponse(BaseModel):
    birth_jd: float
    target_jd: float
    progressed_jd: float        # birth_jd + age_months  (days)
    age_months: float           # number of lunar months since birth
    month_type: str             # "sidereal" | "synodic"
    month_days: float           # actual days per lunar month used
    progressed_planets: list[PlanetPosition]
    progressed_houses: HouseCusps | None = None
    natal_overlay: ReturnNatalOverlay | None = None
    lunation: ProgressedLunation
    arabic_parts: list[ArabicPart] | None = None   # None unless include_lots=True


# ── Transits models ────────────────────────────────────────────────────────────

class TransitRequest(BaseModel):
    # Birth moment
    year: int = Field(..., ge=1, le=3000, example=1990)
    month: int = Field(..., ge=1, le=12, example=6)
    day: int = Field(..., ge=1, le=31, example=15)
    hour: int = Field(..., ge=0, le=23, example=10)
    minute: int = Field(..., ge=0, le=59, example=30)
    ut_offset: float = Field(default=0.0, ge=-12, le=14)
    # Birth location (for natal houses)
    lat: float = Field(..., ge=-90, le=90, example=41.9)
    lon: float = Field(..., ge=-180, le=180, example=12.5)
    # Transit date (noon UTC used as canonical moment)
    transit_year: int = Field(..., ge=1, le=3000, example=2025)
    transit_month: int = Field(..., ge=1, le=12, example=6)
    transit_day: int = Field(..., ge=1, le=31, example=15)
    # Options
    hsys: Literal["A","B","C","E","K","O","P","R","T","V","W","X"] = Field(default="B")
    include_outer: bool = Field(default=False)
    orb: float = Field(default=2.0, ge=0.0, le=10.0, description="Max orb for transit-to-natal aspects")
    cusp_orb: float = Field(default=1.0, ge=0.0, le=5.0, description="Max orb for cusp conjunctions")
    exact_max_days: float = Field(default=90.0, ge=1.0, le=730.0, description="Search window for exact hit date (days)")
    include_cusp_conjunctions: bool = Field(default=True)


class TransitNatalAspect(BaseModel):
    transit_planet_id: int
    transit_planet_name: str
    transit_lon: float
    natal_planet_id: int
    natal_planet_name: str
    natal_lon: float
    aspect_type: int
    aspect_name: str
    orb: float
    max_orb: float
    applying: bool
    exact_jd: float | None = None   # JD of exact hit (within exact_max_days)


class CuspConjunction(BaseModel):
    transit_planet_id: int
    transit_planet_name: str
    transit_lon: float
    cusp_number: int            # 1-12
    cusp_lon: float
    orb: float
    applying: bool
    exact_jd: float | None = None


class TransitsResponse(BaseModel):
    natal_jd: float
    transit_jd: float           # JD of the transit date (noon UTC)
    transit_planets: list[PlanetPosition]
    natal_planets: list[PlanetPosition]
    aspects: list[TransitNatalAspect]
    cusp_conjunctions: list[CuspConjunction]


# ── Epic 5.2: Transit Timing ───────────────────────────────────────────────────

class TransitTimingRequest(BaseModel):
    # Birth moment
    year:      int   = Field(..., ge=1, le=3000, example=1990)
    month:     int   = Field(..., ge=1, le=12,   example=6)
    day:       int   = Field(..., ge=1, le=31,   example=15)
    hour:      int   = Field(..., ge=0, le=23,   example=10)
    minute:    int   = Field(..., ge=0, le=59,   example=30)
    ut_offset: float = Field(default=0.0, ge=-12, le=14)
    # Date range for timing search
    start_year:  int = Field(..., ge=1, le=3000, example=2025)
    start_month: int = Field(..., ge=1, le=12,   example=1)
    start_day:   int = Field(..., ge=1, le=31,   example=1)
    end_year:    int = Field(..., ge=1, le=3000, example=2025)
    end_month:   int = Field(..., ge=1, le=12,   example=12)
    end_day:     int = Field(..., ge=1, le=31,   example=31)
    # Transit planet set
    include_outer:  bool = Field(default=False, description="Add Uranus, Neptune, Pluto, Chiron")
    include_nodes:  bool = Field(default=True,  description="Add True Node and Mean Node")
    include_moon:   bool = Field(default=True,  description="Include Moon (generates many hits)")
    # Station filtering
    include_stations: bool  = Field(default=True, description="Include retrograde station events near natal planets")
    station_orb:      float = Field(default=1.0, ge=0.0, le=10.0, description="Orb (°) within which a station counts as 'near' a natal planet")


class ExactHit(BaseModel):
    transit_planet_id:   int
    transit_planet_name: str
    natal_planet_id:     int
    natal_planet_name:   str
    natal_lon:           float
    aspect_type:         int     # 0–4 Ptolemaic
    aspect_name:         str
    exact_jd:            float
    exact_date:          str     # YYYY-MM-DD
    hit_number:          int     # 1, 2, or 3 within this (planet, natal, aspect) group in the range
    total_hits:          int     # total hits in this group within the date range
    retrograde_at_exact: bool


class StationEvent(BaseModel):
    transit_planet_id:    int
    transit_planet_name:  str
    station_jd:           float
    station_date:         str
    station_type:         str    # "SR" (stationary retrograde) or "SD" (stationary direct)
    station_lon:          float
    nearest_natal_planet: str   | None = None
    nearest_natal_lon:    float | None = None
    orb_to_nearest:       float | None = None


class TransitTimingResponse(BaseModel):
    natal_jd:   float
    start_jd:   float
    end_jd:     float
    exact_hits: list[ExactHit]
    stations:   list[StationEvent]


# ── Epic 5.3: Ingresses ────────────────────────────────────────────────────────

class IngressRequest(BaseModel):
    # Date range
    start_year:  int = Field(..., ge=1, le=3000, example=2025)
    start_month: int = Field(..., ge=1, le=12,   example=1)
    start_day:   int = Field(..., ge=1, le=31,   example=1)
    end_year:    int = Field(..., ge=1, le=3000, example=2025)
    end_month:   int = Field(..., ge=1, le=12,   example=12)
    end_day:     int = Field(..., ge=1, le=31,   example=31)
    # Planet set
    include_outer: bool = Field(default=False, description="Add Uranus, Neptune, Pluto, Chiron")
    include_nodes: bool = Field(default=False, description="Add True Node and Mean Node")
    include_moon:  bool = Field(default=False, description="Include Moon (ingresses every ~2.5 days)")


class IngressEventModel(BaseModel):
    planet_id:    int
    planet_name:  str
    sign:         str    # zodiac sign being entered
    from_sign:    str    # zodiac sign being exited
    boundary_lon: float  # 0, 30, 60 … 330
    ingress_jd:   float
    ingress_date: str    # YYYY-MM-DD
    ingress_time: str    # HH:MM UTC
    retrograde:   bool   # True = retrograde ingress (re-entering previous sign)


class IngressResponse(BaseModel):
    start_jd:  float
    end_jd:    float
    ingresses: list[IngressEventModel]


# ── Profections endpoint models (Epic 7.1) ─────────────────────────────────────

class ProfectionsRequest(BaseModel):
    year:      int   = Field(..., ge=1,  le=3000, example=1990)
    month:     int   = Field(..., ge=1,  le=12,   example=6)
    day:       int   = Field(..., ge=1,  le=31,   example=15)
    hour:      float = Field(..., ge=0,  lt=24,   example=10.0)
    minute:    int   = Field(..., ge=0,  lt=60,   example=30)
    lat:       float = Field(..., ge=-90, le=90,  example=41.9)
    lon:       float = Field(..., ge=-180, le=180, example=12.5)
    hsys:      str   = Field(default="P", example="P")
    ut_offset: float = Field(default=0.0, example=0)
    period:    str   = Field(default="annual", example="monthly")


class ProfectionsEndpointResponse(BaseModel):
    period:    str   # "annual" | "monthly" | "daily"
    birth_jd:  float
    annual:    ProfectionResponse | None = None
    monthly:   MonthlyProfectionResult | None = None
    daily:     DailyProfectionResult   | None = None


# ── Decennials endpoint models (Epic 7.2) ──────────────────────────────────────

class DecennialSubData(BaseModel):
    planet_id:      int
    planet_name:    str
    duration_years: float
    start:          DatePointData
    end:            DatePointData
    is_current:     bool


class DecennialPeriodData(BaseModel):
    planet_id:      int
    planet_name:    str
    duration_years: int
    start:          DatePointData
    end:            DatePointData
    is_current:     bool
    sub_periods:    list[DecennialSubData]


class DecennialsRequest(BaseModel):
    year:      int   = Field(..., ge=1,  le=3000, example=1990)
    month:     int   = Field(..., ge=1,  le=12,   example=6)
    day:       int   = Field(..., ge=1,  le=31,   example=15)
    hour:      float = Field(..., ge=0,  lt=24,   example=10.0)
    minute:    int   = Field(..., ge=0,  lt=60,   example=30)
    lat:       float = Field(..., ge=-90, le=90,  example=41.9)
    lon:       float = Field(..., ge=-180, le=180, example=12.5)
    ut_offset: float = Field(default=0.0, example=0)


class DecennialsResponse(BaseModel):
    birth_hour_lord_id:   int
    birth_hour_lord_name: str
    birth_jd:             float
    cycle_start_jd:       float
    periods:              list[DecennialPeriodData]
    current_period:       DecennialPeriodData | None = None
    current_sub:          DecennialSubData    | None = None


# ── Circumambulations endpoint models (Epic 7.3) ───────────────────────────────

class SubPeriodData(BaseModel):
    planet_id:     int
    planet_name:   str
    start_date:    DatePointData
    end_date:      DatePointData
    duration_days: float


class CircumambulationEventData(BaseModel):
    significator:       str
    promittor_id:       int
    promittor_name:     str
    aspect_angle:       int
    aspect_name:        str
    arc:                float
    age_years:          float
    event_date:         DatePointData
    is_past:            bool
    # Valens extensions
    is_loosing_of_bond: bool = False
    bonification:       str | None = None
    maltreatment:       str | None = None
    sub_periods:        list[SubPeriodData] | None = None


class CircumambulationsRequest(BaseModel):
    year:               int   = Field(..., ge=1,  le=3000, example=1990)
    month:              int   = Field(..., ge=1,  le=12,   example=6)
    day:                int   = Field(..., ge=1,  le=31,   example=15)
    hour:               float = Field(..., ge=0,  lt=24,   example=10.0)
    minute:             int   = Field(..., ge=0,  lt=60,   example=30)
    lat:                float = Field(..., ge=-90, le=90,  example=41.9)
    lon:                float = Field(..., ge=-180, le=180, example=12.5)
    hsys:               str   = Field(default="P", example="P")
    ut_offset:          float = Field(default=0.0, example=0)
    include_sub_periods: bool = Field(default=False)


class CircumambulationsResponse(BaseModel):
    birth_jd:     float
    significators: list[str]
    events:       list[CircumambulationEventData]
    obliquity:    float
    armc:         float
    mc_lon:       float = 0.0
    mc_oa:        float = 0.0


# ── Synastry models (Epic 8.1) ─────────────────────────────────────────────────

class BirthDataInput(BaseModel):
    year:      int   = Field(..., ge=1,  le=3000, example=1990)
    month:     int   = Field(..., ge=1,  le=12,   example=6)
    day:       int   = Field(..., ge=1,  le=31,   example=15)
    hour:      int   = Field(..., ge=0,  le=23,   example=10)
    minute:    int   = Field(..., ge=0,  le=59,   example=30)
    lat:       float = Field(..., ge=-90, le=90,  example=41.9)
    lon:       float = Field(..., ge=-180, le=180, example=12.5)
    hsys:      str   = Field(default="P", example="P")
    ut_offset: float = Field(default=0.0, example=0)


class SynastryRequest(BaseModel):
    chart_a: BirthDataInput
    chart_b: BirthDataInput


class SynastryAspectData(BaseModel):
    planet_a_id:   int
    planet_a_name: str
    planet_b_id:   int
    planet_b_name: str
    aspect_angle:  int
    aspect_name:   str
    orb:           float
    max_orb:       float


class OverlayPlanetData(BaseModel):
    planet_id:   int
    planet_name: str
    planet_lon:  float
    house:       int     # 1–12


class SynastryAntisciaAspectData(BaseModel):
    source:       str    # "A" or "B"
    planet_id:    int
    planet_name:  str
    shadow_type:  str    # "antiscion" | "contra_antiscion"
    shadow_lon:   float
    target_id:    int
    target_name:  str
    target_lon:   float
    aspect_angle: int
    aspect_name:  str
    orb:          float


class SynastryResponse(BaseModel):
    cross_aspects:         list[SynastryAspectData]
    a_planets_in_b_houses: list[OverlayPlanetData]
    b_planets_in_a_houses: list[OverlayPlanetData]
    antiscia_aspects:      list[SynastryAntisciaAspectData]


# ── Composite Chart models (Epic 8.2) ──────────────────────────────────────────

class CompositeRequest(BaseModel):
    chart_a: BirthDataInput
    chart_b: BirthDataInput


class CompositePlanetData(BaseModel):
    planet_id:   int
    planet_name: str
    lon:         float
    sign:        str
    sign_lon:    float
    retrograde:  bool


class CompositeAspectData(BaseModel):
    planet_a_id:   int
    planet_a_name: str
    planet_b_id:   int
    planet_b_name: str
    aspect_angle:  int
    aspect_name:   str
    orb:           float
    max_orb:       float


class CompositeResponse(BaseModel):
    planets:  list[CompositePlanetData]
    asc:      float
    asc_sign: str
    mc:       float
    mc_sign:  str
    aspects:  list[CompositeAspectData]


# ── Horary Judgment models (Epic 9.1) ──────────────────────────────────────────

class HoraryCheckData(BaseModel):
    factor:      str
    label:       str
    present:     bool
    description: str


class HoraryRequest(BaseModel):
    year:      int
    month:     int
    day:       int
    hour:      int
    minute:    int
    lat:       float
    lon:       float
    hsys:      str   = "P"
    ut_offset: float = 0.0


class HoraryResponse(BaseModel):
    asc:        float
    asc_sign:   str
    asc_degree: float

    moon_lon:           float
    moon_sign:          str
    moon_voc:           bool
    next_aspect_planet: str   | None
    next_aspect_name:   str   | None
    next_aspect_orb:    float | None

    saturn_lon:   float
    saturn_house: int

    via_combusta: bool

    checks:         list[HoraryCheckData]
    radicality:     str
    negative_count: int


# ── Horary Perfection models (Epic 9.2) ────────────────────────────────────────

class HorarySignificatorData(BaseModel):
    planet_id:   int
    planet_name: str
    lon:         float
    sign:        str
    sign_lon:    float
    retrograde:  bool
    house:       int


class HoraryAspectRelationData(BaseModel):
    angle:       int
    aspect_name: str
    orb:         float
    applying:    bool


class HoraryPerfectionData(BaseModel):
    perfected:   bool
    method:      str   | None
    translator:  str   | None
    collector:   str   | None
    description: str


class HoraryProhibitionData(BaseModel):
    prohibited:        bool
    prohibitor_name:   str | None
    prohibitor_aspect: str | None
    description:       str


class HoraryRefranationData(BaseModel):
    refranation: bool
    planet_name: str | None
    description: str


class HoraryFrustrationData(BaseModel):
    frustrated:      bool
    frustrator_name: str | None
    description:     str


class HoraryReceptionData(BaseModel):
    querent_in_quesited_domicile:   bool
    quesited_in_querent_domicile:   bool
    querent_in_quesited_exaltation: bool
    quesited_in_querent_exaltation: bool
    mutual_reception:               bool


class HoraryPerfectionRequest(BaseModel):
    year:           int
    month:          int
    day:            int
    hour:           int
    minute:         int
    lat:            float
    lon:            float
    hsys:           str   = "P"
    ut_offset:      float = 0.0
    querent_house:  int   = 1
    quesited_house: int   = 7


class HoraryTimingData(BaseModel):
    days_raw: float
    unit:     str
    value:    float
    modality: str
    note:     str


class HoraryPerfectionResponse(BaseModel):
    querent_house:         int
    quesited_house:        int
    querent_significator:  HorarySignificatorData
    quesited_significator: HorarySignificatorData
    same_lord:             bool
    direct_aspect:         HoraryAspectRelationData | None
    perfection:            HoraryPerfectionData
    prohibition:           HoraryProhibitionData
    refranation:           HoraryRefranationData
    frustration:           HoraryFrustrationData
    reception:             HoraryReceptionData
    timing:                HoraryTimingData | None = None


# ── Horary Essential Dignities models (Epic 9.3) ───────────────────────────────

class DignityDetailData(BaseModel):
    domicile:    bool
    exaltation:  bool
    triplicity:  bool
    term:        bool
    face:        bool
    detriment:   bool
    fall:        bool
    peregrine:   bool
    score:       int
    strength:    str    # "Dignified" | "Peregrine" | "Debilitated"


class SignificatorDignityData(BaseModel):
    planet_id:   int
    planet_name: str
    lon:         float
    sign:        str
    sign_lon:    float
    dignity:     DignityDetailData


class HoraryDignityRequest(BaseModel):
    year:           int
    month:          int
    day:            int
    hour:           int
    minute:         int
    lat:            float
    lon:            float
    hsys:           str   = "P"
    ut_offset:      float = 0.0
    querent_house:  int   = 1
    quesited_house: int   = 7


class HoraryDignityResponse(BaseModel):
    day_chart:             bool
    querent_house:         int
    quesited_house:        int
    querent_significator:  SignificatorDignityData
    quesited_significator: SignificatorDignityData
    moon_dignity:          DignityDetailData


# ── Horary Turned Chart models (Epic 10.4) ─────────────────────────────────────

class TurnedHouseData(BaseModel):
    turned_house: int
    natal_house:  int
    cusp_lon:     float
    lord_id:      int
    lord_name:    str


class HoraryTurnedRequest(BaseModel):
    year:           int
    month:          int
    day:            int
    hour:           int
    minute:         int
    lat:            float
    lon:            float
    hsys:           str = "P"
    ut_offset:      float = 0.0
    from_house:     int = Field(..., ge=1, le=12, description="Perspective house (1-12)")
    quesited_house: int = Field(..., ge=1, le=12, description="Quesited house in turned chart (1-12)")
    querent_house:  int = Field(default=1, ge=1, le=12)


class HoraryTurnedResponse(BaseModel):
    from_house:              int
    from_house_topic:        str
    querent_house:           int
    original_quesited_house: int
    turned_quesited_house:   int
    turned_lord_id:          int
    turned_lord_name:        str
    explanation:             str
    all_turned_houses:       list[TurnedHouseData]
