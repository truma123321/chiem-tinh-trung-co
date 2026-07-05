"""
Swiss Ephemeris wrapper — single source of truth for all calculations.
Ephemeris path points to Morinus data files (already downloaded in tools/morinus).
"""

import os
import swisseph as swe

# Point to ephemeris files from Morinus (shared, no duplication needed)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EPHE_PATH = os.path.join(_BASE_DIR, "..", "tools", "morinus", "SWEP", "Ephem")
_EPHE_PATH = os.path.normpath(_EPHE_PATH)


def init_ephemeris():
    """Initialize Swiss Ephemeris. Call once at app startup."""
    if not os.path.exists(_EPHE_PATH):
        raise RuntimeError(f"Ephemeris path not found: {_EPHE_PATH}")

    se1_files = [f for f in os.listdir(_EPHE_PATH) if f.endswith(".se1")]
    if not se1_files:
        raise RuntimeError(f"No .se1 ephemeris files found in: {_EPHE_PATH}")

    swe.set_ephe_path(_EPHE_PATH)
    print(f"[OK] Swiss Ephemeris initialized: {_EPHE_PATH}")


def close_ephemeris():
    """Clean up Swiss Ephemeris on app shutdown."""
    swe.close()
    # Re-set path immediately so that if close() is called mid-session
    # (e.g., FastAPI lifespan triggered by a test context manager),
    # subsequent swe.calc_ut() calls still find the ephemeris files.
    swe.set_ephe_path(_EPHE_PATH)
