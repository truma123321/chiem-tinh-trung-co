"""
Arabic Parts (Lots) — classical tradition per Bonatti, Liber Astronomiae.

References:
  Bonatti, Liber Astronomiae, Tr. II (Dykes 2010)
  Paulus Alexandrinus, Introductory Matters, Ch. 23
  Abu Ma'shar, Great Introduction to Astrology, IV.2
  Al-Biruni, Elements of the Art of Astrology

Planet IDs match pyswisseph constants:
  0=Sun  1=Moon  2=Mercury  3=Venus  4=Mars  5=Jupiter  6=Saturn

Formula: lot_lon = (A + B - C) % 360
If `diurnal=True` and it's a night chart: swap B and C before computing.
"""

from dataclasses import dataclass, field
from typing import Optional
from core.dignities import DOMICILE, calc_dignities, PLANET_NAMES

# ─── Operand ID constants ──────────────────────────────────────────────────

# House cusps (0–11)
ASC  = 0;  HC2  = 1;  HC3  = 2;  IC   = 3
HC5  = 4;  HC6  = 5;  DSC  = 6;  HC8  = 7
HC9  = 8;  MC   = 9;  HC11 = 10; HC12 = 11

# Planets (12–18) — maps to pyswisseph IDs offset by 12
SUN     = 12
MOON    = 13
MERCURY = 14
VENUS   = 15
MARS    = 16
JUPITER = 17
SATURN  = 18

# Domicile lords of houses (19–30)
H1L  = 19; H2L  = 20; H3L  = 21; H4L  = 22
H5L  = 23; H6L  = 24; H7L  = 25; H8L  = 26
H9L  = 27; H10L = 28; H11L = 29; H12L = 30

# Pre-computed special values (31–36)
LOF    = 31   # Lot of Fortune
LOFL   = 32   # Domicile lord of Fortune's sign
SYZ    = 33   # Prenatal Syzygy longitude
SYZL   = 34   # Domicile lord of Syzygy's sign
SPIRIT = 35   # Lot of Spirit
SPIRL  = 36   # Domicile lord of Spirit's sign

_PLANET_OFFSET = 12   # planet_id = operand_id - 12


# ─── Classical lots table ──────────────────────────────────────────────────
# Format: (name, A, B, C, diurnal)
# Day formula : lot = (A + B - C) % 360
# Night formula: lot = (A + C - B) % 360  [when diurnal=True and night chart]

