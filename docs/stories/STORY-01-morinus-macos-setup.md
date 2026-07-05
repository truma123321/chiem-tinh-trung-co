# STORY-01: Morinus macOS Setup (M1)

**Epic**: EPIC-01 Core Calculation Engine
**Priority**: P0 — Prerequisite cho mọi thứ còn lại
**Status**: Ready for Development
**Created**: 2026-07-01

---

## Mục Tiêu

Chạy Morinus 8.1 Python port trên MacBook M1 để dùng làm **verification oracle** — ground truth để kiểm chứng tất cả calculations của app chính.

---

## Phát Hiện Quan Trọng (Từ Code Analysis)

Sau khi đọc `sweastrology.py` và `ephemcalc.py`:

### sweastrology.py đã là macOS-compatible

File này **không phải** Windows-only. Tác giả đã viết lại hoàn toàn dùng `pyswisseph`:

```python
import swisseph as swe  # pyswisseph — cross-platform
```

Toàn bộ API đã được wrap thành adapter functions:
- `swe_calc_ut_adaptado()` → `swe.calc_ut()`
- `swe_houses_ex_adaptado()` → `swe.houses_ex()`
- `swe_rise_trans()` → `swe.rise_trans()`
- `swe_cotrans()` → `swe.cotrans()`
- `swe_revjul_adaptado()` → `swe.revjul()`

### Tại sao vẫn có sweastrology.pyd?

`.pyd` là Windows DLL. Trên macOS, Python **tự động bỏ qua** `.pyd` và dùng `sweastrology.py` thay thế. Không cần xóa hay patch gì.

### Kết luận

Story 1 chỉ cần:
1. Clone repo
2. Install pyswisseph + wxPython
3. Kiểm tra ephemeris files
4. Chạy

---

## Acceptance Criteria

- [ ] `python morinus.py` khởi động thành công, hiển thị UI
- [ ] Terminal output: `[OK] Motor Suizo conectado con éxito en: .../SWEP/Ephem`
- [ ] Nhập birth data → natal chart render không lỗi
- [ ] Planet positions hiển thị (Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn)
- [ ] House cusps tính được (Alcabitius)
- [ ] Không có Python exception trong terminal

---

## Implementation Steps

### Bước 1 — Cài Homebrew dependencies

```bash
# Kiểm tra Python version
python3 --version  # Cần 3.9+ (3.11 recommended)

# Cài python 3.11 nếu chưa có
brew install python@3.11
```

### Bước 2 — Clone repo và tạo venv

```bash
cd /Users/ducthinh/Workspace/astrology-web-app

# Clone Morinus vào thư mục tools (không phải production code)
git clone https://github.com/Uthopik/morinus-astrology tools/morinus

cd tools/morinus

# Tạo virtual environment
python3.11 -m venv .venv
source .venv/bin/activate
```

### Bước 3 — Cài dependencies

```bash
# Core dependencies
pip install --upgrade pip wheel

# Swiss Ephemeris binding (cross-platform)
pip install pyswisseph

# wxPython cho macOS M1
# Option A: wheel từ PyPI (thử trước)
pip install wxPython

# Option B: nếu Option A fail, build từ source
# pip install -U \
#   -f https://extras.wxpython.org/wxPython4/extras/macosx/ \
#   wxPython
```

> **Note về wxPython trên M1**: wxPython 4.2+ có official ARM support. Nếu `pip install wxPython` fail, xem phần Troubleshooting.

### Bước 4 — Kiểm tra Ephemeris Files

```bash
# Kiểm tra thư mục ephemeris
ls tools/morinus/SWEP/Ephem/

# Cần thấy files .se1, ví dụ:
# sepl_18.se1, semo_18.se1, seas_18.se1 ...
```

**Nếu thư mục rỗng** — download ephemeris files:

```bash
# Swiss Ephemeris files (cần ít nhất basic set)
# Download từ: https://www.astro.com/ftp/swisseph/ephe/

# Files cần thiết cho modern dates (1800-2400):
# sepl_18.se1  — planets
# semo_18.se1  — moon
# seas_18.se1  — asteroids (optional)

# Download script:
mkdir -p tools/morinus/SWEP/Ephem
cd tools/morinus/SWEP/Ephem

# Các file nhỏ nhất đủ dùng:
curl -O https://www.astro.com/ftp/swisseph/ephe/sepl_18.se1
curl -O https://www.astro.com/ftp/swisseph/ephe/semo_18.se1
curl -O https://www.astro.com/ftp/swisseph/ephe/seas_18.se1

cd -
```

> **Note**: Mỗi file `.se1` cover 600 năm. `sepl_18.se1` cover 1800-2400 AD — đủ cho hầu hết birth charts.

### Bước 5 — Chạy Morinus

```bash
cd tools/morinus
source .venv/bin/activate
python morinus.py
```

**Terminal output kỳ vọng:**
```
[OK] Motor Suizo conectado con éxito en: /path/to/SWEP/Ephem
```

---

## Troubleshooting

### wxPython install fail trên M1

```bash
# Option 1: Dùng conda
conda install -c conda-forge wxpython

# Option 2: Build wheel
pip install attrdict
pip install --pre \
  -f https://wxpython.org/Phoenix/snapshot-builds/ \
  wxPython

# Option 3: Rosetta (last resort)
arch -x86_64 pip install wxPython
```

### [ERROR] Ephemeris not found

```
[ERROR] La carpeta .../SWEP/Ephem está vacía o no tiene archivos .se1
```

→ Chạy Bước 4 để download ephemeris files.

### ImportError: No module named 'swisseph'

```bash
pip install pyswisseph
# hoặc
pip install pyswisseph --no-binary pyswisseph  # build từ source
```

### Python version conflicts

Morinus cần Python 3.9+. Verify:
```bash
python --version
which python  # phải point đến .venv/bin/python
```

### AttributeError hoặc function signature mismatch

`sweastrology.py` có một số adapter quirks:

```python
# swe_fixstar_ut trả tuple (data, name, error)
swe_fixstar_ut = lambda star, jd, flag: (swe.fixstar_ut(star, jd, flag)[0], star, "")

# swe_time_equ trả (errcode, value, errmsg)
swe_time_equ = lambda jd: (0, float(swe.time_equ(float(jd))), "")

# swe_sidtime0 trả float
swe_sidtime0 = lambda jd, ecl, nut: float(swe.sidtime0(float(jd), float(ecl), float(nut))[0])
```

Nếu gặp error ở đây, check pyswisseph version:
```bash
python -c "import swisseph; print(swisseph.__version__)"
```

---

## Verification Checklist

Sau khi Morinus chạy được, verify các features cần dùng sau này:

```
Test chart: 15 June 1990, 10:30, Rome (41.9°N, 12.5°E)

[ ] Planet positions tab: Sun ~24° Gemini, Moon ~3° Aquarius
[ ] Houses tab (Alcabitius): ASC calculated
[ ] Almuten figuris: computed without error
[ ] Arabic Parts: Lot of Fortune visible
[ ] Firdaria: current period shown
[ ] Primary Directions: table loads
```

---

## Output Files (Sau Story 1)

Khi Morinus chạy ổn, generate test fixtures cho Story 16:

```bash
# Tạo thư mục fixtures
mkdir -p /Users/ducthinh/Workspace/astrology-web-app/tests/verification/fixtures

# Dùng Morinus UI để export data cho 5 test charts:
# 1. Rome 1990-06-15 10:30 (mid-latitude, day chart)
# 2. Reykjavik 1985-12-21 03:00 (high-latitude, night chart)
# 3. Singapore 2000-03-20 12:00 (equator, day chart)
# 4. Buenos Aires 1970-07-04 22:00 (south hemisphere, night chart)
# 5. Cairo 1952-01-01 06:00 (ancient chart, day chart)
```

---

## Dependencies

- `pyswisseph` >= 2.10
- `wxPython` >= 4.2
- Python 3.11
- Swiss Ephemeris data files (sepl_18.se1, semo_18.se1)
- macOS 12+ (Monterey) trên M1

## Next Story

Khi Story 1 complete → bắt đầu **STORY-02: FastAPI Backend Scaffold**
