"""
Horary Perfection Analysis — Epic 9.2.

Determines whether a horary question will be "perfected" (answered) by
analysing the relationship between the querent significator (lord of H1)
and the quesited significator (lord of the relevant house).

Methods of Perfection:
  1. Direct Application   — Q applies to S (or S to Q) by conjunction/aspect
  2. Translation of Light — planet T separates from one sig and applies to other
  3. Collection of Light  — a heavier planet C receives applications from both
  4. Reception            — mutual dignity between Q and S

Impediments:
  - Prohibition  — third planet intercepts Q before Q reaches S
  - Refranation  — applying significator is retrograde (may not complete)
  - Frustration  — third planet conjoins the quesited before Q arrives

References:
  William Lilly, Christian Astrology, Books 1 & 2.
  Anthony Louis, Horary Astrology Plain & Simple.

Planet IDs: 0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
"""

from __future__ import annotations
from dataclasses import dataclass

# ─── Constants ────────────────────────────────────────────────────────────────

_PLANET_NAMES: dict[int, str] = {
    0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
    4: "Mars", 5: "Jupiter", 6: "Saturn",
}

_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

# Sign modality for Lilly timing (sign_idx → modality)
_MODALITY: dict[int, str] = {
    0: "cardinal", 3: "cardinal", 6: "cardinal", 9: "cardinal",   # Aries/Cancer/Libra/Cap
    1: "fixed",    4: "fixed",    7: "fixed",    10: "fixed",       # Tau/Leo/Sco/Aqu
    2: "mutable",  5: "mutable",  8: "mutable",  11: "mutable",     # Gem/Vir/Sag/Pis
}

# Lilly unit multipliers: cardinal=1 day, fixed=7 (weeks), mutable=30 (months)
_MODALITY_UNIT: dict[str, tuple[str, float]] = {
    "cardinal": ("days",   1.0),
    "fixed":    ("weeks",  7.0),
    "mutable":  ("months", 30.0),
}

# Traditional domicile lords (sign_idx → planet_id)
_SIGN_LORDS: dict[int, int] = {
    0:  4,   # Aries       → Mars
    1:  3,   # Taurus      → Venus
    2:  2,   # Gemini      → Mercury
    3:  1,   # Cancer      → Moon
    4:  0,   # Leo         → Sun
    5:  2,   # Virgo       → Mercury
    6:  3,   # Libra       → Venus
    7:  4,   # Scorpio     → Mars
    8:  5,   # Sagittarius → Jupiter
    9:  6,   # Capricorn   → Saturn
    10: 6,   # Aquarius    → Saturn
    11: 5,   # Pisces      → Jupiter
}

# Classical exaltation signs (planet_id → sign_idx)
_EXALTATION_SIGNS: dict[int, int] = {
    0: 0,    # Sun    exalted in Aries
    1: 1,    # Moon   exalted in Taurus
    2: 5,    # Mercury exalted in Virgo
    3: 11,   # Venus  exalted in Pisces
    4: 9,    # Mars   exalted in Capricorn
    5: 3,    # Jupiter exalted in Cancer
    6: 6,    # Saturn exalted in Libra
}

HORARY_ORBS: dict[int, float] = {
    0:   8.0,   # Conjunction
    60:  4.0,   # Sextile
    90:  7.0,   # Square
    120: 7.0,   # Trine
    180: 8.0,   # Opposition
}

ASPECT_NAMES: dict[int, str] = {
    0: "Conjunction", 60: "Sextile", 90: "Square",
    120: "Trine", 180: "Opposition",
}


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class SignificatorInfo:
    planet_id:   int
    planet_name: str
    lon:         float
    sign:        str
    sign_lon:    float
    retrograde:  bool
    house:       int       # which house it occupies


@dataclass
class AspectRelation:
    angle:       int
    aspect_name: str
    orb:         float
    applying:    bool      # True = applying, False = separating


@dataclass
class PerfectionResult:
    perfected:   bool
    method:      str | None   # "Direct Application" | "Translation of Light" |
                               # "Collection of Light" | "Reception"
    translator:  str | None   # planet name for Translation of Light
    collector:   str | None   # planet name for Collection of Light
    description: str


