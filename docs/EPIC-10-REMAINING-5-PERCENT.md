# Epic 10 — Remaining 5% Morinus Parity

**Updated**: 2026-07-05
**Prerequisite**: Epics 1–9 complete (1459 tests passing)
**Goal**: Đóng 5% còn lại để đạt full Morinus 8.1 parity

---

## Tổng quan 6 stories

| Story | Feature | Effort | Priority |
|-------|---------|--------|----------|
| 10.1 | Fixed Stars: 25 → 110+ stars | M | P1 |
| 10.2 | Outer Planets full support | S | P1 |
| 10.3 | Horary Timing (days to perfection) | S | P2 |
| 10.4 | Horary Turned Charts | M | P2 |
| 10.5 | Arabic Parts in Return/Progressed Charts | M | P2 |
| 10.6 | Circumambulations: Full Valens Method | L | P3 |

Effort: S = 1 session, M = 2-3 sessions, L = 4+ sessions

---

## Story 10.1 — Fixed Stars: Mở rộng từ 25 lên 110+ Stars

### Vấn đề hiện tại

`backend/core/fixed_stars.py` có 25 stars: 15 Behenian + 10 Bonatti additions.
Morinus 8.1 dùng danh sách ~110 stars từ Ptolemy's Almagest + Bonatti's complete list.

### Star catalog cần thêm

**Ptolemy's 48 Constellations — các star chính còn thiếu:**

```
Constellation   | Star name       | SE name              | Nature
----------------|-----------------|----------------------|--------
Ursa Minor      | Polaris         | Polaris,alUMi        | S/V
Ursa Minor      | Kochab          | Kochab,beUMi         | S/M
Perseus         | Mirfak          | Mirfak,alPer         | J/S
Orion           | Mintaka         | Mintaka,deOri        | S/Me
Orion           | Alnilam         | Alnilam,epOri        | J/S
Orion           | Alnitak         | Alnitak,zeOri        | J/S
Orion           | Rigel           | (đã có)              | J/M
Orion           | Saiph           | Saiph,kaOri          | S/M
Canis Major     | Wezen           | Wezen,deCMa          | S
Canis Major     | Adhara          | Adhara,epCMa         | V
Hydra           | Alphard         | Alphard,alHya        | S/V
Leo             | Algieba         | Algieba,gaLeo        | J/V
Leo             | Zosma           | Zosma,deLeo          | S/V
Virgo           | Porrima         | Porrima,gaVir        | V/Me
Libra           | Zubenelgenubi   | Zubenelgenubi,alLib  | S/M
Libra           | Zubeneschamali  | Zubeneschamali,beLib | J/Me
Scorpius        | Graffias        | Graffias,beSco       | M/S
Scorpius        | Dschubba        | Dschubba,deSco       | M/S
Scorpius        | Acrab           | Acrab,piSco          | M/S
Scorpius        | Shaula          | Shaula,laSco         | M/Me
Sagittarius     | Kaus Australis  | Kaus Australis,epSgr | J/M
Sagittarius     | Kaus Media      | Kaus Media,deSgr     | J/M
Capricorn       | Dabih           | Dabih,beCap          | S/V
Aquarius        | Sadalsuud       | Sadalsuud,beCap      | S/Me
Aquarius        | Sadalmelik      | Sadalmelik,alAqr     | S/Me
Pisces          | Alrescha        | Alrescha,alPsc       | M/Me
Cetus           | Menkar          | Menkar,alCet         | S/M
Cetus           | Mira            | Mira,oCet            | S
Eridanus        | Cursa           | Cursa,beEri          | J/V
Auriga          | Menkalinan      | Menkalinan,beAur     | M/Me
Taurus          | Ain             | Ain,epTau            | V/Me
Taurus          | Prima Hyadum    | Prima Hyadum,gaTau   | S/M
Taurus          | Secunda Hyadum  | Secunda Hyadum,daTau | S/M
Cancer          | Acubens         | Acubens,alCnc        | S/Me
Cancer          | Asellus Borealis| Asellus Borealis,gaCnc| S/Me
Cancer          | Asellus Australis| Asellus Australis,daCnc| M/S
Hydra           | Minhar al Shuja | Minhar al Shuja,zetHya| S/M
Corvus          | Gienah          | Gienah,gaCorv        | S/M
Corvus          | Alchiba         | Alchiba,alCrv        | M/S
Centaurus       | Bungula (α Cen) | Bungula,alCen        | V/J
Centaurus       | Agena (β Cen)   | Agena,beCen          | V/J
Corona Borealis | Nusakan         | Nusakan,beCrB        | Me/S
Hercules        | Rasalgethi      | Rasalgethi,alHer     | M/V
Ophiuchus       | Rasalhague      | Rasalhague,alOph     | S/V
Ophiuchus       | Sabik           | Sabik,etOph          | S/V
Scorpius        | Lesath          | Lesath,upsSco        | M/Me
Lyra            | Sheliak         | Sheliak,beLyr        | V/Me
Cygnus          | Deneb           | Deneb,alCyg          | V/Me
Cygnus          | Sadr            | Sadr,gaCyg           | V/Me
Cygnus          | Gienah Cygni    | Gienah Cygni,epCyg   | V/Me
Aquila          | Altair          | Altair,alAql         | M/J
Aquila          | Tarazed         | Tarazed,gaAql        | J/M
Piscis Austrinus| Fomalhaut       | (đã có)              | V/Me
Pegasus         | Scheat          | Scheat,bePeg         | M/Me
Pegasus         | Markab          | Markab,alPeg         | M/S
Pegasus         | Enif            | Enif,epPeg           | M/J
Andromeda       | Alpheratz       | Alpheratz,alAnd      | V/J
```

