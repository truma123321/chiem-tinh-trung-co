"""
Fixed Stars — classical / medieval tradition.

Catalog: 15 Behenian stars + 10 Bonatti additions + 89 Ptolemy/extended stars (114 total).
Positions are computed via pyswisseph fixstar_ut() — automatically precessed
to the chart's Julian Day (no manual precession needed).

Aspect orbs (per Epic 6.6):
  Conjunction  (0°) : 1.0° — classical medieval standard
  Sextile     (60°) : 0.5°
  Square      (90°) : 0.5°
  Trine      (120°) : 0.5°
  Opposition (180°) : 0.5°

Star nature codes (per Bonatti / Ptolemy):
  J = Jupiter-like (benefic)    S = Saturn-like (malefic)
  M = Mars-like (malefic)       V = Venus-like (benefic)
  Me = Mercury-like (neutral)   Su = Sun-like   Lu = Moon-like
  Combined natures use slash: J/V = Jupiter+Venus

Planet IDs: 0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
"""

from __future__ import annotations
from dataclasses import dataclass
import swisseph as swe

# ─── Configuration ────────────────────────────────────────────────────────────

CONJUNCTION_ORB = 1.0   # degrees — classical medieval standard
ASPECT_ORB      = 0.5   # degrees — for non-conjunction aspects

# Aspect angle → (name, orb)
STAR_ASPECTS: dict[int, tuple[str, float]] = {
    0:   ("Conjunction", CONJUNCTION_ORB),
    60:  ("Sextile",     ASPECT_ORB),
    90:  ("Square",      ASPECT_ORB),
    120: ("Trine",       ASPECT_ORB),
    180: ("Opposition",  ASPECT_ORB),
}

# ─── Star catalog ─────────────────────────────────────────────────────────────
# (display_name, se_star_name, ptolemaic_nature)
# Ordered: 15 Behenian + 10 Bonatti + 89 Ptolemy/extended = 114 total

