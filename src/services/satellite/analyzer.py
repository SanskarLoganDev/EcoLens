"""
Satellite Environmental Monitor - Main Analyzer
================================================
Complete pipeline for satellite-based environmental monitoring.

Usage:
    # Analyze pre-defined region
    python src/services/satellite/analyzer.py amazon_basin

    # Analyze custom coordinates with a specific layer
    python src/services/satellite/analyzer.py --lat 28.6 --lon 77.2 --before 2019-11-15 --after 2024-11-15 --name "Delhi" --type urban_sprawl --layer sentinel

    # List available regions
    python src/services/satellite/analyzer.py --list
"""

import sys
import json
import argparse
from typing import Dict, Optional
from datetime import datetime

# Import all components
print("\n📦 Step 1/5: Loading dependencies...")
try:
    from satellite_config import get_region, REGIONS, list_available_regions
    from satellite_fetcher import SatelliteFetcher
    from satellite_vision_analyzer import SatelliteVisionAnalyzer
    from change_detector import ChangeDetector
    from report_generator import ReportGenerator
    print("   ✓ All modules loaded successfully")
except ImportError as e:
    print(f"\n❌ ERROR at Step 1: Could not import required modules")
    print(f"   Error: {e}")
    print(f"   Make sure all files exist in src/services/satellite/ and dependencies are installed:")
    print(f"   pip install anthropic python-dotenv requests pillow")
    import traceback
    traceback.print_exc()
    sys.exit(1)