**Bonatti's Extended Catalog (từ Liber Astronomiae) — thêm ~20 stars:**
```
Pleiades cluster   | Pleiades,etaTau   | M/Lu  (cluster, dùng η Tau)
Praesepe (Beehive) | Praesepe,epCnc    | M     (cluster, dùng ε Cnc)
Nashira            | Nashira,gaCap     | S/J
Sadalsuud          | (xem trên)
Markab             | (xem trên)
Difda              | Difda,beCet       | S
Hamal              | Hamal,alAri       | M/S
Sheratan           | Sheratan,beAri    | M/S
Mesartim           | Mesartim,gaAri    | M
Rana               | Rana,dEri         | S/V
```

### Implementation

**File**: `backend/core/fixed_stars.py`

Chỉ cần mở rộng constant `FIXED_STARS: list[tuple[str, str, str]]`.
Logic `calc_fixed_stars()` không thay đổi — Swiss Ephemeris `fixstar_ut()` handle mọi star bằng tên.

```python
# Verify star name works with SE before adding:
import swisseph as swe
lon, _ = swe.fixstar_ut("Altair,alAql", jd, swe.FLG_SWIEPH)
```

**Verification**: Mỗi star mới cần test SE name lookup không raise exception.

### Acceptance Criteria

- [ ] `FIXED_STARS` catalog mở rộng lên 110+ entries
- [ ] Tất cả SE star names verified hoạt động với `swe.fixstar_ut()`
- [ ] `star_positions` trong response trả về tất cả stars
- [ ] Số lượng aspects tăng proportionally (nhiều stars → nhiều hits)
- [ ] Tests: 1 test verify catalog size ≥ 110, 1 test per nhóm star mới

---

## Story 10.2 — Outer Planets Full Support (Uranus/Neptune/Pluto)

### Vấn đề hiện tại

3 test failures hiện tại:
```
FAILED tests/verification/test_tertiary_progressions.py::test_tp_outer_planets
FAILED tests/verification/test_transit_timing.py::test_api_outer_present_when_requested
FAILED tests/verification/test_transits.py::test_tr_outer_planets_in_transit
```

