"""
Satellite Environmental Monitor - Main Analyzer
================================================
Complete pipeline for satellite-based environmental monitoring.

This is the main entry point that orchestrates the entire workflow:
1. Fetch satellite images from NASA
2. Analyze images with Claude Vision API
3. Detect and quantify changes
4. Generate comprehensive reports

Usage:
    # Analyze pre-defined region
    python analyze_satellite.py amazon_basin
    
    # Analyze custom coordinates
    python analyze_satellite.py --lat -3.0 --lon -60.0 --before 2024-01-01 --after 2025-01-01
    
    # Analyze with custom location name
    python analyze_satellite.py --lat -3.0 --lon -60.0 --before 2024-01-01 --after 2025-01-01 --name "My Forest"
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
    print(f"   Location: analyzer.py:31-35")
    print(f"   Error: {e}")
    print(f"\n   💡 Troubleshooting:")
    print(f"      1. Ensure all files exist in src/services/satellite/:")
    print(f"         - satellite_config.py")
    print(f"         - satellite_fetcher.py")
    print(f"         - satellite_vision_analyzer.py")
    print(f"         - change_detector.py")
    print(f"         - report_generator.py")
    print(f"      2. Check for syntax errors in the files")
    print(f"      3. Verify all dependencies are installed:")
    print(f"         pip install anthropic python-dotenv requests")
    print(f"\n   Full traceback:")
    import traceback
    traceback.print_exc()
    sys.exit(1)


class SatelliteAnalyzer:
    """
    Main orchestrator for satellite environmental monitoring.
    
    Coordinates the entire analysis pipeline:
    - Fetching images from NASA
    - Vision analysis with Claude
    - Change detection and quantification
    - Report generation
    
    Usage:
        analyzer = SatelliteAnalyzer()
        
        # Analyze pre-defined region
        result = analyzer.analyze_region('amazon_basin')
        
        # Analyze custom location
        result = analyzer.analyze_location(
            lat=-3.0,
            lon=-60.0,
            before_date='2024-01-01',
            after_date='2025-01-01',
            location_name='My Location'
        )
    """
    
    def __init__(self):
        """Initialize all components"""

        print("\n" + "="*70)
        print("🛰️  SATELLITE ENVIRONMENTAL MONITOR")
        print("="*70)

        print("\n📦 Step 2/5: Initializing components...")

        try:
            print("   ⏳ Initializing satellite fetcher...")
            self.fetcher = SatelliteFetcher()

            print("   ⏳ Initializing vision analyzer...")
            self.vision = SatelliteVisionAnalyzer()

            print("   ⏳ Initializing change detector...")
            self.detector = ChangeDetector()

            print("   ⏳ Initializing report generator...")
            self.reporter = ReportGenerator()

            print("\n✅ All components initialized successfully")
            print("="*70)

        except ValueError as e:
            print(f"\n❌ ERROR at Step 2: Configuration error")
            print(f"   Location: analyzer.py:__init__")
            print(f"   Error: {e}")
            print(f"\n   💡 Troubleshooting:")
            print(f"      1. Check .env file exists in project root")
            print(f"      2. Verify CLAUDE_API_KEY is set correctly")
            print(f"      3. Optionally set NASA_API_KEY (or use DEMO_KEY)")
            print(f"\n   Full traceback:")
            import traceback
            traceback.print_exc()
            raise
        except Exception as e:
            print(f"\n❌ ERROR at Step 2: Failed to initialize components")
            print(f"   Location: analyzer.py:__init__")
            print(f"   Error: {e}")
            print(f"\n   💡 Troubleshooting:")
            print(f"      1. Ensure all required files are present")
            print(f"      2. Check file permissions for data/results directories")
            print(f"      3. Verify Python version is 3.8+")
            print(f"\n   Full traceback:")
            import traceback
            traceback.print_exc()
            raise
    
    def analyze_region(self, region_key: str) -> Dict:
        """
        Analyze a pre-defined region from config.
        
        Args:
            region_key: Key from REGIONS dict (e.g., 'amazon_basin')
        
        Returns:
            Complete analysis result
        """
        
        # Get region config
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
        
        # Get recommended dates
        dates = region['recommended_dates']
        
        # Run analysis
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
        """
        Complete analysis pipeline for custom location.
        
        Args:
            lat: Latitude
            lon: Longitude
            before_date: Before date (YYYY-MM-DD)
            after_date: After date (YYYY-MM-DD)
            location_name: Optional location name
            analysis_type: Analysis type (deforestation, ice_melt, urban_sprawl, general)
        
        Returns:
            {
                'location': {...},
                'time_period': {...},
                'images': {...},
                'vision_analysis': {...},
                'changes': {...},
                'reports': {...},
                'api_cost': {...}
            }
        """
        
        print(f"\n🚀 Starting analysis pipeline...")
        print(f"   Location: {location_name or f'{lat}, {lon}'}")
        print(f"   Period: {before_date} to {after_date}")
        print(f"   Type: {analysis_type}")

        start_time = datetime.now()

        # Step 1: Fetch satellite images
        print(f"\n{'='*70}")
        print("STEP 3/5: FETCHING SATELLITE IMAGES")
        print(f"{'='*70}")

        try:
            image_pair = self.fetcher.fetch_image_pair(
                lat=lat,
                lon=lon,
                before_date=before_date,
                after_date=after_date,
                location_name=location_name
            )
        except ValueError as e:
            print(f"\n❌ ERROR at Step 3: Failed to fetch satellite images")
            print(f"   Location: analyzer.py:analyze_location() -> fetcher.fetch_image_pair()")
            print(f"   Error: {e}")
            print(f"\n   💡 Troubleshooting:")
            print(f"      1. Check coordinates are valid (lat: -90 to 90, lon: -180 to 180)")
            print(f"      2. Verify dates are in YYYY-MM-DD format")
            print(f"      3. NASA API might be down or rate-limited (DEMO_KEY: 30 req/hour)")
            print(f"      4. Get free NASA API key at: https://api.nasa.gov/")
            print(f"      5. Check internet connection")
            print(f"\n   Full traceback:")
            import traceback
            traceback.print_exc()
            raise
        except Exception as e:
            print(f"\n❌ ERROR at Step 3: Unexpected error fetching images")
            print(f"   Location: analyzer.py:analyze_location() -> fetcher.fetch_image_pair()")
            print(f"   Error: {e}")
            print(f"\n   Full traceback:")
            import traceback
            traceback.print_exc()
            raise
        
        # Step 2: Vision analysis
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
            print(f"\n❌ ERROR at Step 4: Vision analysis failed")
            print(f"   Location: analyzer.py:analyze_location() -> vision.compare_images()")
            print(f"   Error: {e}")
            print(f"\n   💡 Troubleshooting:")
            print(f"      1. Check CLAUDE_API_KEY is valid")
            print(f"      2. Verify images were downloaded successfully")
            print(f"      3. Check Claude API status")
            print(f"      4. Review API rate limits")
            print(f"\n   Full traceback:")
            import traceback
            traceback.print_exc()
            raise

        # Step 3: Change detection
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
            print(f"\n❌ ERROR at Step 5: Change detection failed")
            print(f"   Location: analyzer.py:analyze_location() -> detector.analyze_changes()")
            print(f"   Error: {e}")
            print(f"\n   💡 Troubleshooting:")
            print(f"      1. Check vision analysis completed successfully")
            print(f"      2. Verify vision results contain expected data")
            print(f"\n   Full traceback:")
            import traceback
            traceback.print_exc()
            raise
        
        # Compile results
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
        
        # Add API cost
        complete_result['api_cost'] = self.vision.client.get_cost_summary()
        
        # Generate reports
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
            print(f"\n⚠️  WARNING: Report generation failed")
            print(f"   Location: analyzer.py:analyze_location() -> reporter.create_report()")
            print(f"   Error: {e}")
            print(f"\n   💡 Note: Analysis completed successfully but reports could not be generated")
            print(f"   Check file permissions for results directory")
            print(f"\n   Full traceback:")
            import traceback
            traceback.print_exc()
            complete_result['reports'] = {'error': str(e)}
        
        # Show summary
        self._print_summary(complete_result)
        
        return complete_result
    
    def _print_summary(self, result: Dict):
        """Print analysis summary"""
        
        print(f"\n{'='*70}")
        print("📊 ANALYSIS SUMMARY")
        print(f"{'='*70}")
        
        location = result['location']
        changes = result['changes']
        cost = result['api_cost']
        
        print(f"\n📍 Location: {location['name']}")
        print(f"   Coordinates: {location['lat']}, {location['lon']}")
        
        print(f"\n📅 Time Period:")
        print(f"   Before: {result['time_period']['before']}")
        print(f"   After: {result['time_period']['after']}")
        print(f"   Duration: {result['time_period']['days_elapsed']} days")
        
        print(f"\n🔍 Findings:")
        print(f"   Change Detected: {'Yes ⚠️' if changes['change_detected'] else 'No ✓'}")
        
        if changes['change_detected']:
            print(f"   Change Type: {changes['change_type']}")
            print(f"   Severity: {changes['severity'].upper()} ({changes['severity_score']}/10)")
            print(f"   Trend: {changes['trend'].title()}")
            print(f"   Confidence: {changes['confidence'].title()}")
            
            print(f"\n📊 Key Metrics:")
            metrics = changes['metrics']
            primary_metric = metrics.get('primary_metric_value', 'N/A')
            print(f"   {metrics.get('primary_metric_name', 'Change')}: {primary_metric}")
            
            if 'forest_loss_km2' in metrics:
                print(f"   Forest Loss: {metrics['forest_loss_km2']} km²")
                print(f"   Carbon Emissions: {metrics['carbon_emissions_tons']:,} tons CO2")
            
            if changes.get('detected_features'):
                print(f"\n🔍 New Features Detected:")
                for feature in changes['detected_features'][:5]:
                    print(f"      • {feature}")
        
        print(f"\n💰 API Usage:")
        print(f"   Total Calls: {cost['total_calls']}")
        print(f"   Vision Calls: {cost['vision_calls']}")
        print(f"   Text Calls: {cost['text_calls']}")
        print(f"   Cost: ${cost['total_cost_usd']:.4f}")
        
        print(f"\n⏱️  Execution Time: {result['execution_time_seconds']:.2f} seconds")
        
        print(f"\n📁 Reports Saved:")
        for report_type, path in result['reports'].items():
            print(f"   {report_type}: {path}")
        
        print(f"\n{'='*70}")
        print("✅ ANALYSIS COMPLETE")
        print(f"{'='*70}\n")


def main():
    """
    Command-line interface for satellite analyzer.
    
    Examples:
        # Analyze pre-defined region
        python analyze_satellite.py amazon_basin
        
        # Analyze custom coordinates
        python analyze_satellite.py --lat -3.0 --lon -60.0 --before 2024-01-01 --after 2025-01-01
        
        # With custom name
        python analyze_satellite.py --lat -3.0 --lon -60.0 --before 2024-01-01 --after 2025-01-01 --name "Amazon Site"
        
        # List available regions
        python analyze_satellite.py --list
    """
    
    parser = argparse.ArgumentParser(
        description='Satellite Environmental Monitor - Analyze environmental changes from satellite imagery',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s amazon_basin
  %(prog)s --lat -3.0 --lon -60.0 --before 2024-01-01 --after 2025-01-01
  %(prog)s --lat -3.0 --lon -60.0 --before 2024-01-01 --after 2025-01-01 --name "My Forest"
  %(prog)s --list
        """
    )
    
    # Positional argument for region
    parser.add_argument(
        'region',
        nargs='?',
        help='Pre-defined region to analyze (e.g., amazon_basin, arctic_greenland)'
    )
    
    # Custom coordinates
    parser.add_argument('--lat', type=float, help='Latitude (-90 to 90)')
    parser.add_argument('--lon', type=float, help='Longitude (-180 to 180)')
    parser.add_argument('--before', help='Before date (YYYY-MM-DD)')
    parser.add_argument('--after', help='After date (YYYY-MM-DD)')
    parser.add_argument('--name', help='Location name')
    parser.add_argument('--type', default='general',
                       choices=['deforestation', 'ice_melt', 'urban_sprawl', 'general'],
                       help='Analysis type')
    
    # Utility arguments
    parser.add_argument('--list', action='store_true',
                       help='List available pre-defined regions')
    parser.add_argument('--output', help='Output JSON file path (optional)')
    
    args = parser.parse_args()
    
    # List regions
    if args.list:
        print("\n📍 Available Pre-Defined Regions:\n")
        list_available_regions()
        return 0
    
    # Initialize analyzer
    try:
        analyzer = SatelliteAnalyzer()
    except Exception as e:
        print(f"\n❌ Failed to initialize analyzer: {e}")
        return 1
    
    # Run analysis
    try:
        if args.region:
            # Analyze pre-defined region
            result = analyzer.analyze_region(args.region)
        
        elif args.lat and args.lon and args.before and args.after:
            # Analyze custom location
            result = analyzer.analyze_location(
                lat=args.lat,
                lon=args.lon,
                before_date=args.before,
                after_date=args.after,
                location_name=args.name,
                analysis_type=args.type
            )
        
        else:
            print("\n❌ Error: Must provide either:")
            print("   1. A region name (e.g., 'amazon_basin'), or")
            print("   2. All of: --lat, --lon, --before, --after")
            print("\nUse --help for more information")
            return 1
        
        # Save to custom output if specified
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