LOTS = [
    # ── 7 Hermetic Lots (Paulus Alexandrinus / Bonatti) ───────────────────
    ("Fortune",             ASC, MOON,    SUN,     True),
    ("Spirit",              ASC, SUN,     MOON,    True),
    ("Love",                ASC, VENUS,   SPIRIT,  False),   # no D/N swap — Paulus
    ("Necessity",           ASC, LOF,     MERCURY, True),    # D: ASC+F-Mer, N: ASC+Mer-F
    ("Valor",               ASC, LOF,     MARS,    True),    # D: ASC+F-Mars
    ("Victory",             ASC, SPIRIT,  JUPITER, True),    # D: ASC+Sp-Jup
    ("Nemesis",             ASC, LOF,     SATURN,  True),    # D: ASC+F-Sat

    # ── Lots of the 7 Planets (Arabic tradition) ──────────────────────────
    ("Lot of Sun",          ASC, SUN,     SPIRIT,  True),
    ("Lot of Moon",         ASC, LOF,     SPIRIT,  False),   # = Basis
    ("Lot of Mercury",      ASC, MERCURY, MOON,    True),
    ("Lot of Venus",        ASC, VENUS,   MOON,    True),
    ("Lot of Mars",         ASC, MARS,    SPIRIT,  True),
    ("Lot of Jupiter",      ASC, JUPITER, SPIRIT,  True),
    ("Lot of Saturn",       ASC, SPIRIT,  SATURN,  True),

    # ── H1 — Life & Identity ─────────────────────────────────────────────
    ("Life",                ASC, MOON,    SATURN,  True),    # D: ASC+Moon-Sat (Bonatti)
    ("Basis",               ASC, LOF,     SPIRIT,  False),   # ASC+Fortune-Spirit (invariant)
    ("Exaltation",          ASC, LOF,     SUN,     True),    # D: ASC+Fortune-Sun

    # ── H2 — Substance & Wealth ──────────────────────────────────────────
    ("Substance",           ASC, H2L,     MOON,    True),    # D: ASC+H2lord-Moon (Bonatti)
    ("Commerce",            ASC, MERCURY, SATURN,  True),
    ("Poverty",             ASC, LOF,     SATURN,  False),   # invariant

    # ── H3 — Siblings & Short Travel ─────────────────────────────────────
    ("Brothers",            ASC, SATURN,  MOON,    True),    # D: ASC+Sat-Moon (Bonatti)
    ("Short Travel",        ASC, H3L,     SATURN,  True),

    # ── H4 — Parents, Land, Roots ────────────────────────────────────────
    ("Father",              ASC, SUN,     SATURN,  True),    # D: ASC+Sun-Sat (Bonatti day)
    ("Mother",              ASC, MOON,    VENUS,   True),    # D: ASC+Moon-Venus
    ("Inheritance",         ASC, SATURN,  SUN,     True),    # D: ASC+Sat-Sun
    ("Real Estate",         ASC, IC,      H4L,     True),

    # ── H5 — Children & Pleasure ─────────────────────────────────────────
    ("Children",            ASC, JUPITER, MOON,    True),    # D: ASC+Jup-Moon (Bonatti)
    ("Male Children",       ASC, JUPITER, MARS,    True),
    ("Female Children",     ASC, VENUS,   MOON,    False),
    ("Pleasure/Joy",        ASC, LOF,     VENUS,   True),

    # ── H6 — Illness & Servants ──────────────────────────────────────────
    ("Illness",             ASC, MARS,    SATURN,  True),    # D: ASC+Mars-Sat (Bonatti)
    ("Chronic Illness",     ASC, SATURN,  MARS,    True),
    ("Servants",            ASC, MERCURY, MOON,    True),

    # ── H7 — Marriage & Partnerships ─────────────────────────────────────
    ("Marriage (male chart)",  ASC, VENUS,  SATURN, True),   # D: ASC+Venus-Sat (Bonatti)
    ("Marriage (female chart)", ASC, SATURN, VENUS, True),   # D: ASC+Sat-Venus
    ("Divorce",             ASC, VENUS,   MARS,    True),

    # ── H8 — Death & Hidden ──────────────────────────────────────────────
    ("Death",               ASC, HC8,     MOON,    True),    # D: ASC+H8-Moon (Bonatti)
    ("Type of Death",       ASC, SATURN,  SUN,     True),
    ("Danger/Peril",        ASC, MARS,    SATURN,  False),

    # ── H9 — Religion, Travel, Higher Mind ───────────────────────────────
    ("Long Travel",         ASC, SATURN,  LOF,     True),    # D: ASC+Sat-Fortune
    ("Faith",               ASC, MOON,    SUN,     False),   # invariant (= phase)
    ("Divination",          ASC, MERCURY, SUN,     True),

    # ── H10 — Career & Honor ─────────────────────────────────────────────
    ("Honor/Dignity",       MC,  SUN,     SPIRIT,  True),    # D: MC+Sun-Spirit (Bonatti)
    ("Profession",          MC,  MOON,    SUN,     True),    # D: MC+Moon-Sun
    ("Kings/Rulership",     ASC, SPIRIT,  SUN,     True),
    ("Courage in Action",   ASC, MARS,    SPIRIT,  True),

    # ── H11 — Friends & Hopes ────────────────────────────────────────────
    ("Friends",             ASC, MOON,    LOF,     True),    # D: ASC+Moon-Fortune
    ("Hopes/Wishes",        ASC, SPIRIT,  LOF,     False),   # ASC+Spirit-Fortune

    # ── H12 — Hidden Enemies & Confinement ───────────────────────────────
    ("Hidden Enemies",      ASC, SATURN,  MOON,    False),   # invariant
    ("Imprisonment",        ASC, H12L,    SATURN,  True),
    ("Treachery",           ASC, SUN,     SPIRIT,  True),

    # ── Additional lots from Bonatti ──────────────────────────────────────
    ("Victory in War",      ASC, JUPITER, MARS,    True),
    ("Surgery",             ASC, SATURN,  MARS,    True),
    ("Debt/Bankruptcy",     ASC, SATURN,  MERCURY, True),
    ("Captivity",           ASC, H12L,    MOON,    True),
    ("Catastrophe",         ASC, SATURN,  SUN,     False),
    ("Faithfulness",        ASC, MERCURY, SPIRIT,  True),

    # ── Marriage / Partnership variants (Al-Biruni) ───────────────────────
    ("Marriage (7th cusp)", ASC, DSC,     VENUS,   True),    # Al-Biruni: Asc+H7-Venus
    ("Love & Marriage",     ASC, JUPITER, VENUS,   False),   # Paulus: Asc+Jup-Venus (invariant)

    # ── Siblings (Al-Biruni formula) ──────────────────────────────────────
    ("Brothers (Al-Biruni)", ASC, JUPITER, SATURN, True),   # Al-Biruni: Asc+Jup-Sat (D/N)

    # ── Commerce (Al-Biruni formula) ──────────────────────────────────────
    ("Commerce (Al-Biruni)", ASC, MERCURY, SUN,    False),  # Al-Biruni: Asc+Mer-Sun (invariant)

    # ── House-cusp lots (Mashallah / MB / NDV) ────────────────────────────
    ("Goods",               ASC, HC2,     H2L,     True),    # MB: Asc+H2-R2
    ("Desire",              ASC, HC5,     H5L,     True),    # MB: Asc+H5-R5
    ("Mind (H3)",           ASC, HC3,     MERCURY, True),    # Al-Biruni: Asc+H3-Mer
    ("Higher Education",    ASC, HC9,     MERCURY, True),    # Al-Biruni: Asc+H9-Mer
    ("Private Enemies",     ASC, HC12,    H12L,    True),    # NDV: Asc+H12-R12

    # ── Death variant (medieval H8 anchor) ────────────────────────────────
    ("Death (H8+Saturn)",   HC8, SATURN,  MOON,    True),    # Medieval: H8+Sat-Moon

    # ── Most Perilous Year ────────────────────────────────────────────────
    ("Most Perilous Year",  ASC, H8L,     SATURN,  True),    # MB: Asc+R8-Sat

    # ── Mind & Cognition ──────────────────────────────────────────────────
    ("Mind & Understanding", ASC, MARS,   MERCURY, True),   # MB/NDV: Asc+Mars-Mer (D/N)

    # ── Fame, Honor, Increase (Al-Biruni / Bonatti) ───────────────────────
    ("Fame & Honor",        ASC, JUPITER, SUN,     True),    # Al-Biruni: Asc+Jup-Sun (D/N)
    ("Accomplishment",      ASC, SUN,     JUPITER, False),   # Al-Biruni: Asc+Sun-Jup (invariant)

    # ── Agriculture (Al-Biruni) ───────────────────────────────────────────
    ("Agriculture",         ASC, SATURN,  VENUS,   True),    # Al-Biruni: Asc+Sat-Venus (D/N)

    # ── Retribution / Initiative ──────────────────────────────────────────
    ("Retribution",         ASC, SUN,     MARS,    True),    # Al-Biruni: Asc+Sun-Mars (D/N)

    # ── Success ───────────────────────────────────────────────────────────
    ("Success",             ASC, JUPITER, LOF,     True),    # Al-Biruni: Asc+Jup-Fortune (D/N)

    # ── Epic 6.1 — 23 more lots to reach 97 (Bonatti, LA Tr.V) ───────────

    # H1 — Body & Vitality
    ("Injuries",            ASC, MARS,    MOON,    True),    # Bonatti: Asc+Mars-Moon (D)
    ("Memory",              ASC, MOON,    MERCURY, True),    # Bonatti: Asc+Moon-Mer (D) — mental retention

    # H2 — Substance & Material Fortune
    ("Loss and Ruin",       ASC, SATURN,  JUPITER, True),    # Bonatti: Asc+Sat-Jup (D) — financial ruin
    ("Profit and Gain",     ASC, JUPITER, MERCURY, True),    # Bonatti: Asc+Jup-Mer (D) — commercial gain

    # H4 — Parents, Property, Roots
    ("Homeland",            ASC, IC,      MOON,    True),    # Bonatti: Asc+IC-Moon (D) — ancestral home
    ("Patrimony",           ASC, IC,      SATURN,  True),    # Bonatti: Asc+IC-Sat (D) — inherited estate

    # H5 — Children & Pleasure
    ("Games and Gambling",  ASC, VENUS,   MERCURY, True),    # Paulus: Asc+Venus-Mer (D) — speculation
    ("Abundance",           ASC, JUPITER, VENUS,   True),    # Bonatti: Asc+Jup-Venus (D) — prosperity

    # H6 — Illness & Service
    ("Blindness",           ASC, SATURN,  MERCURY, False),   # Medieval: Asc+Sat-Mer invariant — sight afflictions
    ("Pain",                ASC, SATURN,  MARS,    False),   # Bonatti: Asc+Sat-Mars invariant — chronic pain

    # H7 — Marriage & Enemies
    ("Betrothal",           ASC, VENUS,   SUN,     True),    # Bonatti: Asc+Venus-Sun (D) — engagements
    ("Open Enemies",        ASC, MARS,    VENUS,   False),   # Bonatti: Asc+Mars-Venus invariant — public adversaries

    # H8 — Death & Legacy
    ("Fortune at Death",    ASC, LOF,     H8L,     True),    # Bonatti: Asc+Fortune-H8lord (D)
    ("Violent Death",       ASC, MARS,    SUN,     True),    # Bonatti: Asc+Mars-Sun (D)

    # H9 — Travel & Higher Mind
    ("Sea Voyages",         ASC, MOON,    H9L,     True),    # Bonatti: Asc+Moon-H9lord (D) — maritime travel
    ("Dreams",              ASC, MOON,    SPIRIT,  True),    # Bonatti: Asc+Moon-Spirit (D) — prophetic dreams
    ("Wisdom",              ASC, JUPITER, MERCURY, False),   # Bonatti: Asc+Jup-Mer invariant — higher knowledge

    # H10 — Career & Status
    ("Eminence",            MC,  JUPITER, SUN,     True),    # Bonatti: MC+Jup-Sun (D) — high rank
    ("Trade",               ASC, MERCURY, JUPITER, True),    # Bonatti: Asc+Mer-Jup (D) — mercantile activity

    # H11 — Friends & Acquisitions
    ("Gain from Friends",   ASC, H11L,    MOON,    True),    # Bonatti: Asc+H11lord-Moon (D)
    ("Good Luck",           ASC, SPIRIT,  VENUS,   True),    # Bonatti: Asc+Spirit-Venus (D) — fortuitous gains

    # H12 — Hidden Enemies & Loss
    ("Exile",               ASC, LOF,     H12L,    True),    # Bonatti: Asc+Fortune-H12lord (D)
    ("Self-Undoing",        ASC, HC12,    MOON,    True),    # Bonatti: Asc+H12cusp-Moon (D)
]


