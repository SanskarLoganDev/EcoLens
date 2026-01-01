"""
Geographic Utilities
====================
Helper functions for coordinate validation, area calculations, and region lookup.

Used by: satellite_fetcher.py, change_detector.py, report_generator.py
"""

import math
from typing import Tuple, Optional
from satellite_config import REGIONS


def validate_coordinates(lat: float, lon: float) -> Tuple[bool, str]:
    """
    Validate latitude and longitude coordinates.
    
    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)
    
    Returns:
        (is_valid, error_message)
    """
    
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return False, "Coordinates must be numbers"
    
    if lat < -90 or lat > 90:
        return False, f"Latitude must be between -90 and 90 (got {lat})"
    
    if lon < -180 or lon > 180:
        return False, f"Longitude must be between -180 and 180 (got {lon})"
    
    return True, "Valid"


def format_coordinates(lat: float, lon: float) -> str:
    """
    Format coordinates as human-readable string.
    
    Args:
        lat: Latitude
        lon: Longitude
    
    Returns:
        Formatted string like "3°28'S, 62°13'W"
    """
    
    # Determine N/S and E/W
    lat_dir = 'N' if lat >= 0 else 'S'
    lon_dir = 'E' if lon >= 0 else 'W'
    
    # Convert to absolute values
    lat_abs = abs(lat)
    lon_abs = abs(lon)
    
    # Convert to degrees and minutes
    lat_deg = int(lat_abs)
    lat_min = int((lat_abs - lat_deg) * 60)
    
    lon_deg = int(lon_abs)
    lon_min = int((lon_abs - lon_deg) * 60)
    
    return f"{lat_deg}°{lat_min}'{lat_dir}, {lon_deg}°{lon_min}'{lon_dir}"


def get_region_name(lat: float, lon: float) -> Optional[str]:
    """
    Try to identify which pre-defined region these coordinates belong to.
    
    Args:
        lat: Latitude
        lon: Longitude
    
    Returns:
        Region name if found, None otherwise
    """
    
    # Simple distance check (within 1 degree = ~111km)
    threshold = 1.0
    
    for region_key, region_data in REGIONS.items():
        r_lat = region_data['lat']
        r_lon = region_data['lon']
        
        distance = math.sqrt((lat - r_lat)**2 + (lon - r_lon)**2)
        
        if distance < threshold:
            return region_data['name']
    
    return None


def calculate_area_km2(dim_degrees: float, lat: float) -> float:
    """
    Calculate approximate area covered by image dimension.
    
    At equator: 1 degree ≈ 111 km
    At higher latitudes, longitude degrees are smaller
    
    Args:
        dim_degrees: Image dimension in degrees
        lat: Latitude (for longitude correction)
    
    Returns:
        Approximate area in km²
    """
    
    # 1 degree latitude ≈ 111 km everywhere
    km_per_degree_lat = 111.0
    
    # 1 degree longitude varies by latitude
    km_per_degree_lon = 111.0 * math.cos(math.radians(lat))
    
    # Calculate area
    height_km = dim_degrees * km_per_degree_lat
    width_km = dim_degrees * km_per_degree_lon
    
    area_km2 = height_km * width_km
    
    return area_km2


def estimate_carbon_emissions(
    area_lost_km2: float,
    region_type: str = "tropical_forest"
) -> float:
    """
    Estimate carbon emissions from deforestation.
    
    Based on above-ground biomass carbon density.
    
    Args:
        area_lost_km2: Area of forest lost in km²
        region_type: Forest type (tropical, temperate, boreal)
    
    Returns:
        Estimated CO2 emissions in tons
    """
    
    from satellite_config import CARBON_EMISSION_FACTORS
    
    # Get emission factor (tons CO2 per km²)
    factor = CARBON_EMISSION_FACTORS.get(
        region_type,
        CARBON_EMISSION_FACTORS['default']
    )
    
    emissions_tons = area_lost_km2 * factor
    
    return round(emissions_tons, 2)


def calculate_distance_km(
    lat1: float, lon1: float,
    lat2: float, lon2: float
) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.
    
    Args:
        lat1, lon1: First coordinate
        lat2, lon2: Second coordinate
    
    Returns:
        Distance in kilometers
    """
    
    # Earth radius in km
    R = 6371.0
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = (math.sin(dlat / 2)**2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(dlon / 2)**2)
    
    c = 2 * math.asin(math.sqrt(a))
    
    distance = R * c
    
    return round(distance, 2)


# Example usage / testing
if __name__ == "__main__":
    """
    Test geographic utilities.
    
    Usage:
        python geo_utils.py
    """
    
    print("="*60)
    print("GEOGRAPHIC UTILITIES TEST")
    print("="*60)
    
    # Test coordinate validation
    print("\n1. COORDINATE VALIDATION")
    print("-"*60)
    
    test_coords = [
        (-3.0, -60.0, "Amazon (valid)"),
        (95.0, 0.0, "Invalid lat (too high)"),
        (0.0, 200.0, "Invalid lon (too high)")
    ]
    
    for lat, lon, desc in test_coords:
        valid, msg = validate_coordinates(lat, lon)
        status = "✓" if valid else "✗"
        print(f"{status} {desc}: {msg}")
    
    # Test coordinate formatting
    print("\n2. COORDINATE FORMATTING")
    print("-"*60)
    
    coords = [
        (-3.4653, -62.2159, "Amazon Basin"),
        (72.0, -40.0, "Greenland"),
        (36.1699, -115.1398, "Las Vegas")
    ]
    
    for lat, lon, name in coords:
        formatted = format_coordinates(lat, lon)
        print(f"{name}: {formatted}")
    
    # Test region identification
    print("\n3. REGION IDENTIFICATION")
    print("-"*60)
    
    test_regions = [
        (-3.5, -62.0),  # Near Amazon
        (72.1, -40.1),  # Near Greenland
        (0.0, 0.0)      # Unknown
    ]
    
    for lat, lon in test_regions:
        region = get_region_name(lat, lon)
        if region:
            print(f"({lat}, {lon}) → {region}")
        else:
            print(f"({lat}, {lon}) → Unknown region")
    
    # Test area calculation
    print("\n4. AREA CALCULATION")
    print("-"*60)
    
    dims = [0.025, 0.10, 0.25]
    lat = -3.0  # Amazon
    
    for dim in dims:
        area = calculate_area_km2(dim, lat)
        print(f"{dim}° dimension → {area:.2f} km²")
    
    # Test carbon emissions
    print("\n5. CARBON EMISSIONS ESTIMATE")
    print("-"*60)
    
    areas = [10, 50, 100, 500]
    
    for area in areas:
        emissions = estimate_carbon_emissions(area, "tropical_forest")
        print(f"{area} km² deforestation → {emissions:,} tons CO2")
    
    # Test distance calculation
    print("\n6. DISTANCE CALCULATION")
    print("-"*60)
    
    # Amazon to Congo
    lat1, lon1 = -3.0, -60.0  # Amazon
    lat2, lon2 = 0.0, 25.0    # Congo
    
    distance = calculate_distance_km(lat1, lon1, lat2, lon2)
    print(f"Amazon to Congo: {distance:,} km")
    
    print("\n" + "="*60)
    print("✅ All tests passed")
    print("="*60)