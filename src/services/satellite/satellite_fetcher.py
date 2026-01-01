"""
Satellite Image Fetcher - GIBS API
===================================
Download satellite images from NASA's Global Imagery Browse Services (GIBS).

GIBS provides open-access satellite imagery without requiring API keys.
Uses WMS (Web Map Service) for single image requests.

Features:
- Fetch images by coordinates and date
- Download before/after image pairs
- Multiple satellite products (Landsat, Sentinel, MODIS, VIIRS)
- Save images to disk
- No API key required!

Used by: analyzer.py (main orchestrator)
Depends on: satellite_config.py, geo_utils.py
"""

import os
import json
import base64
import requests
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
from PIL import Image
import io

try:
    from satellite_config import (
        GIBS_WMS_BASE,
        GIBS_LAYERS,
        DEFAULT_LAYER,
        DEFAULT_IMAGE_WIDTH,
        DEFAULT_IMAGE_HEIGHT,
        DEFAULT_BBOX_SIZE,
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
    Fetch satellite images from NASA GIBS API.

    GIBS provides global satellite imagery updated daily.
    No API key required - it's open access!

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

    def __init__(self, layer: str = DEFAULT_LAYER):
        """
        Initialize satellite fetcher.

        Args:
            layer: Satellite product to use (landsat, sentinel, viirs_day, modis_terra, modis_aqua)
        """
        self.layer = layer
        self.layer_name = GIBS_LAYERS.get(layer, GIBS_LAYERS[DEFAULT_LAYER])

        # Create download directories
        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        print(f"[OK] Satellite Fetcher initialized (GIBS API)")
        print(f"   Layer: {self.layer} ({self.layer_name})")
        print(f"   No API key required - open access!")

    def _check_image_has_content(self, image_content: bytes) -> bool:
        """
        Check if image has actual content (not blank/white).
        Returns True if image has visible content, False if blank.
        """
        try:
            img = Image.open(io.BytesIO(image_content))

            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Get image statistics
            extrema = img.getextrema()

            # Check if image is mostly uniform (blank)
            # extrema returns ((min_r, max_r), (min_g, max_g), (min_b, max_b))
            total_range = 0
            for channel_min, channel_max in extrema:
                total_range += (channel_max - channel_min)

            # If total range is very low, image is likely blank
            # Threshold of 30 means very little variation across all channels
            if total_range < 30:
                return False

            return True
        except Exception as e:
            print(f"   [WARNING] Could not verify image content: {e}")
            return True  # Assume it's valid if we can't check

    def fetch_image(self,
                   lat: float,
                   lon: float,
                   date: str,
                   width: int = DEFAULT_IMAGE_WIDTH,
                   height: int = DEFAULT_IMAGE_HEIGHT,
                   bbox_size: float = DEFAULT_BBOX_SIZE,
                   location_name: Optional[str] = None,
                   retry_nearby_dates: bool = True,
                   max_date_offset: int = 7) -> Dict:
        """
        Fetch a single satellite image from GIBS WMS.

        Automatically detects blank images and retries with nearby dates to find
        valid imagery when the requested date has no data available.

        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)
            date: Date in YYYY-MM-DD format (will auto-search nearby dates if blank)
            width: Image width in pixels
            height: Image height in pixels
            bbox_size: Bounding box size in degrees
            location_name: Optional name for the location
            retry_nearby_dates: If True, searches nearby dates when image is blank (default: True)
            max_date_offset: Maximum days to search forward/backward (default: 7)

        Returns:
            {
                'date': '2024-01-01',  # May differ from requested if nearby date was used
                'location': {'lat': -3.0, 'lon': -60.0, 'name': '...'},
                'image_url': 'https://...',
                'image_path': '/path/to/saved/image.png',
                'image_base64': 'base64_encoded_string',
                'layer': 'landsat',
                'metadata': {...}
            }

        Raises:
            ValueError: If coordinates invalid or no valid imagery found within date range
        """

        # Validate coordinates
        is_valid, error = validate_coordinates(lat, lon)
        if not is_valid:
            raise ValueError(f"Invalid coordinates: {error}")

        print(f"\n[FETCH] Fetching satellite image from GIBS...")
        print(f"   Location: {format_coordinates(lat, lon)}")
        print(f"   Date: {date}")
        print(f"   Layer: {self.layer}")

        # Calculate bounding box
        # GIBS WMS expects: minlon,minlat,maxlon,maxlat
        half_bbox = bbox_size / 2
        bbox = f"{lon - half_bbox},{lat - half_bbox},{lon + half_bbox},{lat + half_bbox}"

        # Build WMS request parameters
        params = {
            'SERVICE': 'WMS',
            'VERSION': '1.3.0',
            'REQUEST': 'GetMap',
            'LAYERS': self.layer_name,
            'CRS': 'EPSG:4326',
            'BBOX': bbox,
            'WIDTH': width,
            'HEIGHT': height,
            'FORMAT': 'image/png',
            'TIME': date,
        }

        # Make API request
        try:
            print(f"   [WAIT] Requesting image from GIBS WMS...")
            print(f"   URL: {GIBS_WMS_BASE}")

            response = requests.get(GIBS_WMS_BASE, params=params, timeout=120)
            response.raise_for_status()

            # Check if response is an image
            content_type = response.headers.get('Content-Type', '')
            if 'image' not in content_type:
                # GIBS returns XML error messages
                error_text = response.text[:500]
                print(f"   [ERROR] GIBS returned error instead of image")
                print(f"   Response: {error_text}")
                raise ValueError(f"GIBS API error: No imagery available for {date}")

            image_content = response.content
            print(f"   [OK] Image downloaded ({len(image_content)} bytes)")

        except requests.exceptions.Timeout as e:
            print(f"   [ERROR] GIBS API request timed out")
            print(f"   [TIP] Try again or check internet connection")
            raise ValueError(f"GIBS API timeout: {e}")
        except requests.exceptions.RequestException as e:
            print(f"   [ERROR] GIBS API request failed: {e}")
            raise ValueError(f"Failed to fetch satellite image: {e}")

        # Verify it's a valid image
        try:
            img = Image.open(io.BytesIO(image_content))
            print(f"   [OK] Valid image: {img.size[0]}x{img.size[1]} pixels, {img.mode} mode")
        except Exception as e:
            print(f"   [ERROR] Invalid image data received")
            raise ValueError(f"Invalid image from GIBS: {e}")

        # Check if image has actual content (not blank)
        has_content = self._check_image_has_content(image_content)

        if not has_content and retry_nearby_dates:
            print(f"   [WARNING] Image appears blank - searching for nearby dates with data...")

            # Try nearby dates
            from datetime import datetime as dt, timedelta

            original_date = dt.fromisoformat(date)
            tried_dates = [date]

            for offset in range(1, max_date_offset + 1):
                # Try both forward and backward
                for delta in [offset, -offset]:
                    new_date = original_date + timedelta(days=delta)
                    new_date_str = new_date.strftime('%Y-%m-%d')

                    if new_date_str in tried_dates:
                        continue

                    tried_dates.append(new_date_str)

                    print(f"   [RETRY] Trying {new_date_str} (offset: {delta:+d} days)...")

                    # Recursive call without retry to avoid infinite loop
                    try:
                        return self.fetch_image(
                            lat=lat,
                            lon=lon,
                            date=new_date_str,
                            width=width,
                            height=height,
                            bbox_size=bbox_size,
                            location_name=location_name,
                            retry_nearby_dates=False  # Don't retry again
                        )
                    except Exception as retry_error:
                        print(f"   [SKIP] {new_date_str} also failed: {retry_error}")
                        continue

            # If we get here, all retries failed
            print(f"   [ERROR] No valid imagery found within {max_date_offset} days of {date}")
            raise ValueError(
                f"No valid satellite imagery available for {date} or nearby dates. "
                f"Try using --layer modis_terra or --layer viirs_day for daily coverage."
            )

        elif not has_content:
            print(f"   [WARNING] Image appears blank but retry is disabled")
            # Continue anyway - will be caught by vision analysis

        # Save to disk
        image_path = self._save_image(
            image_content,
            lat, lon, date,
            location_name
        )

        print(f"   [OK] Saved to: {image_path}")

        # Convert to base64 for Vision API
        image_base64 = base64.b64encode(image_content).decode('utf-8')

        # Build result
        result = {
            'date': date,
            'location': {
                'lat': lat,
                'lon': lon,
                'name': location_name or format_coordinates(lat, lon)
            },
            'image_url': f"{GIBS_WMS_BASE}?{requests.compat.urlencode(params)}",
            'image_path': str(image_path),
            'image_base64': image_base64,
            'layer': self.layer,
            'layer_name': self.layer_name,
            'metadata': {
                'width': width,
                'height': height,
                'bbox': bbox,
                'bbox_size_degrees': bbox_size,
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
                        width: int = DEFAULT_IMAGE_WIDTH,
                        height: int = DEFAULT_IMAGE_HEIGHT,
                        bbox_size: float = DEFAULT_BBOX_SIZE,
                        location_name: Optional[str] = None) -> Dict:
        """
        Fetch before and after satellite images.

        Args:
            lat: Latitude
            lon: Longitude
            before_date: Before date (YYYY-MM-DD)
            after_date: After date (YYYY-MM-DD)
            width: Image width
            height: Image height
            bbox_size: Bounding box size
            location_name: Location name

        Returns:
            {
                'before': {...},  # Result from fetch_image()
                'after': {...},   # Result from fetch_image()
                'time_delta_days': 365
            }
        """

        print(f"\n[PAIR] Fetching image pair from GIBS...")

        # Fetch before image
        print(f"\n--- BEFORE IMAGE ---")
        before = self.fetch_image(
            lat=lat,
            lon=lon,
            date=before_date,
            width=width,
            height=height,
            bbox_size=bbox_size,
            location_name=location_name
        )

        # Fetch after image
        print(f"\n--- AFTER IMAGE ---")
        after = self.fetch_image(
            lat=lat,
            lon=lon,
            date=after_date,
            width=width,
            height=height,
            bbox_size=bbox_size,
            location_name=location_name
        )

        # Calculate time difference
        try:
            date1 = datetime.fromisoformat(before_date)
            date2 = datetime.fromisoformat(after_date)
            time_delta = abs((date2 - date1).days)
        except:
            time_delta = 0

        print(f"\n[OK] Image pair fetched successfully from GIBS")
        print(f"  Time span: {time_delta} days")

        return {
            'before': before,
            'after': after,
            'time_delta_days': time_delta
        }

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
        filename = f"{date}_{self.layer}.png"
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
    Test satellite fetcher with GIBS API.

    Usage:
        python satellite_fetcher.py
    """

    import sys

    print("="*70)
    print("SATELLITE FETCHER TEST (GIBS API)")
    print("="*70)

    try:
        # Initialize fetcher
        fetcher = SatelliteFetcher(layer='landsat')

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

        print(f"\n[SUCCESS] Image fetched successfully:")
        print(f"   Location: {result['location']['name']}")
        print(f"   Date: {result['date']}")
        print(f"   Layer: {result['layer']}")
        print(f"   Saved to: {result['image_path']}")
        print(f"   Base64 length: {len(result['image_base64'])} chars")

        print("\n" + "="*70)
        print("[SUCCESS] All tests passed!")
        print("="*70)

    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