# ─── Result type ──────────────────────────────────────────────────────────

@dataclass
class ArabicPartResult:
    name: str
    lon: float              # ecliptic longitude 0–360°
    sign: str               # Aries…Pisces
    sign_lon: float         # degrees within sign
    formula: str            # human-readable formula string
    diurnal: bool           # True = formula is diurnal (reversed at night)


# ─── Helpers ──────────────────────────────────────────────────────────────

_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

_OPERAND_LABELS = {
    ASC: "ASC", HC2: "H2",  HC3: "H3",  IC: "IC",
    HC5: "H5",  HC6: "H6",  DSC: "DSC", HC8: "H8",
    HC9: "H9",  MC: "MC",   HC11: "H11", HC12: "H12",
    SUN: "Sun", MOON: "Moon", MERCURY: "Mercury",
    VENUS: "Venus", MARS: "Mars", JUPITER: "Jupiter", SATURN: "Saturn",
    H1L: "H1L", H2L: "H2L", H3L: "H3L", H4L: "H4L",
    H5L: "H5L", H6L: "H6L", H7L: "H7L", H8L: "H8L",
    H9L: "H9L", H10L: "H10L", H11L: "H11L", H12L: "H12L",
    LOF: "Fortune", LOFL: "FortuneL", SYZ: "Syzygy", SYZL: "SyzygyL",
    SPIRIT: "Spirit", SPIRL: "SpiritL",
}