FIXED_STARS: list[tuple[str, str, str]] = [
    # ── 15 Behenian Stars ───────────────────────────────────────────────────
    ("Algol",              "Algol,bePer",               "S/M"),   # β Per — most malefic
    ("Alcyone",            "Alcyone,etaTau",             "M/Lu"),  # η Tau (Pleiades)
    ("Aldebaran",          "Aldebaran,alTau",            "M"),     # α Tau — royal star
    ("Sirius",             "Sirius,alCMa",               "J/M"),   # α CMa — most powerful
    ("Procyon",            "Procyon,alCMi",              "M/Me"),  # α CMi
    ("Regulus",            "Regulus,alLeo",              "J/M"),   # α Leo — royal star
    ("Alkaid",             "Alkaid,etUMa",               "S/M"),   # η UMa (Benetnasch)
    ("Algorab",            "Algorab,deCrv",              "S/M"),   # δ Crv (Crow)
    ("Spica",              "Spica,alVir",                "V/Me"),  # α Vir — most benefic
    ("Arcturus",           "Arcturus,alBoo",             "J/M"),   # α Boo
    ("Alphecca",           "Alphecca,alCrB",             "V/Me"),  # α CrB (Crown)
    ("Antares",            "Antares,alSco",              "M/J"),   # α Sco — royal star
    ("Vega",               "Vega,alLyr",                 "V/Me"),  # α Lyr
    ("Deneb Algedi",       "Deneb Algedi,deCap",         "S/Me"),  # δ Cap
    ("Fomalhaut",          "Fomalhaut,alPsA",            "V/Me"),  # α PsA — royal star
    # ── Additional Classical Stars (Bonatti) ─────────────────────────────────
    ("Achernar",           "Achernar,alEri",             "J"),     # α Eri
    ("Capella",            "Capella,alAur",              "M/Me"),  # α Aur
    ("Rigel",              "Rigel,beOri",                "J/M"),   # β Ori
    ("Bellatrix",          "Bellatrix,gaOri",            "M/Me"),  # γ Ori
    ("El Nath",            "El Nath,beTau",              "M"),     # β Tau
    ("Betelgeuse",         "Betelgeuse,alOri",           "M/Me"),  # α Ori
    ("Pollux",             "Pollux,beGem",               "M"),     # β Gem (malefic twin)
    ("Castor",             "Castor,alGem",               "Me/M"),  # α Gem
    ("Denebola",           "Denebola,beLeo",             "S/V"),   # β Leo
    ("Vindemiatrix",       "Vindemiatrix,epVir",         "S/Me"),  # ε Vir
    # ── Ursa Minor ──────────────────────────────────────────────────────────
    ("Polaris",            "Polaris,alUMi",              "S/V"),   # α UMi — current pole star
    ("Kochab",             "Kochab,beUMi",               "S/M"),   # β UMi
    # ── Cassiopeia ──────────────────────────────────────────────────────────
    ("Schedar",            "Schedar,alCas",              "V/J"),   # α Cas
    ("Caph",               "Caph,beCas",                 "V/J"),   # β Cas
    ("Ruchbah",            "Ruchbah,deCas",              "Me/J"),  # δ Cas
    # ── Andromeda ───────────────────────────────────────────────────────────
    ("Alpheratz",          "Alpheratz,alAnd",            "V/J"),   # α And
    ("Mirach",             "Mirach,beAnd",               "V/J"),   # β And
    ("Almach",             "Almach,gaAnd",               "V/J"),   # γ And
    # ── Perseus ─────────────────────────────────────────────────────────────
    ("Mirfak",             "Mirfak,alPer",               "J/S"),   # α Per
    ("Menkib",             "Menkib,xiPer",               "S/M"),   # ξ Per
    # ── Aries ───────────────────────────────────────────────────────────────
    ("Hamal",              "Hamal,alAri",                "M/S"),   # α Ari
    ("Sheratan",           "Sheratan,beAri",             "M/S"),   # β Ari
    ("Mesartim",           "Mesartim,gaAri",             "M"),     # γ Ari
    # ── Taurus (extra) ──────────────────────────────────────────────────────
    ("Ain",                "Ain,epTau",                  "V/Me"),  # ε Tau (Hyades)
    ("Prima Hyadum",       "Prima Hyadum,gaTau",         "S/M"),   # γ Tau
    ("Secunda Hyadum",     "Secunda Hyadum,daTau",       "S/M"),   # δ Tau
    ("Al Hecka",           "Al Hecka,zetTau",            "M/S"),   # ζ Tau (Bull's tip)
    # ── Orion ───────────────────────────────────────────────────────────────
    ("Mintaka",            "Mintaka,deOri",              "S/Me"),  # δ Ori (belt)
    ("Alnilam",            "Alnilam,epOri",              "J/S"),   # ε Ori (belt)
    ("Alnitak",            "Alnitak,zeOri",              "J/S"),   # ζ Ori (belt)
    ("Saiph",              "Saiph,kaOri",                "S/M"),   # κ Ori
    # ── Auriga ──────────────────────────────────────────────────────────────
    ("Menkalinan",         "Menkalinan,beAur",           "M/Me"),  # β Aur
    # ── Gemini ──────────────────────────────────────────────────────────────
    ("Alhena",             "Alhena,gaGem",               "Me/V"),  # γ Gem
    ("Wasat",              "Wasat,deGem",                "S"),     # δ Gem
    ("Mebsuda",            "Mebsuda,epGem",              "J/S"),   # ε Gem
    ("Tejat Prior",        "Tejat Prior,muGem",          "S/M"),   # μ Gem
    # ── Cancer ──────────────────────────────────────────────────────────────
    ("Acubens",            "Acubens,alCnc",              "S/Me"),  # α Cnc
    ("Asellus Borealis",   "Asellus Borealis,gaCnc",     "S/Me"),  # γ Cnc
    ("Asellus Australis",  "Asellus Australis,daCnc",    "M/S"),   # δ Cnc
    ("Praesepe",           "Praesepe,epCnc",             "M"),     # ε Cnc (Beehive cluster)
    # ── Leo ─────────────────────────────────────────────────────────────────
    ("Algieba",            "Algieba,gaLeo",              "J/V"),   # γ Leo
    ("Zosma",              "Zosma,deLeo",                "S/V"),   # δ Leo
    ("Adhafera",           "Adhafera,zetLeo",            "S/Me"),  # ζ Leo
    ("Algenubi",           "Algenubi,epLeo",             "S/M"),   # ε Leo
    # ── Virgo ───────────────────────────────────────────────────────────────
    ("Porrima",            "Porrima,gaVir",              "V/Me"),  # γ Vir
    # ── Libra ───────────────────────────────────────────────────────────────
    ("Zubenelgenubi",      "Zubenelgenubi,alLib",        "S/M"),   # α Lib
    ("Zubeneschamali",     "Zubeneschamali,beLib",       "J/Me"),  # β Lib
    # ── Scorpius ────────────────────────────────────────────────────────────
    ("Graffias",           "Graffias,beSco",             "M/S"),   # β Sco
    ("Dschubba",           "Dschubba,deSco",             "M/S"),   # δ Sco
    ("Acrab",              "Acrab,piSco",                "M/S"),   # π Sco
    ("Shaula",             "Shaula,laSco",               "M/Me"),  # λ Sco
    ("Lesath",             "Lesath,upsSco",              "M/Me"),  # υ Sco
    # ── Ophiuchus ───────────────────────────────────────────────────────────
    ("Rasalhague",         "Rasalhague,alOph",           "S/V"),   # α Oph
    ("Sabik",              "Sabik,etOph",                "S/V"),   # η Oph
    # ── Sagittarius ─────────────────────────────────────────────────────────
    ("Kaus Australis",     "Kaus Australis,epSgr",       "J/M"),   # ε Sgr
    ("Kaus Media",         "Kaus Media,deSgr",           "J/M"),   # δ Sgr
    ("Nunki",              "Nunki,siSgr",                "J/Me"),  # σ Sgr
    ("Ascella",            "Ascella,zetSgr",             "J/Me"),  # ζ Sgr
    ("Rukbat",             "Rukbat,alSgr",               "J/M"),   # α Sgr
    # ── Capricorn ───────────────────────────────────────────────────────────
    ("Dabih",              "Dabih,beCap",                "S/V"),   # β Cap
    ("Nashira",            "Nashira,gaCap",              "S/J"),   # γ Cap
    # ── Aquarius ────────────────────────────────────────────────────────────
    ("Sadalsuud",          "Sadalsuud,beAqr",            "S/Me"),  # β Aqr
    ("Sadalmelik",         "Sadalmelik,alAqr",           "S/Me"),  # α Aqr
    # ── Pisces ──────────────────────────────────────────────────────────────
    ("Alrescha",           "Alrescha,alPsc",             "M/Me"),  # α Psc
    # ── Cetus ───────────────────────────────────────────────────────────────
    ("Menkar",             "Menkar,alCet",               "S/M"),   # α Cet
    ("Mira",               "Mira,oCet",                  "S"),     # ο Cet (long-period variable)
    ("Difda",              "Difda,beCet",                "S"),     # β Cet
    # ── Eridanus ────────────────────────────────────────────────────────────
    ("Cursa",              "Cursa,beEri",                "J/V"),   # β Eri
    ("Rana",               "Rana,deEri",                 "S/V"),   # δ Eri
    # ── Puppis ──────────────────────────────────────────────────────────────
    ("Naos",               "Naos,zetPup",                "S/M"),   # ζ Pup
    # ── Hydra ───────────────────────────────────────────────────────────────
    ("Alphard",            "Alphard,alHya",              "S/V"),   # α Hya
    ("Minhar al Shuja",    "Minhar al Shuja,zetHya",     "S/M"),   # ζ Hya
    # ── Corvus ──────────────────────────────────────────────────────────────
    ("Gienah",             "Gienah,gaCorv",              "S/M"),   # γ Crv
    ("Alchiba",            "Alchiba,alCrv",              "M/S"),   # α Crv
    # ── Centaurus ───────────────────────────────────────────────────────────
    ("Bungula",            "Bungula,alCen",              "V/J"),   # α Cen
    ("Agena",              "Agena,beCen",                "V/J"),   # β Cen
    # ── Serpens ─────────────────────────────────────────────────────────────
    ("Unukalhai",          "Unukalhai,alSer",            "S/M"),   # α Ser
    # ── Corona Borealis ─────────────────────────────────────────────────────
    ("Nusakan",            "Nusakan,beCrB",              "Me/S"),  # β CrB
    # ── Hercules ────────────────────────────────────────────────────────────
    ("Rasalgethi",         "Rasalgethi,alHer",           "M/V"),   # α Her
    # ── Bootes ──────────────────────────────────────────────────────────────
    ("Izar",               "Izar,epBoo",                 "J/V"),   # ε Boo
    ("Muphrid",            "Muphrid,etBoo",              "V/Me"),  # η Boo
    ("Nekkar",             "Nekkar,beBoo",               "S/Me"),  # β Boo
    ("Seginus",            "Seginus,gaBoo",              "Me/S"),  # γ Boo
    # ── Draco ───────────────────────────────────────────────────────────────
    ("Thuban",             "Thuban,alDra",               "S/M"),   # α Dra (former pole star)
    # ── Ursa Major ──────────────────────────────────────────────────────────
    ("Dubhe",              "Dubhe,alUMa",                "S/M"),   # α UMa (pointer)
    ("Phecda",             "Phecda,gaUMa",               "S/M"),   # γ UMa
    ("Alioth",             "Alioth,epUMa",               "Me/S"),  # ε UMa (brightest)
    ("Mizar",              "Mizar,zetUMa",               "M/S"),   # ζ UMa
    # ── Lyra ────────────────────────────────────────────────────────────────
    ("Sheliak",            "Sheliak,beLyr",              "V/Me"),  # β Lyr
    # ── Aquila ──────────────────────────────────────────────────────────────
    ("Altair",             "Altair,alAql",               "M/J"),   # α Aql
    ("Tarazed",            "Tarazed,gaAql",              "J/M"),   # γ Aql
    # ── Cygnus ──────────────────────────────────────────────────────────────
    ("Deneb",              "Deneb,alCyg",                "V/Me"),  # α Cyg
    ("Sadr",               "Sadr,gaCyg",                 "V/Me"),  # γ Cyg
    ("Gienah Cygni",       "Gienah Cygni,epCyg",         "V/Me"),  # ε Cyg
    # ── Pegasus ─────────────────────────────────────────────────────────────
    ("Scheat",             "Scheat,bePeg",               "M/Me"),  # β Peg
    ("Markab",             "Markab,alPeg",               "M/S"),   # α Peg
    ("Enif",               "Enif,epPeg",                 "M/J"),   # ε Peg
]