Outer planets (planet IDs 7=Uranus, 8=Neptune, 9=Pluto) được request nhưng không trả về
đúng data trong một số code paths.

### Diagnosis

**Step 1**: Đọc từng test đang fail để hiểu exact assertion nào fail.

**Step 2**: Trace code path cho outer planets trong:
- `backend/core/transits.py` — `calc_transits()`
- `backend/core/transit_timing.py` — `calc_transit_timing()`
- `backend/core/secondary_progressions.py` (tertiary uses same code path)

**Common root causes**:

1. **Planet ID range check** — code có `if pid > 6: continue` hoặc `range(7)` hardcoded
2. **Speed calculation** — `swe.calc_ut()` cho outer planets cần flag `swe.FLG_SPEED`
3. **Retrograde periods** — outer planets có retrograde periods dài hơn, Newton-Raphson có thể không converge

### Implementation

```python
# Pattern để support outer planets — thay range(7) bằng:
CLASSICAL_PLANETS = range(7)   # Sun–Saturn
OUTER_PLANETS = [7, 8, 9]      # Uranus, Neptune, Pluto (SE constants)
ALL_PLANETS = list(range(7)) + OUTER_PLANETS

# SE planet constants:
# swe.URANUS = 7, swe.NEPTUNE = 8, swe.PLUTO = 9

# Outer planets trong swe.calc_ut:
lon, lat, dist, sp, slat, sdist = swe.calc_ut(jd, swe.URANUS, swe.FLG_SWIEPH | swe.FLG_SPEED)
```

**Transit timing cho outer planets**: Tốc độ rất chậm (~0.01–0.04°/day). Newton-Raphson cần
max_iterations cao hơn hoặc tolerance khác. Xem xét dùng bisection thay NR cho outer planets.

### Acceptance Criteria

- [ ] `test_tp_outer_planets` pass
- [ ] `test_api_outer_present_when_requested` pass
- [ ] `test_tr_outer_planets_in_transit` pass
- [ ] Không có regression trong 1459 tests hiện tại
- [ ] Outer planets xuất hiện trong transit response khi `include_outer_planets: true`

---

## Story 10.3 — Horary Timing: Số Ngày Đến Perfection

### Vấn đề hiện tại

`backend/core/horary_perfection.py` xác định được perfection xảy ra bằng cách nào
nhưng không nói **khi nào** — số ngày cụ thể.

### Lý thuyết (William Lilly, Christian Astrology Book 1)

Khi Q applies to S:
```
remaining_orb = current orb giữa Q và S (degrees)
daily_approach = |speed_Q - speed_S| (degrees/day)
days_to_perfection = remaining_orb / daily_approach
```