@dataclass
class ProhibitionResult:
    prohibited:        bool
    prohibitor_name:   str | None
    prohibitor_aspect: str | None
    description:       str


@dataclass
class RefranationResult:
    refranation: bool
    planet_name: str | None
    description: str


@dataclass
class FrustrationResult:
    frustrated:      bool
    frustrator_name: str | None
    description:     str


@dataclass
class ReceptionDetail:
    querent_in_quesited_domicile:   bool
    quesited_in_querent_domicile:   bool
    querent_in_quesited_exaltation: bool
    quesited_in_querent_exaltation: bool
    mutual_reception:               bool   # true if reception in both directions


@dataclass
class TimingEstimate:
    """
    Lilly-style timing estimate for when perfection will occur.

    days_raw    : raw calculation — orb / daily approach rate (days)
    unit        : "days" | "weeks" | "months"  (based on sign modality)
    value       : days_raw expressed in the given unit
    modality    : "cardinal" | "fixed" | "mutable" (from querent's sign)
    note        : human-readable explanation
    """
    days_raw: float
    unit:     str
    value:    float
    modality: str
    note:     str


@dataclass
class HoraryPerfectionResult:
    querent_house:         int
    quesited_house:        int
    querent_significator:  SignificatorInfo
    quesited_significator: SignificatorInfo
    same_lord:             bool              # both houses share the same ruler
    direct_aspect:         AspectRelation | None
    perfection:            PerfectionResult
    prohibition:           ProhibitionResult
    refranation:           RefranationResult
    frustration:           FrustrationResult
    reception:             ReceptionDetail
    timing:                TimingEstimate | None  # None if no direct application


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _sign_info(lon: float) -> tuple[str, float]:
    idx = int(lon / 30.0) % 12
    return _SIGNS[idx], round(lon % 30.0, 4)


def _arc(lon_a: float, lon_b: float) -> float:
    """Shortest arc between two longitudes, [0°, 180°]."""
    diff = abs(lon_a - lon_b) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff


def _find_house(lon: float, cusps: list[float]) -> int:
    """Return 1-based house number."""
    for h in range(12):
        c1 = cusps[h]
        c2 = cusps[(h + 1) % 12]
        if c2 > c1:
            if c1 <= lon < c2:
                return h + 1
        else:
            if lon >= c1 or lon < c2:
                return h + 1
    return 1


def _house_lord(house_num: int, cusps: list[float]) -> int:
    """Return planet_id of the traditional lord of house_num (1-based)."""
    cusp_lon = cusps[house_num - 1]
    sign_idx = int(cusp_lon / 30) % 12
    return _SIGN_LORDS[sign_idx]


def _is_applying(
    lon_a: float, sp_a: float,
    lon_b: float, sp_b: float,
    angle: int,
) -> bool:
    """
    Return True if the aspect arc between A and B is closing (applying).
    Uses a 1-day forward projection.
    """
    curr = abs(_arc(lon_a, lon_b) - angle)
    proj = abs(_arc(lon_a + sp_a, lon_b + sp_b) - angle)
    return proj < curr


def _find_aspect(
    lon_a: float, sp_a: float,
    lon_b: float, sp_b: float,
) -> tuple[int, float, bool] | None:
    """
    Return (angle, orb, applying) for the first aspect within orbs, or None.
    Checks in canonical order: 0°, 60°, 90°, 120°, 180°.
    """
    arc = _arc(lon_a, lon_b)
    for angle, max_orb in sorted(HORARY_ORBS.items()):
        orb = abs(arc - angle)
        if orb <= max_orb:
            applying = _is_applying(lon_a, sp_a, lon_b, sp_b, angle)
            return angle, round(orb, 4), applying
    return None


