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
    # Fallback: try loading from current working directory
    load_dotenv()  # This will silently fail if .env doesn't exist

# ===================================
# API KEYS
# ===================================

# NASA GIBS does not require an API key - it's open access!
# No API key needed for GIBS imagery

# Claude API Key (reuse from other features)
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')

# ===================================
# NASA GIBS API SETTINGS
# ===================================

# GIBS WMTS (Web Map Tile Service) endpoint
# Using Geographic projection (EPSG:4326)
GIBS_WMTS_BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/wmts.cgi"

# GIBS WMS (Web Map Service) endpoint for single image requests
GIBS_WMS_BASE = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"

# Available imagery layers (products)
# HLS (Harmonized Landsat Sentinel-2) - Best for land monitoring
GIBS_LAYERS = {
    'landsat': 'HLS_L30_Nadir_BRDF_Adjusted_Reflectance',  # Landsat 8/9
    'sentinel': 'HLS_S30_Nadir_BRDF_Adjusted_Reflectance',  # Sentinel-2
    'viirs_day': 'VIIRS_SNPP_CorrectedReflectance_TrueColor',  # VIIRS Day
    'modis_terra': 'MODIS_Terra_CorrectedReflectance_TrueColor',  # MODIS Terra
    'modis_aqua': 'MODIS_Aqua_CorrectedReflectance_TrueColor',  # MODIS Aqua
}

# Default layer for analysis
# Note: VIIRS has daily coverage which ensures better data availability
# Landsat/Sentinel have higher resolution but 5-16 day repeat cycles
DEFAULT_LAYER = 'viirs_day'  # VIIRS - daily coverage, 375m resolution, reliable availability

# Image size in pixels (GIBS supports various sizes)
# Larger = better detail but bigger file size
DEFAULT_IMAGE_WIDTH = 1024
DEFAULT_IMAGE_HEIGHT = 1024

# Bounding box size in degrees (for WMS requests)
# Smaller = more detail, Larger = wider view
DEFAULT_BBOX_SIZE = 0.1  # ~11km x 11km at equator

# ===================================
# PRE-DEFINED REGIONS FOR TESTING
# ===================================

REGIONS: Dict[str, Dict] = {
    # Amazon Rainforest - Active deforestation
    "amazon_basin": {
        "name": "Amazon Rainforest, Brazil",
        "lat": -3.4653,
        "lon": -62.2159,
        "type": "deforestation",
        "description": "High deforestation area in Brazilian Amazon",
        "recommended_dates": {
            "before": "2023-06-15",  # Mid-year dates more likely to have clear imagery
            "after": "2024-06-15"
        },
        "recommended_layer": "viirs_day"  # VIIRS has daily coverage, better availability
    },
    
    # Amazon - Rondônia (heavy deforestation)
    "amazon_rondonia": {
        "name": "Rondônia, Brazil",
        "lat": -9.4281,
        "lon": -63.0648,
        "type": "deforestation",
        "description": "One of most deforested regions in Amazon",
        "recommended_dates": {
            "before": "2022-01-01",
            "after": "2024-01-01"
        }
    },
    
    # Arctic Ice - Greenland
    "arctic_greenland": {
        "name": "Greenland Ice Sheet",
        "lat": 72.0,
        "lon": -40.0,
        "type": "ice_melt",
        "description": "Arctic ice monitoring",
        "recommended_dates": {
            "before": "2023-07-01",  # Summer
            "after": "2024-07-01"
        }
    },
    
    # Urban Sprawl - Las Vegas
    "las_vegas": {
        "name": "Las Vegas, Nevada, USA",
        "lat": 36.1699,
        "lon": -115.1398,
        "type": "urban_sprawl",
        "description": "Rapid urban expansion in desert",
        "recommended_dates": {
            "before": "2020-01-01",
            "after": "2024-01-01"
        }
    },
    
    # Urban Sprawl - Dubai
    "dubai": {
        "name": "Dubai, UAE",
        "lat": 25.2048,
        "lon": 55.2708,
        "type": "urban_sprawl",
        "description": "Rapid coastal development",
        "recommended_dates": {
            "before": "2018-01-01",
            "after": "2024-01-01"
        }
    },
    
    # Wildfire Impact - California
    "california_forests": {
        "name": "Northern California Forests",
        "lat": 40.0,
        "lon": -121.0,
        "type": "fire_damage",
        "description": "Wildfire monitoring",
        "recommended_dates": {
            "before": "2023-06-01",  # Before fire season
            "after": "2023-09-01"   # After fire season
        }
    },
    
    # Congo Basin - Africa
    "congo_basin": {
        "name": "Congo Rainforest, DRC",
        "lat": -0.5,
        "lon": 25.0,
        "type": "deforestation",
        "description": "Second largest rainforest",
        "recommended_dates": {
            "before": "2022-01-01",
            "after": "2024-01-01"
        }
    },
    
    # Test location - Small area for quick testing
    "test_location": {
        "name": "Test Location (Amazon)",
        "lat": -3.0,
        "lon": -60.0,
        "type": "test",
        "description": "Quick test location",
        "recommended_dates": {
            "before": "2024-01-01",
            "after": "2024-06-01"
        }
    }
}

