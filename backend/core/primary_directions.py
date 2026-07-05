"""
Primary Directions — Ptolemaic Zodiacal method (Placidean poles).

Theory:
  The diurnal rotation of the celestial sphere carries each natal point to
  new positions.  When a natal point (significator) reaches the position of
  another natal point or its aspect ray (promittor), the arc of movement
  (in degrees of equatorial rotation) equals years of life in the Ptolemaic
  key (1° = 1 year).

Significators implemented: ASC, MC, and all 7 classical planets.
Promittors: 7 classical planets × 8 aspect rays (body + sinister/dexter
            sextile, square, trine + opposition) = 56 promittor points.
Self-directions filtered: a planet significator does not direct its own aspect rays.

Direction types:
  Zodiacal (in zodiaco): Promittor defined by ecliptic longitude ± aspect offset,
      converted to equatorial (ecliptic latitude ignored). OA under sig's pole.
  Mundane (in mundo): Promittor defined by actual equatorial RA/Dec (latitude
      included). Aspect offsets added directly to OA on the equator.
Directions: direct (sphere rotates forward) and converse (backward).

Pole calculation (Placidean doctrine):
  Each significator has its own pole derived from its position in the
  diurnal arc.  The promittor is measured under the same pole.

  pole(S) = arctan(tan(φ) × MD_S / SA_S)

  where MD_S = meridian distance of S from nearest meridian (MC or IC)
        SA_S = corresponding semi-arc (DSA if above, NSA if below horizon)
        DSA  = 90° + AD,   NSA = 90° − AD
        AD   = arcsin(tan(Dec_S) × tan(φ))

  Special cases:
    ASC: always on the horizon → pole = φ  (geographic latitude)
    MC:  always on the meridian → pole = 0°  (promittors use RA, no AD)

Formula:
  OA(P, ρ) = RA(P) − AD(P, ρ)   [Oblique Ascension under pole ρ]
  AD(P, ρ) = arcsin(tan(Dec_P) × tan(ρ))

  Arc S→P (direct)   = (OA(P, ρ_S) − OA(S, ρ_S)) % 360
  Converse arc       = (OA(S, ρ_S) − OA(P, ρ_S)) % 360

Timing keys:
  ptolemy    — 1° arc = 1 Julian year (365.25 days)
  naibod     — 1° arc = mean solar motion rate × Julian year ≈ 360 days
  van_dam    — 1° arc = 1 tropical year (365.2422 days)
  solar_arc  — 1° arc = time for secondary-progressed Sun to travel that arc

Planet IDs: 0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
import swisseph as swe

# ─── Configuration ────────────────────────────────────────────────────────────

MAX_ARC = 90.0   # Ignore arcs > 90 years (configurable)

# ─── Timing key constants ──────────────────────────────────────────────────────

JULIAN_YEAR   = 365.25     # Julian year in days (Ptolemy)
TROPICAL_YEAR = 365.2422   # Mean tropical year in days (Van Dam)
NAIBOD_RATE   = 0.985647   # Mean solar motion in °/day

# Offset from planet's ecliptic longitude to each aspect ray
ASPECT_OFFSETS: dict[str, float] = {
    "body":              0.0,
    "sinister_sextile":  60.0,
    "dexter_sextile":   -60.0,
    "sinister_square":   90.0,
    "dexter_square":    -90.0,
    "sinister_trine":   120.0,
    "dexter_trine":    -120.0,
    "opposition":       180.0,
}

_PLANET_NAMES = {
    0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
    4: "Mars", 5: "Jupiter", 6: "Saturn",
}


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class PrimaryDirection:
    significator: str        # "ASC" | "MC" | planet name
    promittor_planet: str    # planet name
    promittor_planet_id: int
    promittor_aspect: str    # "body" | "sinister_sextile" | …
    direction: str           # "direct" | "converse"
    arc: float               # degrees = years of life (Ptolemy key)
    direction_type: str = "zodiacal"  # "zodiacal" | "mundane"
    date_exact: float = 0.0  # Julian Day of the direction event


@dataclass
class PrimaryDirectionsResult:
    directions: list[PrimaryDirection]   # sorted by arc
    ramc: float
    obliquity: float
    geo_lat: float
    sig_poles: dict[str, float] = None  # Placidean pole per significator (degrees)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _ecl_to_equ(lon_deg: float, eps_deg: float) -> tuple[float, float]:
    """
    Convert ecliptic longitude (β=0) to equatorial (RA, Dec) in degrees.
    Returns (RA, Dec) with RA in [0°, 360°).
    """
    lon = math.radians(lon_deg)
    eps = math.radians(eps_deg)

    sin_dec = math.sin(eps) * math.sin(lon)
    sin_dec = max(-1.0, min(1.0, sin_dec))
    dec = math.asin(sin_dec)

    # atan2 for correct quadrant
    ra = math.atan2(math.cos(eps) * math.sin(lon), math.cos(lon))
    return math.degrees(ra) % 360.0, math.degrees(dec)


def _oa(ra_deg: float, dec_deg: float, pole_deg: float) -> float:
    """
    Oblique Ascension of a point at (RA, Dec) under pole latitude.
    OA = RA − AD  where  sin(AD) = tan(Dec) × tan(pole).
    Circumpolar or never-rising points: AD clamped to ±90°.
    """
    sin_ad = math.tan(math.radians(dec_deg)) * math.tan(math.radians(pole_deg))
    sin_ad = max(-1.0, min(1.0, sin_ad))
    ad = math.degrees(math.asin(sin_ad))
    return (ra_deg - ad) % 360.0


def _placidean_pole(ra: float, dec: float, ramc: float, geo_lat: float) -> float:
    """
    Placidean pole of a significator at (ra, dec).

    Divides each semi-arc proportionally from the meridian to the horizon:
        pole = arctan(tan(φ) × MD / SA)

    MD = meridian distance from nearest meridian (MC or IC), range [0°, 90°]
    SA = corresponding semi-arc (DSA if above horizon, NSA if below)
    DSA = 90° + AD,  NSA = 90° − AD,  AD = arcsin(tan(Dec) × tan(φ))

    Boundary cases:
      At MC  (MD = 0):   pole = 0°  (equatorial, no latitude effect)
      At ASC (MD = DSA): pole = φ   (equals geographic latitude)
    """
    phi = math.radians(geo_lat)

    # Hour angle from upper meridian, positive westward, range (−180°, 180°]
    H = (ramc - ra) % 360.0
    if H > 180.0:
        H -= 360.0

    # Ascensional difference and semi-arcs under φ
    sin_ad = math.tan(math.radians(dec)) * math.tan(phi)
    sin_ad = max(-1.0, min(1.0, sin_ad))
    ad = math.degrees(math.asin(sin_ad))
    dsa = 90.0 + ad   # diurnal semi-arc
    nsa = 90.0 - ad   # nocturnal semi-arc

    abs_H = abs(H)

    if abs_H <= dsa:
        # Above horizon: fraction of diurnal semi-arc from MC
        frac = abs_H / dsa if dsa > 0.0 else 0.0
    else:
        # Below horizon: fraction of nocturnal semi-arc from IC
        dist_ic = 180.0 - abs_H
        frac = dist_ic / nsa if nsa > 0.0 else 0.0

    return math.degrees(math.atan(math.tan(phi) * frac))


def _arc_to_jd(arc: float, jd_birth: float, natal_sun_lon: float, key: str) -> float:
    """
    Convert a primary direction arc (degrees) to a Julian Day of the event.

    ptolemy   : days = arc × 365.25  (Julian year per degree)
    naibod    : days = arc × NAIBOD_RATE × 365.25  ≈ arc × 360  (mean solar motion)
    van_dam   : days = arc × 365.2422  (tropical year per degree)
    solar_arc : Newton-Raphson search for JD where SP Sun has moved `arc` from natal
    """
    if key == "naibod":
        return jd_birth + arc * NAIBOD_RATE * JULIAN_YEAR
    if key == "van_dam":
        return jd_birth + arc * TROPICAL_YEAR
    if key == "solar_arc":
        return _solar_arc_jd(arc, jd_birth, natal_sun_lon)
    # default: ptolemy
    return jd_birth + arc * JULIAN_YEAR


def _solar_arc_jd(arc: float, jd_birth: float, natal_sun_lon: float) -> float:
    """
    Find the calendar JD where the secondary-progressed Sun has moved `arc`
    degrees from the natal Sun longitude.

    In secondary progressions, 1 day after birth (JD) = 1 year of life.
    We find SP-day `d` such that sun_lon(jd_birth + d) − natal_sun_lon = arc,
    then return jd_birth + d × JULIAN_YEAR.

    Uses Newton-Raphson convergence (2–4 iterations typical).
    """
    # Initial estimate via Naibod rate
    sp_day = arc / NAIBOD_RATE
    for _ in range(8):
        r, _ = swe.calc_ut(jd_birth + sp_day, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SPEED)
        current_arc = (r[0] - natal_sun_lon) % 360.0
        speed = r[3]  # degrees/day
        if speed <= 0:
            speed = NAIBOD_RATE  # fallback
        delta = (arc - current_arc)
        # Handle wrap-around near 0°/360°
        if delta > 180:
            delta -= 360.0
        if delta < -180:
            delta += 360.0
        sp_day += delta / speed
        if abs(delta) < 1e-7:
            break
    return jd_birth + sp_day * JULIAN_YEAR


# ─── Core calculation ─────────────────────────────────────────────────────────

def calc_primary_directions(
    planet_lons: dict,   # {0..6: ecliptic longitude}
    ramc: float,         # ARMC from swe.houses() ascmc[2]
    geo_lat: float,      # geographic latitude
    jd: float,           # Julian Day (birth moment) — also used for obliquity
    max_arc: float = MAX_ARC,
    key: str = "ptolemy",  # timing key: "ptolemy" | "naibod" | "van_dam" | "solar_arc"
) -> PrimaryDirectionsResult:
    """
    Compute Ptolemaic zodiacal + mundane primary directions for ASC, MC, and all 7 planets.

    Returns all direction arcs 0 < arc ≤ max_arc, sorted by arc.
    Each direction carries arc (degrees) and date_exact (Julian Day of the event)
    computed under the chosen timing key.
    Self-directions (planet directing its own aspect rays) are excluded.
    """
    # Obliquity
    r_ecl, _ = swe.calc_ut(jd, swe.ECL_NUT, 0)
    eps = r_ecl[0]   # true obliquity

    natal_sun_lon = planet_lons[0]  # needed for solar_arc key

    # ── Equatorial coordinates for all planet significators ──────────────────
    planet_equ: dict[int, tuple[float, float]] = {
        pid: _ecl_to_equ(planet_lons[pid], eps)
        for pid in _PLANET_NAMES
    }

    # ── Placidean poles per significator ─────────────────────────────────────
    # ASC: on the horizon → pole = geo_lat
    # MC:  on the meridian → pole = 0° (promittors use RA, no AD)
    # Planets: Placidean pole from each planet's position in the semi-arc
    sig_poles: dict[str, float] = {"ASC": geo_lat, "MC": 0.0}
    for pid, name in _PLANET_NAMES.items():
        ra, dec = planet_equ[pid]
        sig_poles[name] = _placidean_pole(ra, dec, ramc, geo_lat)

    # ── Significator OA under own pole ───────────────────────────────────────
    sig_oa: dict[str, float] = {
        "ASC": ramc,   # OA(ASC) = RAMC by definition
        "MC":  ramc,   # same origin; promittors use RA
    }
    for pid, name in _PLANET_NAMES.items():
        ra, dec = planet_equ[pid]
        sig_oa[name] = _oa(ra, dec, sig_poles[name])

    # ── Planet ID for each planet significator (for self-direction filter) ───
    _SIG_PLANET_ID: dict[str, int] = {name: pid for pid, name in _PLANET_NAMES.items()}

    directions: list[PrimaryDirection] = []

    for sig_name, sig_origin in sig_oa.items():
        sig_pole = sig_poles[sig_name]
        use_ra_only = (sig_name == "MC")   # MC promittors: pole=0° → OA = RA
        sig_pid = _SIG_PLANET_ID.get(sig_name)  # None for ASC and MC

        for prom_pid, prom_name in _PLANET_NAMES.items():
            # Skip self-directions: planet significator → own aspect rays
            if sig_pid is not None and sig_pid == prom_pid:
                continue

            prom_lon = planet_lons[prom_pid]

            for asp_name, offset in ASPECT_OFFSETS.items():
                asp_lon = (prom_lon + offset) % 360.0

                ra_p, dec_p = _ecl_to_equ(asp_lon, eps)
                # Promittor OA computed under the significator's pole
                prom_oa = ra_p if use_ra_only else _oa(ra_p, dec_p, sig_pole)

                direct_arc   = (prom_oa - sig_origin) % 360.0
                converse_arc = (sig_origin - prom_oa) % 360.0

                if 0.0 < direct_arc <= max_arc:
                    directions.append(PrimaryDirection(
                        significator=sig_name,
                        promittor_planet=prom_name,
                        promittor_planet_id=prom_pid,
                        promittor_aspect=asp_name,
                        direction="direct",
                        arc=round(direct_arc, 4),
                        date_exact=round(_arc_to_jd(direct_arc, jd, natal_sun_lon, key), 4),
                    ))

                if 0.0 < converse_arc <= max_arc:
                    directions.append(PrimaryDirection(
                        significator=sig_name,
                        promittor_planet=prom_name,
                        promittor_planet_id=prom_pid,
                        promittor_aspect=asp_name,
                        direction="converse",
                        arc=round(converse_arc, 4),
                        date_exact=round(_arc_to_jd(converse_arc, jd, natal_sun_lon, key), 4),
                    ))

    # ── Mundane directions (in mundo) ────────────────────────────────────────
    # Actual equatorial coordinates (RA, Dec) including celestial latitude.
    planet_equ_actual: dict[int, tuple[float, float]] = {}
    for pid in _PLANET_NAMES:
        r, _ = swe.calc_ut(jd, pid, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)
        planet_equ_actual[pid] = (r[0], r[1])

    # Placidean poles recomputed from actual RA/Dec (differ when lat ≠ 0)
    mundane_poles: dict[str, float] = {"ASC": geo_lat, "MC": 0.0}
    for pid, name in _PLANET_NAMES.items():
        ra, dec = planet_equ_actual[pid]
        mundane_poles[name] = _placidean_pole(ra, dec, ramc, geo_lat)

    # Significator OA from actual equatorial coords under mundane pole
    mundane_sig_oa: dict[str, float] = {"ASC": ramc, "MC": ramc}
    for pid, name in _PLANET_NAMES.items():
        ra, dec = planet_equ_actual[pid]
        mundane_sig_oa[name] = _oa(ra, dec, mundane_poles[name])

    for sig_name, sig_origin in mundane_sig_oa.items():
        sig_pole    = mundane_poles[sig_name]
        use_ra_only = (sig_name == "MC")
        sig_pid     = _SIG_PLANET_ID.get(sig_name)

        for prom_pid, prom_name in _PLANET_NAMES.items():
            if sig_pid is not None and sig_pid == prom_pid:
                continue

            ra_p, dec_p = planet_equ_actual[prom_pid]
            # Base OA of actual planet body under the significator's pole
            base_oa = ra_p if use_ra_only else _oa(ra_p, dec_p, sig_pole)

            for asp_name, offset in ASPECT_OFFSETS.items():
                # Mundane: offset applied directly on the equator (not ecliptic)
                prom_oa = (base_oa + offset) % 360.0

                direct_arc   = (prom_oa - sig_origin) % 360.0
                converse_arc = (sig_origin - prom_oa) % 360.0

                if 0.0 < direct_arc <= max_arc:
                    directions.append(PrimaryDirection(
                        significator=sig_name,
                        promittor_planet=prom_name,
                        promittor_planet_id=prom_pid,
                        promittor_aspect=asp_name,
                        direction="direct",
                        arc=round(direct_arc, 4),
                        direction_type="mundane",
                        date_exact=round(_arc_to_jd(direct_arc, jd, natal_sun_lon, key), 4),
                    ))

                if 0.0 < converse_arc <= max_arc:
                    directions.append(PrimaryDirection(
                        significator=sig_name,
                        promittor_planet=prom_name,
                        promittor_planet_id=prom_pid,
                        promittor_aspect=asp_name,
                        direction="converse",
                        arc=round(converse_arc, 4),
                        direction_type="mundane",
                        date_exact=round(_arc_to_jd(converse_arc, jd, natal_sun_lon, key), 4),
                    ))

    directions.sort(key=lambda d: d.arc)

    return PrimaryDirectionsResult(
        directions=directions,
        ramc=round(ramc, 4),
        obliquity=round(eps, 6),
        geo_lat=geo_lat,
        sig_poles={k: round(v, 4) for k, v in sig_poles.items()},
    )
