"""
Satellite Image Fetcher
========================
Download satellite images from NASA Earth Imagery API (EPIC).

Features:
- Fetch images by coordinates and date
- Download before/after image pairs
- Check image quality (cloud cover)
- Save images to disk
- Metadata extraction

Used by: analyze_satellite.py (main orchestrator)
Depends on: config.py, geo_utils.py
"""

import os
import json
import base64
import requests
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

try:
    from satellite_config import (
        NASA_API_KEY,
        NASA_IMAGERY_ENDPOINT,
        NASA_ASSETS_ENDPOINT,
        DEFAULT_IMAGE_DIM,
        CLOUD_COVER_THRESHOLD,
        DOWNLOADS_DIR,
        CACHE_DIR
    )
    from geo_utils import validate_coordinates, format_coordinates
except ImportError:
    # Fallback for direct execution
    import sys
    sys.path.append(os.path.dirname(__file__))
    from satellite_config import *
    from geo_utils import validate_coordinates, format_coordinates


class SatelliteFetcher:
    """
    Fetch satellite images from NASA Earth Imagery API.
    
    Usage:
        fetcher = SatelliteFetcher()
        
        # Fetch single image
        image_data = fetcher.fetch_image(
            lat=-3.0,
            lon=-60.0,
            date="2024-01-01"
        )
        
        # Fetch before/after pair
        pair = fetcher.fetch_image_pair(
            lat=-3.0,
            lon=-60.0,
            before_date="2024-01-01",
            after_date="2025-01-01"
        )
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize satellite fetcher.
        
        Args:
            api_key: NASA API key (uses config default if not provided)
        """
        self.api_key = api_key or NASA_API_KEY
        
        # Create download directories
        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        print(f"✅ Satellite Fetcher initialized")
        if self.api_key == 'DEMO_KEY':
            print(f"   ⚠️  Using DEMO_KEY (limited to 30 requests/hour)")
        else:
            print(f"   API Key: {self.api_key[:10]}...")
    
    def fetch_image(self,
                   lat: float,
                   lon: float,
                   date: str,
                   dim: float = DEFAULT_IMAGE_DIM,
                   location_name: Optional[str] = None,
                   check_cloud_cover: bool = True) -> Dict:
        """
        Fetch a single satellite image from NASA API.
        
        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)
            date: Date in YYYY-MM-DD format
            dim: Image dimension in degrees (default: 0.10)
            location_name: Optional name for the location
            check_cloud_cover: Warn if image is cloudy
        
        Returns:
            {
                'date': '2024-01-01',
                'location': {'lat': -3.0, 'lon': -60.0, 'name': '...'},
                'image_url': 'https://...',
                'image_path': '/path/to/saved/image.png',
                'image_base64': 'base64_encoded_string',
                'cloud_score': 0.15,
                'metadata': {...}
            }
        
        Raises:
            ValueError: If coordinates invalid or image not available
        """
        
        # Validate coordinates
        is_valid, error = validate_coordinates(lat, lon)
        if not is_valid:
            raise ValueError(f"Invalid coordinates: {error}")
        
        print(f"\n📡 Fetching satellite image...")
        print(f"   Location: {format_coordinates(lat, lon)}")
        print(f"   Date: {date}")
        
        # Build request parameters
        params = {
            'lat': lat,
            'lon': lon,
            'date': date,
            'dim': dim,
            'cloud_score': True,
            'api_key': self.api_key
        }
        
        # Make API request
        try:
            response = requests.get(NASA_IMAGERY_ENDPOINT, params=params, timeout=30)
            response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            print(f"   ❌ NASA API request failed: {e}")
            raise ValueError(f"Failed to fetch satellite image: {e}")
        
        # Parse response
        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"   ❌ Invalid JSON response from NASA API")
            raise ValueError("NASA API returned invalid JSON")
        
        # Check for errors in response
        if 'error' in data or 'msg' in data:
            error_msg = data.get('msg') or data.get('error', 'Unknown error')
            print(f"   ❌ NASA API error: {error_msg}")
            raise ValueError(f"NASA API error: {error_msg}")
        
        # Extract data
        image_url = data.get('url')
        cloud_score = data.get('cloud_score', 0)
        actual_date = data.get('date', date)
        
        if not image_url:
            raise ValueError("NASA API did not return image URL")
        
        # Check cloud cover
        if check_cloud_cover and cloud_score > CLOUD_COVER_THRESHOLD / 100:
            print(f"   ⚠️  High cloud cover: {cloud_score*100:.1f}%")
        else:
            print(f"   ✓ Cloud cover: {cloud_score*100:.1f}%")
        
        # Download image
        print(f"   📥 Downloading image...")
        image_content = self._download_image(image_url)
        
        # Save to disk
        image_path = self._save_image(
            image_content,
            lat, lon, date,
            location_name
        )
        
        print(f"   ✓ Saved to: {image_path}")
        
        # Convert to base64 for Vision API
        image_base64 = base64.b64encode(image_content).decode('utf-8')
        
        # Build result
        result = {
            'date': actual_date,
            'location': {
                'lat': lat,
                'lon': lon,
                'name': location_name or format_coordinates(lat, lon)
            },
            'image_url': image_url,
            'image_path': str(image_path),
            'image_base64': image_base64,
            'cloud_score': cloud_score,
            'metadata': {
                'dimension': dim,
                'api_key_used': self.api_key[:10] + '...' if len(self.api_key) > 10 else self.api_key,
                'fetch_time': datetime.now().isoformat()
            }
        }
        
        # Save metadata
        self._save_metadata(result, image_path)
        
        return result
    
    def fetch_image_pair(self,
                        lat: float,
                        lon: float,
                        before_date: str,
                        after_date: str,
                        dim: float = DEFAULT_IMAGE_DIM,
                        location_name: Optional[str] = None) -> Dict:
        """
        Fetch before and after satellite images.
        
        Args:
            lat: Latitude
            lon: Longitude
            before_date: Before date (YYYY-MM-DD)
            after_date: After date (YYYY-MM-DD)
            dim: Image dimension
            location_name: Location name
        
        Returns:
            {
                'before': {...},  # Result from fetch_image()
                'after': {...},   # Result from fetch_image()
                'time_delta_days': 365
            }
        """
        
        print(f"\n🔄 Fetching image pair...")
        
        # Fetch before image
        print(f"\n--- BEFORE IMAGE ---")
        before = self.fetch_image(
            lat=lat,
            lon=lon,
            date=before_date,
            dim=dim,
            location_name=location_name
        )
        
        # Fetch after image
        print(f"\n--- AFTER IMAGE ---")
        after = self.fetch_image(
            lat=lat,
            lon=lon,
            date=after_date,
            dim=dim,
            location_name=location_name
        )
        
        # Calculate time difference
        try:
            date1 = datetime.fromisoformat(before_date)
            date2 = datetime.fromisoformat(after_date)
            time_delta = abs((date2 - date1).days)
        except:
            time_delta = 0
        
        print(f"\n✓ Image pair fetched successfully")
        print(f"  Time span: {time_delta} days")
        
        return {
            'before': before,
            'after': after,
            'time_delta_days': time_delta
        }
    
    def check_available_dates(self,
                             lat: float,
                             lon: float,
                             begin_date: str,
                             end_date: Optional[str] = None) -> List[Dict]:
        """
        Check which dates have available imagery.
        
        Uses NASA Earth Assets API to get metadata.
        
        Args:
            lat: Latitude
            lon: Longitude
            begin_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to today
        
        Returns:
            List of available dates with metadata
        """
        
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"\n🔍 Checking available dates...")
        print(f"   Location: {format_coordinates(lat, lon)}")
        print(f"   Range: {begin_date} to {end_date}")
        
        params = {
            'lat': lat,
            'lon': lon,
            'begin': begin_date,
            'end': end_date,
            'api_key': self.api_key
        }
        
        try:
            response = requests.get(NASA_ASSETS_ENDPOINT, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('results', [])
            
            print(f"   ✓ Found {len(results)} available dates")
            
            # Sort by cloud score (best first)
            results.sort(key=lambda x: x.get('cloud_score', 1.0))
            
            return results
            
        except Exception as e:
            print(f"   ⚠️  Could not check dates: {e}")
            return []
    
    def _download_image(self, url: str) -> bytes:
        """Download image from URL"""
        
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            return response.content
            
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to download image from {url}: {e}")
    
    def _save_image(self,
                   image_content: bytes,
                   lat: float,
                   lon: float,
                   date: str,
                   location_name: Optional[str]) -> Path:
        """Save image to disk"""
        
        # Create location-specific directory
        if location_name:
            # Clean location name for filesystem
            clean_name = "".join(c for c in location_name if c.isalnum() or c in (' ', '-', '_'))
            clean_name = clean_name.replace(' ', '_').lower()
            location_dir = DOWNLOADS_DIR / clean_name
        else:
            location_dir = DOWNLOADS_DIR / f"lat{lat}_lon{lon}"
        
        location_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename
        filename = f"{date}.png"
        image_path = location_dir / filename
        
        # Save
        with open(image_path, 'wb') as f:
            f.write(image_content)
        
        return image_path
    
    def _save_metadata(self, result: Dict, image_path: Path):
        """Save metadata JSON alongside image"""
        
        metadata_path = image_path.with_suffix('.json')
        
        # Exclude base64 data from metadata (too large)
        metadata = {k: v for k, v in result.items() if k != 'image_base64'}
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)