def _days_to_exact(
    lon_a: float, sp_a: float,
    lon_b: float, sp_b: float,
    angle: int,
) -> float:
    """
    Linear estimate of days until the aspect arc equals `angle`.
    Returns float('inf') if the aspect is separating.
    """
    curr = abs(_arc(lon_a, lon_b) - angle)
    proj = abs(_arc(lon_a + sp_a, lon_b + sp_b) - angle)
    daily_close = curr - proj   # positive = applying
    if daily_close <= 0:
        return float("inf")
    return curr / daily_close


def _reception(
    pid_a: int, lon_a: float,
    pid_b: int, lon_b: float,
) -> tuple[bool, bool, bool, bool]:
    """
    Return (a_in_b_dom, b_in_a_dom, a_in_b_exalt, b_in_a_exalt).

    a_in_b_dom  : A occupies a sign ruled by B.
    b_in_a_dom  : B occupies a sign ruled by A.
    a_in_b_exalt: A occupies B's exaltation sign.
    b_in_a_exalt: B occupies A's exaltation sign.
    """
    sign_a = int(lon_a / 30) % 12
    sign_b = int(lon_b / 30) % 12

    a_in_b_dom   = (_SIGN_LORDS[sign_a] == pid_b)
    b_in_a_dom   = (_SIGN_LORDS[sign_b] == pid_a)
    a_in_b_exalt = (_EXALTATION_SIGNS.get(pid_b) == sign_a)
    b_in_a_exalt = (_EXALTATION_SIGNS.get(pid_a) == sign_b)

    return a_in_b_dom, b_in_a_dom, a_in_b_exalt, b_in_a_exalt


# ─── Core calculation ──────────────────────────────────────────────────────────