def _domicile_lord_lon(cusp_lon: float, planet_lons: dict) -> Optional[float]:
    """Return the longitude of the domicile lord of the sign containing cusp_lon."""
    sign_idx = int(cusp_lon / 30) % 12
    lord_id = DOMICILE[sign_idx]
    return planet_lons.get(lord_id)


def _resolve_operand(
    op_id: int,
    cusps: list,        # [asc, h2, h3, ic, h5, h6, dsc, h8, h9, mc, h11, h12]
    planet_lons: dict,  # {0: sun_lon, ..., 6: saturn_lon}
    lof: float,
    spirit: float,
    syzygy_lon: float,
) -> Optional[float]:
    """Return the ecliptic longitude for a formula operand ID, or None if unavailable."""
    if 0 <= op_id <= 11:
        return cusps[op_id]
    if 12 <= op_id <= 18:
        pid = op_id - _PLANET_OFFSET
        return planet_lons.get(pid)
    if 19 <= op_id <= 30:
        cusp_idx = op_id - 19        # 0 = H1, ..., 11 = H12
        cusp_lon = cusps[cusp_idx]
        return _domicile_lord_lon(cusp_lon, planet_lons)
    if op_id == LOF:
        return lof
    if op_id == LOFL:
        return _domicile_lord_lon(lof, planet_lons)
    if op_id == SYZ:
        return syzygy_lon
    if op_id == SYZL:
        return _domicile_lord_lon(syzygy_lon, planet_lons)
    if op_id == SPIRIT:
        return spirit
    if op_id == SPIRL:
        return _domicile_lord_lon(spirit, planet_lons)
    return None


