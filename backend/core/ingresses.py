"""
Ingresses (Epic 5.3).

Finds the exact moments when planets cross 0° of each zodiac sign
(i.e., cross one of the 12 sign boundaries at 0, 30, 60 … 330°).

Retrograde ingresses are included: a planet crossing a sign boundary
while moving backwards is re-entering the previous sign (e.g., Mercury
crossing back through the Aquarius/Capricorn boundary while retrograde
= entering Capricorn).

Reuses _find_hits_for_target and _STEP from core.transit_timing so the
scan algorithm and step sizes are consistent across Epic 5 endpoints.
"""

from __future__ import annotations
from dataclasses import dataclass
import swisseph as swe

from core.transit_timing import _find_hits_for_target, _STEP, _DEFAULT_STEP

_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

SIGN_NAMES: list[str] = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

# 12 sign-cusp longitudes: 0°Ari, 0°Tau, …, 0°Pis
_BOUNDARIES: list[float] = [i * 30.0 for i in range(12)]


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class IngressEvent:
    planet_id:    int
    planet_name:  str
    sign:         str    # sign being entered
    from_sign:    str    # sign being exited
    boundary_lon: float  # 0, 30, 60 … 330
    ingress_jd:   float
    ingress_date: str    # YYYY-MM-DD
    ingress_time: str    # HH:MM UTC
    retrograde:   bool   # True when re-entering previous sign


# ── Helpers ────────────────────────────────────────────────────────────────────

def _jd_to_datetime(jd: float) -> tuple[str, str]:
    y, m, d, h = swe.revjul(jd, swe.GREG_CAL)
    hour_int = int(h)
    minute_int = int(round((h - hour_int) * 60))
    if minute_int == 60:
        hour_int += 1
        minute_int = 0
    return (
        f"{int(y):04d}-{int(m):02d}-{int(d):02d}",
        f"{hour_int:02d}:{minute_int:02d}",
    )


# ── Main function ──────────────────────────────────────────────────────────────

def calc_ingresses(
    start_jd: float,
    end_jd: float,
    planet_ids: list[tuple[int, str]],
) -> list[IngressEvent]:
    """
    Return all sign ingresses in [start_jd, end_jd], sorted chronologically.

    Parameters
    ----------
    planet_ids
        List of (swisseph planet id, display name) pairs.
    """
    events: list[IngressEvent] = []

    for pid, name in planet_ids:
        step = _STEP.get(pid, _DEFAULT_STEP)

        for boundary in _BOUNDARIES:
            for jd in _find_hits_for_target(start_jd, end_jd, pid, boundary, step):
                r, _ = swe.calc_ut(jd, pid, _FLAGS)
                retro = r[3] < 0

                sign_idx = int(boundary / 30) % 12
                if retro:
                    # Crossing boundary going backwards → entering the sign BELOW
                    entering = SIGN_NAMES[(sign_idx - 1) % 12]
                    leaving  = SIGN_NAMES[sign_idx]
                else:
                    entering = SIGN_NAMES[sign_idx]
                    leaving  = SIGN_NAMES[(sign_idx - 1) % 12]

                date_str, time_str = _jd_to_datetime(jd)
                events.append(IngressEvent(
                    planet_id=pid,
                    planet_name=name,
                    sign=entering,
                    from_sign=leaving,
                    boundary_lon=boundary,
                    ingress_jd=jd,
                    ingress_date=date_str,
                    ingress_time=time_str,
                    retrograde=retro,
                ))

    events.sort(key=lambda e: e.ingress_jd)
    return events