class SatelliteAnalyzer:
    """
    Main orchestrator for satellite environmental monitoring.

    Usage:
        analyzer = SatelliteAnalyzer()                      # uses viirs_day
        analyzer = SatelliteAnalyzer(layer='sentinel')      # 30m resolution
        analyzer = SatelliteAnalyzer(layer='landsat')       # 30m resolution

        result = analyzer.analyze_region('amazon_basin')
        result = analyzer.analyze_location(lat=..., lon=..., ...)
    """

    def __init__(self, layer: str = 'viirs_day'):
        """
        Initialize all components.

        Args:
            layer: Satellite imagery layer to use.
                   viirs_day   — 375m resolution, daily coverage (default)
                   modis_terra — 250m resolution, daily coverage
                   modis_aqua  — 250m resolution, daily coverage
                   sentinel    — 30m resolution, 5-day repeat cycle
                   landsat     — 30m resolution, 16-day repeat cycle
        """

        print("\n" + "="*70)
        print("🛰️  SATELLITE ENVIRONMENTAL MONITOR")
        print("="*70)
        print(f"   Layer: {layer}")

        print("\n📦 Step 2/5: Initializing components...")

        try:
            print("   ⏳ Initializing satellite fetcher...")
            self.fetcher = SatelliteFetcher(layer=layer)

            print("   ⏳ Initializing vision analyzer...")
            self.vision = SatelliteVisionAnalyzer()

            print("   ⏳ Initializing change detector...")
            self.detector = ChangeDetector()

            print("   ⏳ Initializing report generator...")
            self.reporter = ReportGenerator()

            print("\n✅ All components initialized successfully")
            print("="*70)

        except ValueError as e:
            print(f"\n❌ ERROR at Step 2: Configuration error — {e}")
            print(f"   Check that CLAUDE_API_KEY is set in your .env file")
            import traceback
            traceback.print_exc()
            raise
        except Exception as e:
            print(f"\n❌ ERROR at Step 2: Failed to initialize components — {e}")
            import traceback
            traceback.print_exc()
            raise

    def analyze_region(self, region_key: str) -> Dict:
        """Analyze a pre-defined region from config."""

        try:
            region = get_region(region_key)
        except KeyError as e:
            print(f"\n❌ {e}")
            print("\nAvailable regions:")
            list_available_regions()
            raise

        print(f"\n📍 Analyzing region: {region['name']}")
        print(f"   Type: {region['type']}")
        print(f"   Coordinates: ({region['lat']}, {region['lon']})")

        dates = region['recommended_dates']

        return self.analyze_location(
            lat=region['lat'],
            lon=region['lon'],
            before_date=dates['before'],
            after_date=dates['after'],
            location_name=region['name'],
            analysis_type=region['type']
        )

    def analyze_location(self,
                         lat: float,
                         lon: float,
                         before_date: str,
                         after_date: str,
                         location_name: Optional[str] = None,
                         analysis_type: str = 'general') -> Dict:
        """Complete analysis pipeline for a custom location."""

        print(f"\n🚀 Starting analysis pipeline...")
        print(f"   Location: {location_name or f'{lat}, {lon}'}")
        print(f"   Period: {before_date} to {after_date}")
        print(f"   Type: {analysis_type}")

        start_time = datetime.now()

        # ── Step 3: Fetch satellite images ────────────────────────────────────
        print(f"\n{'='*70}")
        print("STEP 3/5: FETCHING SATELLITE IMAGES")
        print(f"{'='*70}")

        try:
            image_pair = self.fetcher.fetch_image_pair(
                lat=lat, lon=lon,
                before_date=before_date, after_date=after_date,
                location_name=location_name
            )
        except Exception as e:
            print(f"\n❌ ERROR at Step 3: Failed to fetch satellite images — {e}")
            print(f"   Tips: check coordinates, dates (YYYY-MM-DD), and internet connection")
            import traceback
            traceback.print_exc()
            raise

        # ── Step 4: Vision analysis ───────────────────────────────────────────
        print(f"\n{'='*70}")
        print("STEP 4/5: VISION ANALYSIS")
        print(f"{'='*70}")

        try:
            vision_result = self.vision.compare_images(
                before_image=image_pair['before']['image_path'],
                after_image=image_pair['after']['image_path'],
                before_date=before_date,
                after_date=after_date,
                location_name=location_name or f"{lat}, {lon}",
                analysis_type=analysis_type
            )
        except Exception as e:
            print(f"\n❌ ERROR at Step 4: Vision analysis failed — {e}")
            import traceback
            traceback.print_exc()
            raise

        # ── Step 5: Change detection ──────────────────────────────────────────
        print(f"\n{'='*70}")
        print("STEP 5/5: CHANGE DETECTION & QUANTIFICATION")
        print(f"{'='*70}")

        try:
            changes = self.detector.analyze_changes(
                vision_comparison=vision_result,
                lat=lat,
                analysis_type=analysis_type
            )
        except Exception as e:
            print(f"\n❌ ERROR at Step 5: Change detection failed — {e}")
            import traceback
            traceback.print_exc()
            raise

        # ── Compile results ───────────────────────────────────────────────────
        print(f"\n{'='*70}")
        print("COMPILING RESULTS")
        print(f"{'='*70}")

        complete_result = {
            'location': {
                'name': location_name or f"{lat}, {lon}",
                'lat': lat,
                'lon': lon
            },
            'time_period': {
                'before': before_date,
                'after': after_date,
                'days_elapsed': image_pair['time_delta_days']
            },
            'analysis_type': analysis_type,
            'images': {
                'before': {
                    'date': image_pair['before']['date'],
                    'image_path': image_pair['before']['image_path'],
                    'image_url': image_pair['before']['image_url'],
                    'layer': image_pair['before']['layer']
                },
                'after': {
                    'date': image_pair['after']['date'],
                    'image_path': image_pair['after']['image_path'],
                    'image_url': image_pair['after']['image_url'],
                    'layer': image_pair['after']['layer']
                }
            },
            'vision_analysis': vision_result,
            'changes': changes,
            'analysis_date': datetime.now().isoformat(),
            'execution_time_seconds': (datetime.now() - start_time).total_seconds()
        }

        complete_result['api_cost'] = self.vision.client.get_cost_summary()

        # ── Generate reports ──────────────────────────────────────────────────
        print(f"\n{'='*70}")
        print("GENERATING REPORTS")
        print(f"{'='*70}")

        try:
            report_paths = self.reporter.create_report(
                analysis_result=complete_result,
                location_name=location_name or f"lat{lat}_lon{lon}"
            )
            complete_result['reports'] = report_paths
        except Exception as e:
            print(f"\n⚠️  WARNING: Report generation failed — {e}")
            complete_result['reports'] = {'error': str(e)}

        self._print_summary(complete_result)
        return complete_result

    def _print_summary(self, result: Dict):
        """Print analysis summary to terminal."""

        print(f"\n{'='*70}")
        print("📊 ANALYSIS SUMMARY")
        print(f"{'='*70}")

        location = result['location']
        changes  = result['changes']
        cost     = result['api_cost']

        print(f"\n📍 Location: {location['name']}")
        print(f"   Coordinates: {location['lat']}, {location['lon']}")
        print(f"\n📅 Time Period:")
        print(f"   Before: {result['time_period']['before']}")
        print(f"   After:  {result['time_period']['after']}")
        print(f"   Duration: {result['time_period']['days_elapsed']} days")
        print(f"\n🔍 Findings:")
        print(f"   Change Detected: {'Yes ⚠️' if changes['change_detected'] else 'No ✓'}")

        if changes['change_detected']:
            print(f"   Change Type: {changes['change_type']}")
            print(f"   Severity: {changes['severity'].upper()} ({changes['severity_score']}/10)")
            print(f"   Trend: {changes['trend'].title()}")
            print(f"   Confidence: {changes['confidence'].title()}")
            metrics = changes['metrics']
            print(f"\n📊 Key Metrics:")
            print(f"   {metrics.get('primary_metric_name', 'Change')}: {metrics.get('primary_metric_value', 'N/A')}")
            if 'forest_loss_km2' in metrics:
                print(f"   Forest Loss: {metrics['forest_loss_km2']} km²")
                print(f"   Carbon Emissions: {metrics['carbon_emissions_tons']:,} tons CO2")
            if changes.get('detected_features'):
                print(f"\n🔍 New Features Detected:")
                for feature in changes['detected_features'][:5]:
                    print(f"      • {feature}")

        print(f"\n💰 API Usage:")
        print(f"   Total Calls: {cost['total_calls']}  (Vision: {cost['vision_calls']}, Text: {cost['text_calls']})")
        print(f"   Cost: ${cost['total_cost_usd']:.4f}")
        print(f"\n⏱️  Execution Time: {result['execution_time_seconds']:.2f} seconds")
        print(f"\n📁 Reports Saved:")
        for report_type, path in result['reports'].items():
            print(f"   {report_type}: {path}")
        print(f"\n{'='*70}")
        print("✅ ANALYSIS COMPLETE")
        print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Satellite Environmental Monitor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pre-defined region (uses default viirs_day layer)
  python src/services/satellite/analyzer.py dubai

  # Custom coordinates with Sentinel-2 (30m, sharp imagery)
  python src/services/satellite/analyzer.py --lat 28.6139 --lon 77.2090 --before 2019-11-15 --after 2024-11-15 --name "Delhi NCR" --type urban_sprawl --layer sentinel

  # Custom coordinates with Landsat (30m, highest resolution)
  python src/services/satellite/analyzer.py --lat 28.6139 --lon 77.2090 --before 2019-11-15 --after 2024-11-15 --name "Delhi NCR" --type urban_sprawl --layer landsat

  # List all available regions
  python src/services/satellite/analyzer.py --list
        """
    )

    parser.add_argument('region', nargs='?',
                        help='Pre-defined region key (e.g., dubai, las_vegas, delhi_ncr)')
    parser.add_argument('--lat',    type=float, help='Latitude (-90 to 90)')
    parser.add_argument('--lon',    type=float, help='Longitude (-180 to 180)')
    parser.add_argument('--before', help='Before date (YYYY-MM-DD)')
    parser.add_argument('--after',  help='After date (YYYY-MM-DD)')
    parser.add_argument('--name',   help='Location name for reports')
    parser.add_argument('--type',   default='general',
                        choices=['deforestation', 'ice_melt', 'urban_sprawl', 'general'],
                        help='Analysis type (default: general)')
    parser.add_argument('--layer',  default='viirs_day',
                        choices=['viirs_day', 'modis_terra', 'modis_aqua', 'sentinel', 'landsat'],
                        help='Satellite layer (default: viirs_day). Use sentinel or landsat for 30m sharp imagery.')
    parser.add_argument('--list',   action='store_true',
                        help='List all available pre-defined regions')
    parser.add_argument('--output', help='Also save result JSON to this path')

    args = parser.parse_args()

    if args.list:
        print("\n📍 Available Pre-Defined Regions:\n")
        list_available_regions()
        return 0

    try:
        analyzer = SatelliteAnalyzer(layer=args.layer)
    except Exception as e:
        print(f"\n❌ Failed to initialize analyzer: {e}")
        return 1

    try:
        if args.region:
            result = analyzer.analyze_region(args.region)

        elif args.lat and args.lon and args.before and args.after:
            result = analyzer.analyze_location(
                lat=args.lat,
                lon=args.lon,
                before_date=args.before,
                after_date=args.after,
                location_name=args.name,
                analysis_type=args.type
            )

        else:
            print("\n❌ Error: Provide a region name, or all of: --lat --lon --before --after")
            print("Use --help for examples.")
            return 1

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n💾 Results also saved to: {args.output}")

        return 0

    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