# ===================================
# ANALYSIS CONSTANTS
# ===================================

# Carbon emission factors (tons CO2 per km²)
# Based on above-ground biomass for tropical forests
CARBON_EMISSION_FACTORS = {
    "tropical_forest": 200,  # tons CO2/km² when cleared
    "temperate_forest": 150,
    "boreal_forest": 100,
    "savanna": 50,
    "default": 150
}

# Severity thresholds (% forest loss)
SEVERITY_THRESHOLDS = {
    "critical": 20,   # >20% loss
    "high": 10,       # 10-20% loss
    "moderate": 5,    # 5-10% loss
    "low": 2,         # 2-5% loss
    "minimal": 0      # <2% loss
}

# ===================================
# FILE PATHS
# ===================================

import os
from pathlib import Path

# Base data directory - inside satellite service folder
DATA_DIR = Path(__file__).parent / "data"

# Subdirectories
DOWNLOADS_DIR = DATA_DIR / "downloads"
CACHE_DIR = DATA_DIR / "cache"
RESULTS_DIR = Path(__file__).parent / "results"  # Results in satellite/results/

# Create directories if they don't exist
for directory in [DOWNLOADS_DIR, CACHE_DIR, RESULTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ===================================
# VALIDATION
# ===================================

def validate_config():
    """Validate configuration on import"""

    if not CLAUDE_API_KEY:
        print("[WARNING] CLAUDE_API_KEY not set in environment")
        print("   Set it with: export CLAUDE_API_KEY='your_key_here'")
    else:
        print(f"[OK] Claude API Key loaded: {CLAUDE_API_KEY[:10]}...")

    # GIBS doesn't require API key - it's open access!
    print("[OK] Using NASA GIBS API (no API key required)")
    print(f"   WMS Endpoint: {GIBS_WMS_BASE}")
    print(f"   Default Layer: {GIBS_LAYERS[DEFAULT_LAYER]}")

    # Check data directories
    if not DOWNLOADS_DIR.exists():
        print(f"[OK] Created downloads directory: {DOWNLOADS_DIR}")

    return True

# Run validation on import
validate_config()

# ===================================
# HELPER FUNCTIONS
# ===================================

def get_region(region_key: str) -> Dict:
    """
    Get region configuration by key.
    
    Args:
        region_key: Key from REGIONS dict (e.g., 'amazon_basin')
    
    Returns:
        Region configuration dict
    
    Raises:
        KeyError: If region not found
    """
    if region_key not in REGIONS:
        available = ', '.join(REGIONS.keys())
        raise KeyError(
            f"Region '{region_key}' not found. "
            f"Available regions: {available}"
        )
    
    return REGIONS[region_key]

def list_available_regions():
    """Print all available pre-defined regions"""
    print("\n📍 Available Regions:\n")
    
    for key, region in REGIONS.items():
        print(f"  {key}:")
        print(f"    Name: {region['name']}")
        print(f"    Type: {region['type']}")
        print(f"    Coordinates: ({region['lat']}, {region['lon']})")
        print(f"    Recommended dates: {region['recommended_dates']}")
        print()


# Example usage
if __name__ == "__main__":
    """
    Test configuration.
    
    Usage:
        python config.py
    """
    
    print("="*60)
    print("SATELLITE MONITOR CONFIGURATION")
    print("="*60)

    print(f"\n🔑 API Configuration:")
    print(f"   NASA GIBS API: No key required (open access)")
    print(f"   Claude API Key: {'Set ✓' if CLAUDE_API_KEY else 'Not set ✗'}")

    print(f"\n📂 Data Directories:")
    print(f"   Downloads: {DOWNLOADS_DIR}")
    print(f"   Cache: {CACHE_DIR}")
    print(f"   Results: {RESULTS_DIR}")

    print(f"\n⚙️  GIBS Settings:")
    print(f"   WMS Endpoint: {GIBS_WMS_BASE}")
    print(f"   Default Layer: {DEFAULT_LAYER}")
    print(f"   Image Size: {DEFAULT_IMAGE_WIDTH}x{DEFAULT_IMAGE_HEIGHT} pixels")
    print(f"   Bbox Size: {DEFAULT_BBOX_SIZE}°")

    list_available_regions()

    print("="*60)
    print("✅ Configuration loaded successfully")
    print("="*60)