Unit conversion (Lilly's rules):
```
Nếu significator ở Cardinal sign → 1 unit = days
Nếu significator ở Fixed sign    → 1 unit = weeks (× 7)
Nếu significator ở Mutable sign  → 1 unit = months (× 30)
```

Sign modality:
```python
CARDINAL = {0, 3, 6, 9}   # Aries, Cancer, Libra, Capricorn
FIXED    = {1, 4, 7, 10}  # Taurus, Leo, Scorpio, Aquarius
MUTABLE  = {2, 5, 8, 11}  # Gemini, Virgo, Sagittarius, Pisces
```

### Implementation

**File**: `backend/core/horary_perfection.py` — thêm vào `HoraryPerfectionResult`

```python
@dataclass
class TimingEstimate:
    days_raw: float          # raw calculation (days)
    unit: str                # "days" | "weeks" | "months"
    value: float             # days_raw converted to unit
    sign_modality: str       # "cardinal" | "fixed" | "mutable"
    note: str                # e.g. "Q in cardinal sign → days"
```

**Thêm vào `HoraryPerfectionResult`**:
```python
timing: TimingEstimate | None  # None nếu no direct application
```

**New endpoint**: Không cần endpoint riêng — thêm `timing` field vào
`POST /chart/horary/perfection` response.

**Pydantic model update** (`backend/models/chart.py`):
```python
class HoraryTimingData(BaseModel):
    days_raw: float
    unit: str
    value: float
    sign_modality: str
    note: str

class HoraryPerfectionResponse(BaseModel):
    # existing fields...
    timing: HoraryTimingData | None = None
```

### Acceptance Criteria

- [ ] `timing` field trong perfection response khi có direct application
- [ ] `unit` đúng theo sign modality của querent significator
- [ ] `days_raw` = `remaining_orb / daily_approach`
- [ ] `timing = null` khi perfection qua translation/collection (không có direct approach)
- [ ] Tests: cardinal sign → days, fixed sign → weeks, mutable sign → months
- [ ] 8 tests minimum

---

## Story 10.4 — Horary Turned Charts

### Vấn đề hiện tại

Morinus cho phép "turn" horary chart: re-derive houses từ góc nhìn của một house khác.

**Ví dụ**: Hỏi về "Will my brother find a job?"
- Anh trai = H3 (siblings)
- Job của anh trai = H10 tính từ H3 = H12 natal
- Tiền của anh trai = H2 tính từ H3 = H4 natal

### Lý thuyết

```
Turned house number = ((target_house - 1) + (from_house - 1)) % 12 + 1
```

Ví dụ:
```
H10 tính từ H3:  ((10-1) + (3-1)) % 12 + 1 = (9+2) % 12 + 1 = 11 + 1 = 12
H2 tính từ H3:   ((2-1) + (3-1)) % 12 + 1 = (1+2) % 12 + 1 = 3 + 1 = 4
```

House lord derivation: dùng cusp longitude của turned house → `_SIGN_LORDS[sign]`

### New Endpoint

`POST /chart/horary/turned`

**Request**:
```json
{
  "datetime": "2024-06-15T14:30:00",
  "lat": 51.5074,
  "lon": -0.1278,
  "house_system": "P",
  "from_house": 3,
  "querent_house": 1,
  "quesited_house": 10
}
```

**Response**:
```json
{
  "turned_quesited_house": 12,
  "turned_lord_id": 6,
  "turned_lord_name": "Saturn",
  "original_quesited_house": 10,
  "from_house": 3,
  "explanation": "H10 from H3 = H12 natal (Saturn)",
  "all_turned_houses": {
    "1": {"natal": 3, "lord_id": 2, "lord_name": "Mercury"},
    "2": {"natal": 4, "lord_id": 1, "lord_name": "Moon"},
    ...
    "12": {"natal": 2, "lord_id": 3, "lord_name": "Venus"}
  }
}
```

**`all_turned_houses`**: mapping đầy đủ 12 turned houses → natal house + lord,
giúp client render turned chart overlay.

### New Core Module

**File**: `backend/core/horary_turned.py`

```python
from dataclasses import dataclass

_SIGN_LORDS = {0:4, 1:3, 2:2, 3:1, 4:0, 5:2, 6:3, 7:4, 8:5, 9:6, 10:6, 11:5}
_PLANET_NAMES = {0:"Sun", 1:"Moon", 2:"Mercury", 3:"Venus",
                 4:"Mars", 5:"Jupiter", 6:"Saturn"}

@dataclass
class TurnedHouseInfo:
    turned_house: int    # 1–12 in turned chart
    natal_house:  int    # corresponding natal house
    cusp_lon:     float  # longitude of this cusp
    lord_id:      int
    lord_name:    str

@dataclass
class HoraryTurnedResult:
    from_house:             int
    querent_house:          int
    original_quesited_house: int
    turned_quesited_house:  int
    turned_lord_id:         int
    turned_lord_name:       str
    explanation:            str
    all_turned_houses:      list[TurnedHouseInfo]   # 12 items

def calc_horary_turned(
    cusps: list[float],   # 12 cusps from swe.houses()
    from_house: int,      # perspective house (1–12)
    querent_house: int,   # usually 1
    quesited_house: int,  # the matter house (e.g. 10 for career)
) -> HoraryTurnedResult:
    """
    Turn the chart: derive all 12 houses from 'from_house' perspective.
    Turned H1 = natal 'from_house'.
    Turned Hn = natal house ((from_house + n - 2) % 12 + 1).
    """
    ...
```

### Files cần tạo/sửa

- `backend/core/horary_turned.py` (new)
- `backend/api/routes/horary_turned_route.py` (new)
- `backend/models/chart.py` — thêm `HoraryTurnedRequest`, `HoraryTurnedResponse`
- `backend/main.py` — register router
- `tests/verification/test_horary_turned.py` (new, 15+ tests)

### Acceptance Criteria

- [ ] `calc_horary_turned(cusps, from_house=3, quesited_house=10)` → `turned_quesited_house=12`
- [ ] `all_turned_houses` có đủ 12 entries
- [ ] Lord derivation đúng cho mỗi turned house
- [ ] `explanation` string human-readable
- [ ] `from_house = 1` → turned chart = natal chart (identity case)
- [ ] `POST /chart/horary/turned` endpoint hoạt động
- [ ] Tests: anh trai + job, mẹ + bệnh, bạn bè + tiền, identity case

---

## Story 10.5 — Arabic Parts trong Return & Progressed Charts

### Vấn đề hiện tại

`backend/core/arabic_parts.py` tính 97 lots nhưng chỉ cho natal chart.
Morinus cũng tính lots cho solar return chart và progressed chart.

### Lý thuyết

Cùng formula, khác data input:
```
Lot of Fortune (day chart) = ASC + Moon - Sun

Natal:     dùng natal planet lons + natal ASC
Return:    dùng return planet lons + return ASC
Progressed: dùng progressed planet lons + progressed ASC
```

Sect (day/night) cũng tính theo chart đang tính, không phải natal.

### Implementation

**File**: `backend/core/arabic_parts.py` — API hiện tại:
```python
def calc_arabic_parts(planet_lons: dict, asc: float, day_chart: bool) -> ArabicPartsResult
```

API này đã generic! Chỉ cần truyền đúng data.

**Thay đổi cần làm**: Update các routes để expose lots trong return/progressed responses.

**`backend/api/routes/solar_return_route.py`**: Thêm `lots` vào response:
```python
# Sau khi tính return chart:
from core.arabic_parts import calc_arabic_parts
lots = calc_arabic_parts(return_planet_lons, return_asc, return_day_chart)
```

**`backend/models/chart.py`**: Thêm optional `lots` field vào:
```python
class SolarReturnResponse(BaseModel):
    # existing fields...
    lots: list[ArabicPartData] | None = None  # optional, default None

class ProgressionResponse(BaseModel):
    # existing fields...
    lots: list[ArabicPartData] | None = None
```

**Query param**: `include_lots: bool = False` để không làm nặng response mặc định.

### Files cần sửa

- `backend/api/routes/solar_return_route.py`
- `backend/api/routes/lunar_return_route.py`
- `backend/api/routes/secondary_progressions_route.py`
- `backend/api/routes/solar_arc_route.py`
- `backend/models/chart.py`
- `tests/verification/test_arabic_parts_in_returns.py` (new, 10+ tests)

### Acceptance Criteria

- [ ] Solar return response có `lots` khi `include_lots=true`
- [ ] Lot values dùng return chart ASC + planets (không phải natal)
- [ ] Sect dùng return chart Sun position
- [ ] Lunar return tương tự
- [ ] Secondary progression tương tự
- [ ] Solar arc tương tự
- [ ] `include_lots=false` (default) → `lots: null` (không tính, tiết kiệm CPU)
- [ ] Tests: verify Lot of Fortune khác nhau giữa natal vs return của cùng chart

---

## Story 10.6 — Circumambulations: Full Valens Method

### Vấn đề hiện tại

`backend/core/circumambulations.py` implement aphesis by bounds (Ptolemy key).
Valens' full method còn bao gồm:

1. **Releasing by Triplicity Lords** — khi bound lord của current period thay đổi
   → sub-period lord = triplicity lord của sect light's sign
2. **Loosing of the Bond** — khi releasing arc crosses MC (10th từ releaser) hoặc DSC
3. **Sect light as second releaser** — always compute both ASC-releasing và sect-light-releasing
   (hiện tại ta có, nhưng cần verify sect light selection đúng)
4. **Bonification & Maltreatment** — period lord bị benefic/malefic aspect → strengthen/weaken reading
5. **Timing within period** — sub-periods chia theo minor years của planets

### Lý thuyết — Minor Years (Ptolemy/Paulus)

```python
MINOR_YEARS = {
    0: 19,   # Sun
    1: 25,   # Moon
    2: 20,   # Mercury
    3: 8,    # Venus
    4: 15,   # Mars
    5: 12,   # Jupiter
    6: 30,   # Saturn
}
```

Sub-period trong một releasing arc = sub-arc / total_arc × major_period_years × 365.25 days

### Loosing of the Bond

```
Khi accumulated OA của ASC-releaser cross qua OA của natal MC:
  → "loosing of the bond" — particularly significant period
  → tương đương: phép releasing tới đúng H10 của natal chart
```

Cần track MC's OA và flag khi event arc gần MC_OA.

### Bonification & Maltreatment

Trong period của planet P:
```
Benefic aspect (trine/sextile) từ Jupiter hoặc Venus tới P → bonification (+)
Malefic aspect (square/opposition) từ Mars hoặc Saturn tới P → maltreatment (−)
```
Tính từ natal positions của planets.

### Implementation

**File**: `backend/core/circumambulations.py`

```python
@dataclass
class CircumambulationEvent:
    # existing fields...
    is_loosing_of_bond: bool = False
    bonification: str | None = None    # "Jupiter trine", "Venus sextile", ...
    maltreatment: str | None = None    # "Saturn square", "Mars opposition", ...
    sub_periods: list["SubPeriod"] | None = None

@dataclass
class SubPeriod:
    planet_id:   int
    planet_name: str
    start_date:  str
    end_date:    str
    duration_days: float
```

**Config param**: `include_sub_periods: bool = False` — sub-periods là expensive calculation.

### Acceptance Criteria

- [ ] `is_loosing_of_bond: true` cho event gần natal MC OA (within 3°)
- [ ] `bonification` field khi Jupiter/Venus aspect period lord natally
- [ ] `maltreatment` field khi Mars/Saturn aspect period lord natally
- [ ] `sub_periods` list khi `include_sub_periods=true`
- [ ] Sub-period durations sum ≈ major period duration
- [ ] Sect light releaser selection đúng (Sun cho day chart, Moon cho night)
- [ ] Tests: 15+ tests bao gồm loosing of bond, bonification, maltreatment, sub-periods

---

## Implementation Order

Nên làm theo thứ tự:

```
10.2 (Outer Planets) → fix 3 failing tests ngay, low risk
10.3 (Horary Timing) → nhỏ, isolated, dễ test
10.1 (Fixed Stars)   → catalog expansion, no logic change
10.4 (Turned Charts) → new module, medium complexity
10.5 (Arabic Parts in Returns) → wire existing code, medium
10.6 (Circumambulations)       → most complex, last
```

**10.2 trước tiên** vì nó sửa existing failures thay vì thêm feature mới.

---

## Definition of Done (Epic 10)

- [ ] 0 test failures (hiện tại 3 → 0)
- [ ] 110+ fixed stars trong catalog
- [ ] Horary timing field trong perfection response
- [ ] `/chart/horary/turned` endpoint hoạt động
- [ ] `include_lots=true` trả về lots trong return/progressed responses
- [ ] Circumambulations có loosing of bond + bonification/maltreatment
- [ ] Tổng tests tăng lên ≥ 1520 (thêm ~60+ tests mới)
- [ ] Morinus parity: **~99%** (5% remaining → <1%, phần còn lại là GUI-only)
