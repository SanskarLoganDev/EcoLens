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
from PIL import Image, ImageStat
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
    import sys
    sys.path.append(os.path.dirname(__file__))
    from satellite_config import *
    from geo_utils import validate_coordinates, format_coordinates


class SatelliteFetcher:
    """
    Fetch satellite images from NASA GIBS API.

    GIBS provides global satellite imagery updated daily.
    No API key required - it's open access!
    """

    def __init__(self, layer: str = DEFAULT_LAYER):
        self.layer = layer
        self.layer_name = GIBS_LAYERS.get(layer, GIBS_LAYERS[DEFAULT_LAYER])

        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        print(f"[OK] Satellite Fetcher initialized (GIBS API)")
        print(f"   Layer: {self.layer} ({self.layer_name})")
        print(f"   No API key required - open access!")

    def _check_image_has_content(self, image_content: bytes) -> bool:
        """
        Check if image contains actual surface data (not blank/cloud/empty).

        Rejects three kinds of bad images:
          1. Near-black  — fully transparent PNG rendered as black after RGBA→RGB
                          conversion, or a genuine no-data tile.
          2. Near-white  — 100% cloud cover. GIBS returns a valid PNG but every
                          pixel is white (~255,255,255). The old threshold of 30
                          on total_range only caught black; white images slipped
                          through because their range is also low (~0-10 across
                          an all-white image) but their mean is ~250, not ~0.
          3. Transparent — RGBA image with alpha=0 (no data mask).

        Strategy:
          - Convert to RGB (transparent → black).
          - Compute per-channel mean brightness and total pixel-value range.
          - Reject if mean brightness > 240 (overwhelmingly white = clouds).
          - Reject if total_range < 30 (uniformly dark = no data / black).
          - Accept otherwise.
        """
        try:
            img = Image.open(io.BytesIO(image_content))

            # Handle transparency: transparent pixels become black after RGB conversion
            if img.mode == 'RGBA':
                # Check if image is mostly transparent (no data from GIBS)
                alpha_channel = img.split()[3]
                alpha_stat = ImageStat.Stat(alpha_channel)
                if alpha_stat.mean[0] < 10:
                    # Almost entirely transparent — no data
                    return False

            img_rgb = img.convert('RGB')
            stat = ImageStat.Stat(img_rgb)

            # Mean brightness per channel (0=black, 255=white)
            mean_r, mean_g, mean_b = stat.mean
            overall_mean = (mean_r + mean_g + mean_b) / 3

            # Total range across all channels (how much variation exists)
            extrema = img_rgb.getextrema()
            total_range = sum(ch_max - ch_min for ch_min, ch_max in extrema)

            # ── Rejection rules ───────────────────────────────────────────
            # Rule 1: Near-white → cloud cover or empty tile
            if overall_mean > 240:
                print(f"   [INFO] Image rejected: near-white (mean={overall_mean:.1f}) — likely full cloud cover")
                return False

            # Rule 2: Near-black with low range → transparent/no-data tile
            if total_range < 30:
                print(f"   [INFO] Image rejected: near-black/uniform (range={total_range}) — no data")
                return False

            # Rule 3: Very bright overall (heavy cloud) even if not pure white
            if overall_mean > 210 and total_range < 80:
                print(f"   [INFO] Image rejected: bright uniform (mean={overall_mean:.1f}, range={total_range}) — likely cloud")
                return False

            print(f"   [INFO] Image accepted: mean={overall_mean:.1f}, range={total_range}")
            return True

        except Exception as e:
            print(f"   [WARNING] Could not verify image content: {e}")
            return True  # Assume valid if check fails

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

        Automatically detects blank/cloud/empty images and retries with
        nearby dates to find valid imagery.
        """

        is_valid, error = validate_coordinates(lat, lon)
        if not is_valid:
            raise ValueError(f"Invalid coordinates: {error}")

        print(f"\n[FETCH] Fetching satellite image from GIBS...")
        print(f"   Location: {format_coordinates(lat, lon)}")
        print(f"   Date: {date}")
        print(f"   Layer: {self.layer}")

        # ── BBOX axis order ───────────────────────────────────────────────────
        # WMS 1.3.0 + EPSG:4326 requires lat/lon axis order (OGC spec):
        #   BBOX = minLat, minLon, maxLat, maxLon
        # This is the OPPOSITE of WMS 1.1.1 (minLon,minLat,maxLon,maxLat).
        # Using lon/lat order here sends the request to wrong coordinates
        # and GIBS returns a valid-but-empty/black PNG every time.
        # ─────────────────────────────────────────────────────────────────────
        half_bbox = bbox_size / 2
        bbox = f"{lat - half_bbox},{lon - half_bbox},{lat + half_bbox},{lon + half_bbox}"

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

        try:
            print(f"   [WAIT] Requesting image from GIBS WMS...")
            print(f"   URL: {GIBS_WMS_BASE}")

            response = requests.get(GIBS_WMS_BASE, params=params, timeout=120)
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '')
            if 'image' not in content_type:
                error_text = response.text[:500]
                print(f"   [ERROR] GIBS returned error instead of image")
                print(f"   Response: {error_text}")
                raise ValueError(f"GIBS API error: No imagery available for {date}")

            image_content = response.content
            print(f"   [OK] Image downloaded ({len(image_content)} bytes)")

        except requests.exceptions.Timeout as e:
            print(f"   [ERROR] GIBS API request timed out")
            raise ValueError(f"GIBS API timeout: {e}")
        except requests.exceptions.RequestException as e:
            print(f"   [ERROR] GIBS API request failed: {e}")
            raise ValueError(f"Failed to fetch satellite image: {e}")

        try:
            img = Image.open(io.BytesIO(image_content))
            print(f"   [OK] Valid image: {img.size[0]}x{img.size[1]} pixels, {img.mode} mode")
        except Exception as e:
            print(f"   [ERROR] Invalid image data received")
            raise ValueError(f"Invalid image from GIBS: {e}")

        has_content = self._check_image_has_content(image_content)

        if not has_content and retry_nearby_dates:
            print(f"   [WARNING] Image unusable — searching nearby dates...")

            original_date = datetime.fromisoformat(date)
            tried_dates = [date]

            for offset in range(1, max_date_offset + 1):
                for delta in [offset, -offset]:
                    new_date = original_date + timedelta(days=delta)
                    new_date_str = new_date.strftime('%Y-%m-%d')

                    if new_date_str in tried_dates:
                        continue

                    tried_dates.append(new_date_str)
                    print(f"   [RETRY] Trying {new_date_str} (offset: {delta:+d} days)...")

                    try:
                        return self.fetch_image(
                            lat=lat,
                            lon=lon,
                            date=new_date_str,
                            width=width,
                            height=height,
                            bbox_size=bbox_size,
                            location_name=location_name,
                            retry_nearby_dates=False
                        )
                    except Exception as retry_error:
                        print(f"   [SKIP] {new_date_str} also failed: {retry_error}")
                        continue

            print(f"   [ERROR] No valid imagery found within {max_date_offset} days of {date}")
            raise ValueError(
                f"No valid satellite imagery available for {date} or nearby dates. "
                f"Try --layer modis_terra for daily coverage."
            )

        elif not has_content:
            print(f"   [WARNING] Image appears unusable but retry is disabled — continuing anyway")

        image_path = self._save_image(image_content, lat, lon, date, location_name)
        print(f"   [OK] Saved to: {image_path}")

        image_base64 = base64.b64encode(image_content).decode('utf-8')

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
        """Fetch before and after satellite images."""

        print(f"\n[PAIR] Fetching image pair from GIBS...")

        print(f"\n--- BEFORE IMAGE ---")
        before = self.fetch_image(
            lat=lat, lon=lon, date=before_date,
            width=width, height=height, bbox_size=bbox_size,
            location_name=location_name
        )

        print(f"\n--- AFTER IMAGE ---")
        after = self.fetch_image(
            lat=lat, lon=lon, date=after_date,
            width=width, height=height, bbox_size=bbox_size,
            location_name=location_name
        )

        try:
            date1 = datetime.fromisoformat(before_date)
            date2 = datetime.fromisoformat(after_date)
            time_delta = abs((date2 - date1).days)
        except:
            time_delta = 0

        print(f"\n[OK] Image pair fetched successfully from GIBS")
        print(f"  Time span: {time_delta} days")

        return {'before': before, 'after': after, 'time_delta_days': time_delta}

    def _save_image(self, image_content: bytes, lat: float, lon: float,
                    date: str, location_name: Optional[str]) -> Path:
        """Save image to disk."""
        if location_name:
            clean_name = "".join(c for c in location_name if c.isalnum() or c in (' ', '-', '_'))
            clean_name = clean_name.replace(' ', '_').lower()
            location_dir = DOWNLOADS_DIR / clean_name
        else:
            location_dir = DOWNLOADS_DIR / f"lat{lat}_lon{lon}"

        location_dir.mkdir(parents=True, exist_ok=True)
        image_path = location_dir / f"{date}_{self.layer}.png"

        with open(image_path, 'wb') as f:
            f.write(image_content)

        return image_path

    def _save_metadata(self, result: Dict, image_path: Path):
        """Save metadata JSON alongside image."""
        metadata_path = image_path.with_suffix('.json')
        metadata = {k: v for k, v in result.items() if k != 'image_base64'}
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)


if __name__ == "__main__":
    import sys

    print("="*70)
    print("SATELLITE FETCHER TEST (GIBS API)")
    print("="*70)

    try:
        fetcher = SatelliteFetcher(layer='viirs_day')
        result = fetcher.fetch_image(
            lat=-3.4653, lon=-62.2159,
            date='2024-08-01',
            location_name='Amazon Basin Test'
        )
        print(f"\n[SUCCESS] Saved to: {result['image_path']}")
    except Exception as e:
        print(f"\n[FAILED] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