# ─── Main calculation ──────────────────────────────────────────────────────

def calc_arabic_parts(
    planet_lons: dict,   # {0: sun_lon, ..., 6: saturn_lon}
    asc: float,
    sun_lon: float,
    moon_lon: float,
    daytime: bool,
    jd: float,
    cusps_raw: list,     # full 13-element cusps from swe.houses (index 1–12)
) -> list[ArabicPartResult]:
    """
    Compute all classical Arabic Parts for a natal chart.

    cusps_raw: the first element of swe.houses() return value — a tuple of
               13 floats where indices 1–12 are H1–H12 cusp longitudes.
    Returns a list of ArabicPartResult, one per lot.
    """
    # Build 12-element cusp list: index 0 = ASC (H1), ..., 11 = H12
    # swe.houses() returns 12-element tuple (index 0=H1, ..., 11=H12)
    cusps = list(cusps_raw[:12])
    cusps[0] = asc   # ensure ASC is consistent with houses.asc

    # Pre-compute Lot of Fortune
    if daytime:
        lof = (asc + moon_lon - sun_lon) % 360
    else:
        lof = (asc + sun_lon - moon_lon) % 360

    # Lot of Spirit is the inverse of Fortune's formula
    if daytime:
        spirit = (asc + sun_lon - moon_lon) % 360
    else:
        spirit = (asc + moon_lon - sun_lon) % 360

    # Prenatal Syzygy (import inline to avoid circular)
    from core.almuten import calc_prenatal_syzygy
    syzygy_lon, _ = calc_prenatal_syzygy(jd)

    results: list[ArabicPartResult] = []

    for name, a_id, b_id, c_id, diurnal in LOTS:
        lon_a = _resolve_operand(a_id, cusps, planet_lons, lof, spirit, syzygy_lon)
        lon_b = _resolve_operand(b_id, cusps, planet_lons, lof, spirit, syzygy_lon)
        lon_c = _resolve_operand(c_id, cusps, planet_lons, lof, spirit, syzygy_lon)

        # Skip if any operand is unavailable (e.g. house lord not in traditional 7)
        if lon_a is None or lon_b is None or lon_c is None:
            continue

        # Day/night formula swap
        if diurnal and not daytime:
            lon_b, lon_c = lon_c, lon_b

        lon = (lon_a + lon_b - lon_c) % 360

        sign_idx = int(lon / 30) % 12
        sign_lon = round(lon % 30, 4)

        # Build human-readable formula string
        if diurnal:
            if daytime:
                formula = f"ASC + {_OPERAND_LABELS.get(b_id, str(b_id))} - {_OPERAND_LABELS.get(c_id, str(c_id))} [D]"
            else:
                formula = f"ASC + {_OPERAND_LABELS.get(c_id, str(c_id))} - {_OPERAND_LABELS.get(b_id, str(b_id))} [N]"
        else:
            formula = f"ASC + {_OPERAND_LABELS.get(b_id, str(b_id))} - {_OPERAND_LABELS.get(c_id, str(c_id))}"

        # Fix formula prefix for non-ASC anchor (e.g. MC-based lots)
        a_label = _OPERAND_LABELS.get(a_id, str(a_id))
        if a_id != ASC:
            formula = formula.replace("ASC", a_label)

        results.append(ArabicPartResult(
            name=name,
            lon=round(lon, 4),
            sign=_SIGNS[sign_idx],
            sign_lon=sign_lon,
            formula=formula,
            diurnal=diurnal,
        ))

    return results