def calc_horary_perfection(
    planet_lons:    dict[int, float],
    planet_speeds:  dict[int, float],
    cusps:          list[float],
    querent_house:  int = 1,
    quesited_house: int = 7,
) -> HoraryPerfectionResult:
    """
    Analyse horary perfection between querent and quesited significators.

    planet_lons    : {planet_id: ecliptic_longitude} for 7 classical planets
    planet_speeds  : {planet_id: daily motion in degrees}
    cusps          : 12 house cusp longitudes (1-based, index 0 = cusp of H1)
    querent_house  : house number of the querent (default 1)
    quesited_house : house number of the quesited (the matter asked about)
    """
    # ── Significators ─────────────────────────────────────────────────────────
    q_id = _house_lord(querent_house,  cusps)
    s_id = _house_lord(quesited_house, cusps)
    same_lord = (q_id == s_id)

    q_lon = planet_lons[q_id]
    q_sp  = planet_speeds[q_id]
    s_lon = planet_lons[s_id]
    s_sp  = planet_speeds[s_id]

    def _sig_info(pid: int) -> SignificatorInfo:
        lon = planet_lons[pid]
        sign, sign_lon = _sign_info(lon)
        return SignificatorInfo(
            planet_id=pid,
            planet_name=_PLANET_NAMES[pid],
            lon=round(lon, 4),
            sign=sign,
            sign_lon=sign_lon,
            retrograde=(planet_speeds[pid] < 0),
            house=_find_house(lon, cusps),
        )

    q_sig = _sig_info(q_id)
    s_sig = _sig_info(s_id)

    # ── Direct aspect ─────────────────────────────────────────────────────────
    direct_aspect:      AspectRelation | None = None
    applying_direct:    bool  = False
    direct_remaining:   float = float("inf")
    applying_angle:     int   = 0

    if same_lord:
        # Same lord rules both houses: trivial conjunction at 0° orb
        direct_aspect   = AspectRelation(angle=0, aspect_name="Conjunction", orb=0.0, applying=True)
        applying_direct = True
        direct_remaining = 0.0
    else:
        asp = _find_aspect(q_lon, q_sp, s_lon, s_sp)
        if asp:
            angle, orb, applying = asp
            direct_aspect = AspectRelation(
                angle=angle, aspect_name=ASPECT_NAMES[angle],
                orb=orb, applying=applying,
            )
            if applying:
                applying_direct  = True
                direct_remaining = orb
                applying_angle   = angle

    # ── Reception ─────────────────────────────────────────────────────────────
    a_dom, b_dom, a_exalt, b_exalt = _reception(q_id, q_lon, s_id, s_lon)
    mutual = (a_dom or a_exalt) and (b_dom or b_exalt)
    reception = ReceptionDetail(
        querent_in_quesited_domicile=a_dom,
        quesited_in_querent_domicile=b_dom,
        querent_in_quesited_exaltation=a_exalt,
        quesited_in_querent_exaltation=b_exalt,
        mutual_reception=mutual,
    )

    # ── Translation of Light ──────────────────────────────────────────────────
    translator_id: int | None = None
    if not applying_direct and not same_lord:
        for t_id in range(7):
            if t_id == q_id or t_id == s_id:
                continue
            t_lon = planet_lons[t_id]
            t_sp  = planet_speeds[t_id]
            asp_tq = _find_aspect(t_lon, t_sp, q_lon, q_sp)
            asp_ts = _find_aspect(t_lon, t_sp, s_lon, s_sp)
            # T separating from Q, applying to S
            if asp_tq and not asp_tq[2] and asp_ts and asp_ts[2]:
                translator_id = t_id
                break
            # T separating from S, applying to Q
            if asp_ts and not asp_ts[2] and asp_tq and asp_tq[2]:
                translator_id = t_id
                break

    # ── Collection of Light ───────────────────────────────────────────────────
    collector_id: int | None = None
    if not applying_direct and not same_lord and translator_id is None:
        for c_id in range(7):
            if c_id == q_id or c_id == s_id:
                continue
            c_lon = planet_lons[c_id]
            c_sp  = planet_speeds[c_id]
            asp_qc = _find_aspect(q_lon, q_sp, c_lon, c_sp)
            asp_sc = _find_aspect(s_lon, s_sp, c_lon, c_sp)
            if asp_qc and asp_qc[2] and asp_sc and asp_sc[2]:
                collector_id = c_id
                break

    # ── Perfection verdict ────────────────────────────────────────────────────
    if same_lord:
        perf = PerfectionResult(
            perfected=True, method="Direct Application",
            translator=None, collector=None,
            description=(
                f"Same lord ({q_sig.planet_name}) rules both H{querent_house} "
                f"and H{quesited_house}: matter is immediately radical"
            ),
        )
    elif applying_direct:
        perf = PerfectionResult(
            perfected=True, method="Direct Application",
            translator=None, collector=None,
            description=(
                f"{q_sig.planet_name} applies to {s_sig.planet_name} "
                f"({direct_aspect.aspect_name}, orb {direct_aspect.orb:.2f}°)"
            ),
        )
    elif translator_id is not None:
        tname = _PLANET_NAMES[translator_id]
        perf = PerfectionResult(
            perfected=True, method="Translation of Light",
            translator=tname, collector=None,
            description=(
                f"{tname} translates light between "
                f"{q_sig.planet_name} and {s_sig.planet_name}"
            ),
        )
    elif collector_id is not None:
        cname = _PLANET_NAMES[collector_id]
        perf = PerfectionResult(
            perfected=True, method="Collection of Light",
            translator=None, collector=cname,
            description=(
                f"{cname} collects light from both "
                f"{q_sig.planet_name} and {s_sig.planet_name}"
            ),
        )
    elif mutual:
        perf = PerfectionResult(
            perfected=True, method="Reception",
            translator=None, collector=None,
            description=(
                f"Mutual reception between {q_sig.planet_name} and "
                f"{s_sig.planet_name} perfects the question"
            ),
        )
    else:
        perf = PerfectionResult(
            perfected=False, method=None,
            translator=None, collector=None,
            description=(
                f"No applying aspect, translation, collection, or mutual reception "
                f"between {q_sig.planet_name} and {s_sig.planet_name}: "
                "matter will not come to pass"
            ),
        )

    # ── Prohibition ───────────────────────────────────────────────────────────
    prohib = ProhibitionResult(
        prohibited=False, prohibitor_name=None, prohibitor_aspect=None,
        description="No prohibition detected",
    )
    if applying_direct and direct_remaining < float("inf"):
        for p_id in range(7):
            if p_id in (q_id, s_id):
                continue
            p_lon = planet_lons[p_id]
            p_sp  = planet_speeds[p_id]
            asp_ps = _find_aspect(p_lon, p_sp, s_lon, s_sp)
            if asp_ps and asp_ps[2]:   # P applying to S
                p_orb = asp_ps[1]
                if p_orb < direct_remaining:
                    pname = _PLANET_NAMES[p_id]
                    pasp  = ASPECT_NAMES[asp_ps[0]]
                    prohib = ProhibitionResult(
                        prohibited=True,
                        prohibitor_name=pname,
                        prohibitor_aspect=pasp,
                        description=(
                            f"{pname} prohibits: applies to {s_sig.planet_name} "
                            f"({pasp}, orb {p_orb:.2f}°) before "
                            f"{q_sig.planet_name} (orb {direct_remaining:.2f}°)"
                        ),
                    )
                    break

    # ── Refranation ───────────────────────────────────────────────────────────
    refran = RefranationResult(
        refranation=False, planet_name=None,
        description="No refranation detected",
    )
    if applying_direct:
        for r_id in (q_id, s_id):
            if planet_speeds[r_id] < 0:
                rname  = _PLANET_NAMES[r_id]
                refran = RefranationResult(
                    refranation=True,
                    planet_name=rname,
                    description=(
                        f"{rname} is retrograde and may refrain from completing "
                        f"the {direct_aspect.aspect_name} before perfection"
                    ),
                )
                break

    # ── Frustration ───────────────────────────────────────────────────────────
    frustrat = FrustrationResult(
        frustrated=False, frustrator_name=None,
        description="No frustration detected",
    )
    if applying_direct and direct_remaining < float("inf"):
        q_days = _days_to_exact(q_lon, q_sp, s_lon, s_sp, applying_angle)
        for f_id in range(7):
            if f_id in (q_id, s_id):
                continue
            f_lon = planet_lons[f_id]
            f_sp  = planet_speeds[f_id]
            # F conjuncts S before Q reaches its aspect
            asp_fs = _find_aspect(f_lon, f_sp, s_lon, s_sp)
            if asp_fs and asp_fs[2] and asp_fs[0] == 0:   # applying conjunction
                f_days = _days_to_exact(f_lon, f_sp, s_lon, s_sp, 0)
                if f_days < q_days:
                    fname = _PLANET_NAMES[f_id]
                    frustrat = FrustrationResult(
                        frustrated=True,
                        frustrator_name=fname,
                        description=(
                            f"{fname} frustrates: will conjoin {s_sig.planet_name} "
                            f"in ~{f_days:.1f} day(s) before "
                            f"{q_sig.planet_name} arrives (~{q_days:.1f} day(s))"
                        ),
                    )
                    break

    # ── Timing estimate (Lilly) ───────────────────────────────────────────────
    # Only meaningful for direct application (not translation/collection/reception)
    timing: TimingEstimate | None = None
    if applying_direct and direct_remaining < float("inf") and not same_lord:
        days_raw = _days_to_exact(q_lon, q_sp, s_lon, s_sp, applying_angle)
        if days_raw < float("inf"):
            sign_idx  = int(q_sig.lon / 30.0) % 12
            modality  = _MODALITY[sign_idx]
            unit, mul = _MODALITY_UNIT[modality]
            value     = round(days_raw / mul, 2)
            timing = TimingEstimate(
                days_raw=round(days_raw, 2),
                unit=unit,
                value=value,
                modality=modality,
                note=(
                    f"{q_sig.planet_name} in {q_sig.sign} ({modality}): "
                    f"~{value:.1f} {unit} until exact {direct_aspect.aspect_name}"
                ),
            )

    return HoraryPerfectionResult(
        querent_house=querent_house,
        quesited_house=quesited_house,
        querent_significator=q_sig,
        quesited_significator=s_sig,
        same_lord=same_lord,
        direct_aspect=direct_aspect,
        perfection=perf,
        prohibition=prohib,
        refranation=refran,
        frustration=frustrat,
        reception=reception,
        timing=timing,
    )
