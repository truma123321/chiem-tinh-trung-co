"""
Sect (Hayresis) — classical / medieval tradition.

Chart Sect:
  Day chart  : Sun above horizon — (sun_lon - asc) % 360 >= 180
  Night chart: Sun below horizon

Planet Sect (classical):
  Diurnal (Solar) sect : Sun, Jupiter, Saturn
  Nocturnal (Lunar) sect: Moon, Venus, Mars
  Mercury              : common — diurnal if oriental (ahead of Sun in zodiac),
                         nocturnal if occidental

Sign Polarity (Ptolemy):
  Masculine (diurnal) signs : Aries(0), Gemini(2), Leo(4), Libra(6),
                               Sagittarius(8), Aquarius(10)  — sign_idx % 2 == 0
  Feminine (nocturnal) signs: Taurus(1), Cancer(3), Virgo(5), Scorpio(7),
                               Capricorn(9), Pisces(11)       — sign_idx % 2 == 1

Hemisphere:
  Above horizon : (planet_lon - asc) % 360 >= 180  (houses 7-12)
  Below horizon : (planet_lon - asc) % 360 <  180  (houses 1-6)

Hayz (fully in sect, per Bonatti / Lilly):
  Diurnal planet + day chart  + above horizon + masculine sign → in hayz
  Nocturnal planet + night chart + below horizon + feminine sign → in hayz
  Mercury: above horizon in day chart (diurnal mode) OR below in night chart
           (nocturnal mode), AND in matching sign polarity

In-sect (basic, single condition):
  Planet's sect matches chart sect (diurnal planet in day, nocturnal in night).
  Mercury in hayz-compatible hemisphere/sign also counted as in-sect.

Planet IDs: 0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
"""

from __future__ import annotations
from dataclasses import dataclass

# ─── Joy houses ──────────────────────────────────────────────────────────────
# Each planet rejoices in a specific house (ancient doctrine).

JOY_HOUSE: dict[int, int] = {
    2: 1,    # Mercury — H1
    1: 3,    # Moon    — H3
    3: 5,    # Venus   — H5
    4: 6,    # Mars    — H6
    0: 9,    # Sun     — H9
    5: 11,   # Jupiter — H11
    6: 12,   # Saturn  — H12
}


def planet_house(lon: float, cusps: list[float]) -> int:
    """Return the 1-based house number for the given ecliptic longitude.

    cusps[0] = H1 cusp longitude … cusps[11] = H12 cusp longitude.
    Handles the 0°/360° wrap-around.
    """
    lon = lon % 360.0
    for i in range(12):
        c_start = cusps[i] % 360.0
        c_end   = cusps[(i + 1) % 12] % 360.0
        if c_end > c_start:
            if c_start <= lon < c_end:
                return i + 1
        else:                        # segment spans the 0°/360° boundary
            if lon >= c_start or lon < c_end:
                return i + 1
    return 1                         # fallback (shouldn't happen)


# ─── Sect membership ────────────────────────────────────────────────────────

SOLAR_SECT  = frozenset([0, 5, 6])   # Sun, Jupiter, Saturn
LUNAR_SECT  = frozenset([1, 3, 4])   # Moon, Venus, Mars
# Mercury (2) = common

_PLANET_NAMES = {
    0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
    4: "Mars", 5: "Jupiter", 6: "Saturn",
}


# ─── Result types ────────────────────────────────────────────────────────────

@dataclass
class PlanetSect:
    planet_id: int
    planet_name: str
    sect: str            # "diurnal" | "nocturnal" | "common"
    in_sect: bool        # planet's sect matches chart sect
    above_horizon: bool  # in upper hemisphere (houses 7-12)
    sign_masculine: bool # in a masculine (odd-indexed) sign
    in_hayz: bool        # fully in sect (planet + hemisphere + sign all aligned)
    in_joy: bool         # planet is in its joy house (Epic 6.4)
    joy_house: int       # the house this planet rejoices in (1-based)


@dataclass
class SectResult:
    day_chart: bool
    planet_sects: list[PlanetSect]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _above_horizon(planet_lon: float, asc: float) -> bool:
    """True when planet is in the upper hemisphere (houses 7-12)."""
    return (planet_lon - asc) % 360.0 >= 180.0


def _is_masculine_sign(lon: float) -> bool:
    """Aries(0), Gemini(2), Leo(4), Libra(6), Sagittarius(8), Aquarius(10)."""
    return (int(lon / 30.0) % 12) % 2 == 0


def _planet_sect(pid: int, planet_lon: float, sun_lon: float) -> str:
    if pid in SOLAR_SECT:
        return "diurnal"
    if pid in LUNAR_SECT:
        return "nocturnal"
    # Mercury: oriental (ahead of Sun) → diurnal; occidental → nocturnal
    elong = (planet_lon - sun_lon) % 360.0
    return "diurnal" if elong < 180.0 else "nocturnal"


# ─── Core calculation ─────────────────────────────────────────────────────────

def calc_sect(
    planet_lons:  dict,                    # {0..6: ecliptic longitude}
    asc:          float,                   # Ascendant longitude
    day_chart:    bool,                    # True if day chart (Sun above horizon)
    house_cusps:  list[float] | None = None,  # 12 cusp longitudes for joy calc
) -> SectResult:
    """
    Compute sect membership, in-sect status, hayz, and joy for all 7 traditional planets.

    Pass house_cusps to enable in_joy calculation; omit to leave in_joy=False.
    """
    sun_lon = planet_lons[0]
    planet_sects: list[PlanetSect] = []

    for pid in range(7):
        lon   = planet_lons[pid]
        sect  = _planet_sect(pid, lon, sun_lon)
        above = _above_horizon(lon, asc)
        masc  = _is_masculine_sign(lon)

        # ── In sect (basic) ──────────────────────────────────────────────────
        if sect == "diurnal":
            in_sect = day_chart
        elif sect == "nocturnal":
            in_sect = not day_chart
        else:
            in_sect = True

        # ── Hayz ─────────────────────────────────────────────────────────────
        if day_chart:
            in_hayz = (sect == "diurnal") and above and masc
        else:
            in_hayz = (sect == "nocturnal") and (not above) and (not masc)

        # ── Joy ──────────────────────────────────────────────────────────────
        pjoy = JOY_HOUSE.get(pid, -1)
        if house_cusps is not None:
            h      = planet_house(lon, house_cusps)
            in_joy = h == pjoy
        else:
            in_joy = False

        planet_sects.append(PlanetSect(
            planet_id=pid,
            planet_name=_PLANET_NAMES[pid],
            sect=sect,
            in_sect=in_sect,
            above_horizon=above,
            sign_masculine=masc,
            in_hayz=in_hayz,
            in_joy=in_joy,
            joy_house=pjoy,
        ))

    return SectResult(day_chart=day_chart, planet_sects=planet_sects)
