"""
Satellite Monitor Configuration
================================
API keys, region presets, and configuration constants.

Usage:
    from config import NASA_API_KEY, REGIONS
"""

import os
from typing import Dict
from dotenv import load_dotenv, find_dotenv

# Load environment variables
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
    print(f"[OK] Loaded .env from: {dotenv_path}")
else:
    load_dotenv()

# ===================================
# API KEYS
# ===================================

# NASA GIBS does not require an API key - it's open access!
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')

# ===================================
# NASA GIBS API SETTINGS
# ===================================

GIBS_WMTS_BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/wmts.cgi"
GIBS_WMS_BASE  = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"

# Available imagery layers
GIBS_LAYERS = {
    'landsat':    'HLS_L30_Nadir_BRDF_Adjusted_Reflectance',         # Landsat 8/9, 30m, 16-day repeat
    'sentinel':   'HLS_S30_Nadir_BRDF_Adjusted_Reflectance',         # Sentinel-2,  30m, 5-day repeat
    'viirs_day':  'VIIRS_SNPP_CorrectedReflectance_TrueColor',        # VIIRS,       375m, daily ← default
    'modis_terra':'MODIS_Terra_CorrectedReflectance_TrueColor',       # MODIS Terra, 250m, daily
    'modis_aqua': 'MODIS_Aqua_CorrectedReflectance_TrueColor',        # MODIS Aqua,  250m, daily
}

DEFAULT_LAYER = 'viirs_day'

# Image output size in pixels — kept at 1024 for Claude Vision quality
DEFAULT_IMAGE_WIDTH  = 1024
DEFAULT_IMAGE_HEIGHT = 1024

# ── Bounding box size ─────────────────────────────────────────────────────────
# This controls how much ground each image covers, and is the main driver of
# perceived image sharpness.
#
# VIIRS native resolution is 375m/pixel. At 1024px output:
#   ground coverage needed = 1024 × 375m = ~384km → 0.384° minimum
#
# Setting to 0.5° gives ~50km × 50km coverage at equatorial latitudes,
# which fills the 1024px canvas at roughly 1 native VIIRS pixel per output
# pixel — producing sharp, crisp imagery instead of blocky upscaled squares.
#
# Rule of thumb by layer:
#   viirs_day / modis : 0.5°  (375–250m native res)
#   landsat / sentinel: 0.05° (30m native res, but these have infrequent passes)
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_BBOX_SIZE = 0.5   # was 0.1° — increased to match VIIRS 375m native resolution

# ===================================
# PRE-DEFINED REGIONS
# ===================================

REGIONS: Dict[str, Dict] = {

    # Amazon Rainforest - Active deforestation

    "amazon_basin": {
        "name": "Amazon Rainforest, Brazil",
        "lat": -3.4653,
        "lon": -62.2159,
        "type": "deforestation",
        "description": "Active deforestation area in Brazilian Amazon",
        "recommended_dates": {
            "before": "2023-08-15",   # August = dry season, lower cloud cover
            "after":  "2024-08-15"
        },
        "recommended_layer": "viirs_day"
    },

    # Amazon - Rondônia (heavy deforestation)
    "amazon_rondonia": {
        "name": "Rondônia, Brazil",
        "lat": -9.4281,
        "lon": -63.0648,
        "type": "deforestation",
        "description": "One of the most deforested regions in the Amazon",
        "recommended_dates": {
            "before": "2022-08-01",
            "after":  "2024-08-01"
        },
        "recommended_layer": "viirs_day"
    },

    "congo_basin": {
        "name": "Congo Rainforest, DRC",
        "lat": -0.5,
        "lon": 25.0,
        "type": "deforestation",
        "description": "Second largest tropical rainforest",
        "recommended_dates": {
            "before": "2022-07-01",
            "after":  "2024-07-01"
        },
        "recommended_layer": "viirs_day"
    },

    # Urban sprawl: Las Vegas

    "las_vegas": {
        "name": "Las Vegas, Nevada, USA",
        "lat": 36.1699,
        "lon": -115.1398,
        "type": "urban_sprawl",
        "description": "Rapid urban expansion into Nevada desert — near-zero cloud cover year-round",
        "recommended_dates": {
            "before": "2020-01-15",
            "after":  "2024-01-15"
        },
        "recommended_layer": "viirs_day"
    },

    
    # Urban sprawl: Dubai
    "dubai": {
        "name": "Dubai, UAE",
        "lat": 25.2048,
        "lon": 55.2708,
        "type": "urban_sprawl",
        "description": "Rapid coastal development in Arabian desert — near-zero cloud cover",
        "recommended_dates": {
            "before": "2018-02-01",
            "after":  "2024-02-01"
        },
        "recommended_layer": "viirs_day"
    },

    # Urban sprawl: Delhi NCR
    "delhi_ncr": {
        "name": "Delhi NCR, India",
        "lat": 28.6139,
        "lon": 77.2090,
        "type": "urban_sprawl",
        "description": (
            "Delhi National Capital Region — one of the fastest-growing urban "
            "areas on Earth. The surrounding farmland in Haryana and UP has been "
            "rapidly converted to residential and industrial zones since 2015. "
            "Best imaged October–March (post-monsoon dry season, low cloud cover)."
        ),
        "recommended_dates": {
            "before": "2019-11-15",   # Pre-COVID baseline, dry season
            "after":  "2024-11-15"    # Five years of urban expansion
        },
        "recommended_layer": "viirs_day"
    },

    # Arctic Ice - Greenland

    "arctic_greenland": {
        "name": "Greenland Ice Sheet",
        "lat": 72.0,
        "lon": -40.0,
        "type": "ice_melt",
        "description": "Arctic ice monitoring — clear skies in polar summer",
        "recommended_dates": {
            "before": "2023-07-15",
            "after":  "2024-07-15"
        },
        "recommended_layer": "viirs_day"
    },

    # Wildfire Impact - California

    "california_forests": {
        "name": "Northern California Forests",
        "lat": 40.0,
        "lon": -121.0,
        "type": "fire_damage",
        "description": "Wildfire monitoring — compare pre/post fire season",
        "recommended_dates": {
            "before": "2023-06-01",
            "after":  "2023-10-01"
        },
        "recommended_layer": "viirs_day"
    },

    # Test location - Small area for quick testing

    "test_location": {
        "name": "Test Location (Amazon)",
        "lat": -3.0,
        "lon": -60.0,
        "type": "test",
        "description": "Quick test — swap for a low-cloud region in practice",
        "recommended_dates": {
            "before": "2024-08-01",
            "after":  "2024-10-01"
        },
        "recommended_layer": "viirs_day"
    },
}

