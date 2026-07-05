"""
Horary Turned Charts — Epic 10.4.

In horary, "turning the chart" means viewing it from the perspective
of a particular house. If you ask about your sibling's money, the
sibling IS the ASC (H3), and their money is H2 from H3 = H4 natal.

Formula:
    natal_house = ((from_house - 1) + (target_house - 1)) % 12 + 1

Identity case: from_house = 1 → turned chart = natal chart.

References:
    William Lilly, Christian Astrology, Book 2.
    Anthony Louis, Horary Astrology Plain & Simple.

Planet IDs: 0=Sun, 1=Moon, 2=Mercury, 3=Venus, 4=Mars, 5=Jupiter, 6=Saturn
"""

from __future__ import annotations
from dataclasses import dataclass, field

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

_PLANET_NAMES: dict[int, str] = {
    0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
    4: "Mars", 5: "Jupiter", 6: "Saturn",
}

_HOUSE_TOPICS: dict[int, str] = {
    1:  "self / body",
    2:  "money / possessions",
    3:  "siblings / short journeys",
    4:  "home / father",
    5:  "children / pleasure",
    6:  "illness / servants",
    7:  "partner / open enemies",
    8:  "death / shared resources",
    9:  "travel / religion / higher mind",
    10: "career / reputation / mother",
    11: "friends / hopes",
    12: "hidden enemies / confinement",
}


# ─── Result types ─────────────────────────────────────────────────────────────

@dataclass
class TurnedHouseInfo:
    """Mapping of one turned house to its natal counterpart."""
    turned_house: int    # 1–12 in the turned chart
    natal_house:  int    # corresponding natal house
    cusp_lon:     float  # ecliptic longitude of this cusp (= natal cusp_lon)
    lord_id:      int    # planet_id of the traditional lord
    lord_name:    str


@dataclass
class HoraryTurnedResult:
    from_house:               int
    from_house_topic:         str
    querent_house:            int
    original_quesited_house:  int    # quesited house as stated (in turned numbering)
    turned_quesited_house:    int    # natal house number that corresponds to quesited
    turned_lord_id:           int
    turned_lord_name:         str
    explanation:              str
    all_turned_houses:        list[TurnedHouseInfo]   # 12 items, ordered by turned house


# ─── Core calculation ──────────────────────────────────────────────────────────

def calc_horary_turned(
    cusps:          list[float],
    from_house:     int,
    quesited_house: int,
    querent_house:  int = 1,
) -> HoraryTurnedResult:
    """
    Turn the horary chart to view it from 'from_house' perspective.

    cusps          : 12 natal house cusp longitudes (index 0 = H1 cusp)
    from_house     : the house whose perspective we adopt (1–12)
    quesited_house : the matter house IN THE TURNED CHART (1–12)
    querent_house  : usually 1

    Returns the mapping of turned houses to natal houses, plus the
    natal house and lord that correspond to the turned quesited house.
    """
    if not (1 <= from_house <= 12):
        raise ValueError(f"from_house must be 1–12, got {from_house}")
    if not (1 <= quesited_house <= 12):
        raise ValueError(f"quesited_house must be 1–12, got {quesited_house}")

    def _natal_house(turned_h: int) -> int:
        return ((from_house - 1) + (turned_h - 1)) % 12 + 1

    def _lord(house_num: int) -> tuple[int, str]:
        cusp_lon  = cusps[house_num - 1]
        sign_idx  = int(cusp_lon / 30.0) % 12
        pid       = _SIGN_LORDS[sign_idx]
        return pid, _PLANET_NAMES[pid]

    # Build all 12 turned houses
    all_turned: list[TurnedHouseInfo] = []
    for h in range(1, 13):
        natal_h  = _natal_house(h)
        pid, pname = _lord(natal_h)
        all_turned.append(TurnedHouseInfo(
            turned_house=h,
            natal_house=natal_h,
            cusp_lon=round(cusps[natal_h - 1], 4),
            lord_id=pid,
            lord_name=pname,
        ))

    # The turned quesited house maps to this natal house
    turned_natal = _natal_house(quesited_house)
    lord_id, lord_name = _lord(turned_natal)

    from_topic   = _HOUSE_TOPICS.get(from_house,     "")
    quest_topic  = _HOUSE_TOPICS.get(quesited_house, "")

    explanation = (
        f"H{quesited_house} ({quest_topic}) from H{from_house} ({from_topic}) "
        f"= H{turned_natal} natal → ruled by {lord_name}"
    )

    return HoraryTurnedResult(
        from_house=from_house,
        from_house_topic=from_topic,
        querent_house=querent_house,
        original_quesited_house=quesited_house,
        turned_quesited_house=turned_natal,
        turned_lord_id=lord_id,
        turned_lord_name=lord_name,
        explanation=explanation,
        all_turned_houses=all_turned,
    )