_PLANET_NAMES = {
    0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
    4: "Mars", 5: "Jupiter", 6: "Saturn",
}


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class StarAspect:
    star_name:    str
    star_lon:     float   # ecliptic longitude of the star (precessed to JD)
    star_nature:  str     # Ptolemaic nature e.g. "J/M"
    planet_id:    int
    planet_name:  str
    orb:          float   # degrees from exact aspect
    aspect_angle: int     # 0, 60, 90, 120, or 180
    aspect_name:  str     # "Conjunction", "Sextile", "Square", "Trine", "Opposition"


@dataclass
class FixedStarsResult:
    aspects:        list[StarAspect]               # all aspects, sorted by orb
    star_positions: list[tuple[str, float, str]]   # (name, lon, nature)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _arc(a: float, b: float) -> float:
    """Shortest arc between two ecliptic longitudes, 0–180°."""
    d = abs(a - b) % 360.0
    return d if d <= 180.0 else 360.0 - d


# ─── Core calculation ─────────────────────────────────────────────────────────

def calc_fixed_stars(
    planet_lons: dict,   # {0..6: ecliptic longitude}
    jd: float,           # Julian Day (UT) — for precession
) -> FixedStarsResult:
    """
    Compute fixed star positions (precessed to JD) and find all major aspects
    (conjunction, sextile, square, trine, opposition) between planets and stars.

    Orbs: conjunction 1°, all other aspects 0.5°.
    Results sorted by orb (tightest first).
    """
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

    aspects:        list[StarAspect] = []
    star_positions: list[tuple[str, float, str]] = []

    for display_name, se_name, nature in FIXED_STARS:
        try:
            coords, _stnam, _serr = swe.fixstar_ut(se_name, jd, flags)
            star_lon = coords[0]
        except Exception:
            continue   # star not found in catalog — skip silently

        star_positions.append((display_name, round(star_lon, 4), nature))

        for pid, planet_lon in planet_lons.items():
            arc = _arc(planet_lon, star_lon)   # 0–180°

            for angle, (asp_name, orb) in STAR_ASPECTS.items():
                diff = abs(arc - angle)
                if diff <= orb:
                    aspects.append(StarAspect(
                        star_name=display_name,
                        star_lon=round(star_lon, 4),
                        star_nature=nature,
                        planet_id=pid,
                        planet_name=_PLANET_NAMES[pid],
                        orb=round(diff, 4),
                        aspect_angle=angle,
                        aspect_name=asp_name,
                    ))

    aspects.sort(key=lambda a: a.orb)
    return FixedStarsResult(
        aspects=aspects,
        star_positions=star_positions,
    )