# Example usage / testing
if __name__ == "__main__":
    """
    Test satellite fetcher.
    
    Usage:
        python satellite_fetcher.py
    """
    
    import sys
    
    print("="*70)
    print("SATELLITE FETCHER TEST")
    print("="*70)
    
    # Check API key
    if NASA_API_KEY == 'DEMO_KEY':
        print("\n⚠️  Using DEMO_KEY (limited to 30 requests/hour)")
        print("Get a free API key at: https://api.nasa.gov/")
        print("\nContinuing with DEMO_KEY for testing...")
    
    try:
        fetcher = SatelliteFetcher()
        
        # Test single image fetch
        print("\n" + "="*70)
        print("TEST 1: Fetch Single Image")
        print("="*70)
        
        result = fetcher.fetch_image(
            lat=-3.4653,
            lon=-62.2159,
            date='2024-01-01',
            location_name='Amazon Basin Test'
        )
        
        print(f"\n✅ Image fetched successfully:")
        print(f"   Location: {result['location']['name']}")
        print(f"   Date: {result['date']}")
        print(f"   Cloud cover: {result['cloud_score']*100:.1f}%")
        print(f"   Saved to: {result['image_path']}")
        print(f"   Base64 length: {len(result['image_base64'])} chars")
        
        # Test available dates check
        print("\n" + "="*70)
        print("TEST 2: Check Available Dates")
        print("="*70)
        
        dates = fetcher.check_available_dates(
            lat=-3.4653,
            lon=-62.2159,
            begin_date='2024-01-01',
            end_date='2024-01-31'
        )
        
        if dates:
            print(f"\nTop 5 clearest dates in January 2024:")
            for i, d in enumerate(dates[:5], 1):
                date_str = d.get('date', 'unknown')
                cloud = d.get('cloud_score', 0) * 100
                print(f"   {i}. {date_str} - Cloud cover: {cloud:.1f}%")
        
        print("\n" + "="*70)
        print("✅ All tests passed!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)