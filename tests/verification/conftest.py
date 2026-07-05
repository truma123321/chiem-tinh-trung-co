"""
Test fixtures — 5 charts ở vĩ độ khác nhau để verify planetary positions.

Expected values được tính trực tiếp từ pyswisseph (Swiss Ephemeris / JPL DE431).
Đây là same engine mà Astro.com và Morinus dùng — nên kết quả phải khớp.

Cách verify thủ công với Morinus:
  1. Mở Morinus: python tools/morinus/morinus.py
  2. Nhập birth data từ TEST_CHARTS bên dưới
  3. So sánh planet positions với expected values
  4. Tolerance: ≤ 0.01°
"""

import sys
import os
import pytest
import swisseph as swe

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))


# Ephemeris path (shared với Morinus tool)
EPHE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../tools/morinus/SWEP/Ephem")
)

# Tolerance cho float comparison (degrees)
TOLERANCE = 0.01


@pytest.fixture(scope="session", autouse=True)
def init_swe():
    """Initialize Swiss Ephemeris once for all tests."""
    swe.set_ephe_path(EPHE_PATH)
    yield
    swe.close()


# 5 test charts — vĩ độ và điều kiện khác nhau
TEST_CHARTS = {
    "rome_1990_day": {
        "desc": "Rome, Italy — mid-latitude, day chart",
        "year": 1990, "month": 6, "day": 15,
        "hour": 10, "minute": 30, "ut_offset": 0,
        "lat": 41.9, "lon": 12.5,
        "jd": 2448057.9375,  # pre-calculated JD
    },
    "reykjavik_1985_night": {
        "desc": "Reykjavik, Iceland — high latitude, night chart",
        "year": 1985, "month": 12, "day": 21,
        "hour": 3, "minute": 0, "ut_offset": 0,
        "lat": 64.1, "lon": -21.9,
        "jd": 2446420.625,
    },
    "singapore_2000_day": {
        "desc": "Singapore — equatorial, day chart",
        "year": 2000, "month": 3, "day": 20,
        "hour": 12, "minute": 0, "ut_offset": 0,
        "lat": 1.3, "lon": 103.8,
        "jd": 2451624.0,
    },
    "buenos_aires_1970_night": {
        "desc": "Buenos Aires — southern hemisphere, night chart",
        "year": 1970, "month": 7, "day": 4,
        "hour": 22, "minute": 0, "ut_offset": 0,
        "lat": -34.6, "lon": -58.4,
        "jd": 2440772.416667,
    },
    "cairo_1952_day": {
        "desc": "Cairo, Egypt — low latitude, day chart",
        "year": 1952, "month": 1, "day": 1,
        "hour": 6, "minute": 0, "ut_offset": 0,
        "lat": 30.0, "lon": 31.2,
        "jd": 2434012.75,
    },
}

PLANETS_TO_TEST = [
    (swe.SUN,     "Sun"),
    (swe.MOON,    "Moon"),
    (swe.MERCURY, "Mercury"),
    (swe.VENUS,   "Venus"),
    (swe.MARS,    "Mars"),
    (swe.JUPITER, "Jupiter"),
    (swe.SATURN,  "Saturn"),
    (swe.TRUE_NODE, "True Node"),
    (swe.MEAN_NODE, "Mean Node"),
]
