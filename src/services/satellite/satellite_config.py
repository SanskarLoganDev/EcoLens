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
    print(f"✅ Loaded .env from: {dotenv_path}")
else:
    # Fallback: try loading from current working directory
    load_dotenv()  # This will silently fail if .env doesn't exist

# ===================================
# API KEYS
# ===================================

# NASA Earth API Key
# Get yours at: https://api.nasa.gov/ (free, instant)
NASA_API_KEY = os.getenv('NASA_API_KEY', 'DEMO_KEY')

# Claude API Key (reuse from other features)
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')

# ===================================
# NASA EARTH API SETTINGS
# ===================================

NASA_EARTH_API_BASE = "https://api.nasa.gov/planetary/earth"
NASA_IMAGERY_ENDPOINT = f"{NASA_EARTH_API_BASE}/imagery"
NASA_ASSETS_ENDPOINT = f"{NASA_EARTH_API_BASE}/assets"

# Image dimensions (in degrees)
# 0.025 = ~2.5 km at equator
# 0.10 = ~10 km at equator
# 0.25 = ~25 km at equator
DEFAULT_IMAGE_DIM = 0.10  # Good balance of detail and file size

# Cloud cover threshold (0-100)
# Images with >50% clouds will trigger a warning
CLOUD_COVER_THRESHOLD = 50

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
            "before": "2023-01-01",
            "after": "2024-01-01"
        }
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
        print("⚠️  Warning: CLAUDE_API_KEY not set in environment")
        print("   Set it with: export CLAUDE_API_KEY='your_key_here'")
    
    if NASA_API_KEY == 'DEMO_KEY':
        print("ℹ️  Using NASA DEMO_KEY (limited to 30 requests/hour)")
        print("   Get a free API key at: https://api.nasa.gov/")
    
    # Check data directories
    if not DOWNLOADS_DIR.exists():
        print(f"✓ Created downloads directory: {DOWNLOADS_DIR}")
    
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
    
    print(f"\n🔑 API Keys:")
    print(f"   NASA API Key: {NASA_API_KEY[:20]}..." if len(NASA_API_KEY) > 20 else f"   NASA API Key: {NASA_API_KEY}")
    print(f"   Claude API Key: {'Set ✓' if CLAUDE_API_KEY else 'Not set ✗'}")
    
    print(f"\n📂 Data Directories:")
    print(f"   Downloads: {DOWNLOADS_DIR}")
    print(f"   Cache: {CACHE_DIR}")
    print(f"   Results: {RESULTS_DIR}")
    
    print(f"\n⚙️  Settings:")
    print(f"   Image dimension: {DEFAULT_IMAGE_DIM}°")
    print(f"   Cloud threshold: {CLOUD_COVER_THRESHOLD}%")
    
    list_available_regions()
    
    print("="*60)
    print("✅ Configuration loaded successfully")
    print("="*60)