# ===================================
# ANALYSIS CONSTANTS
# ===================================

CARBON_EMISSION_FACTORS = {
    "tropical_forest": 200,
    "temperate_forest": 150,
    "boreal_forest":    100,
    "savanna":           50,
    "default":          150
}

SEVERITY_THRESHOLDS = {
    "critical": 20,
    "high":     10,
    "moderate":  5,
    "low":       2,
    "minimal":   0
}

# ===================================
# FILE PATHS
# ===================================

from pathlib import Path

DATA_DIR      = Path(__file__).parent / "data"
DOWNLOADS_DIR = DATA_DIR / "downloads"
CACHE_DIR     = DATA_DIR / "cache"
RESULTS_DIR   = Path(__file__).parent / "results"

for directory in [DOWNLOADS_DIR, CACHE_DIR, RESULTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ===================================
# VALIDATION
# ===================================

def validate_config():
    if not CLAUDE_API_KEY:
        print("[WARNING] CLAUDE_API_KEY not set in environment")
    else:
        print(f"[OK] Claude API Key loaded: {CLAUDE_API_KEY[:10]}...")
    print("[OK] Using NASA GIBS API (no API key required)")
    print(f"   WMS Endpoint: {GIBS_WMS_BASE}")
    print(f"   Default Layer: {GIBS_LAYERS[DEFAULT_LAYER]}")
    return True

validate_config()

# ===================================
# HELPER FUNCTIONS
# ===================================

def get_region(region_key: str) -> Dict:
    if region_key not in REGIONS:
        available = ', '.join(REGIONS.keys())
        raise KeyError(
            f"Region '{region_key}' not found. "
            f"Available regions: {available}"
        )
    return REGIONS[region_key]

def list_available_regions():
    print("\n📍 Available Regions:\n")
    for key, region in REGIONS.items():
        print(f"  {key}:")
        print(f"    Name: {region['name']}")
        print(f"    Type: {region['type']}")
        print(f"    Coordinates: ({region['lat']}, {region['lon']})")
        print(f"    Recommended dates: {region['recommended_dates']}")
        print()

if __name__ == "__main__":
    print("="*60)
    print("SATELLITE MONITOR CONFIGURATION")
    print("="*60)
    print(f"\n📂 Data Directories:")
    print(f"   Downloads: {DOWNLOADS_DIR}")
    print(f"   Cache:     {CACHE_DIR}")
    print(f"   Results:   {RESULTS_DIR}")
    print(f"\n⚙️  GIBS Settings:")
    print(f"   Default Layer: {DEFAULT_LAYER}")
    print(f"   Bbox Size:     {DEFAULT_BBOX_SIZE}° (~{DEFAULT_BBOX_SIZE * 111:.0f}km at equator)")
    print(f"   Image Size:    {DEFAULT_IMAGE_WIDTH}×{DEFAULT_IMAGE_HEIGHT}px")
    list_available_regions()
    print("="*60)
    print("✅ Configuration loaded successfully")
    print("="*60)
