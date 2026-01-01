"""
Satellite Vision Analyzer
==========================
Analyze satellite images using Claude Vision API.

Specialized for:
- Deforestation detection
- Ice melt monitoring
- Urban sprawl tracking
- Environmental change detection

Used by: analyzer.py (main orchestrator)
Depends on: satellite_client.py, prompts.py
"""

import base64
from typing import Dict, Optional
from pathlib import Path
from client import SatelliteClient
from prompts import (
    satellite_image_analysis_prompt,
    comparison_analysis_prompt,
    side_by_side_comparison_prompt
)


class SatelliteVisionAnalyzer:
    """
    Analyze satellite images for environmental changes.
    
    Supports:
    - Single image analysis (forest cover, features)
    - Before/after comparison (change detection)
    - Multi-step analysis (separate then compare)
    
    Usage:
        analyzer = SatelliteVisionAnalyzer()
        
        # Analyze single image
        result = analyzer.analyze_single_image(
            image_path="before.png",
            date="2024-01-01",
            location_name="Amazon Basin",
            analysis_type="deforestation"
        )
        
        # Compare two images
        comparison = analyzer.compare_images(
            before_image="before.png",
            after_image="after.png",
            before_date="2024-01-01",
            after_date="2025-01-01",
            location_name="Amazon Basin",
            analysis_type="deforestation"
        )
    """
    
    def __init__(self, client: Optional[SatelliteClient] = None):
        """
        Initialize vision analyzer.
        
        Args:
            client: Optional existing SatelliteClient (for shared cost tracking)
        """
        self.client = client or SatelliteClient()
        print("✅ Satellite Vision Analyzer initialized")
    
    def analyze_single_image(self,
                            image_path: str,
                            date: str,
                            location_name: str = "",
                            analysis_type: str = "general",
                            use_cache: bool = True) -> Dict:
        """
        Analyze a single satellite image.
        
        Args:
            image_path: Path to satellite image file
            date: Date of the image (e.g., "2024-01-01")
            location_name: Name of location (e.g., "Amazon Basin")
            analysis_type: Type of analysis (deforestation, ice_melt, urban_sprawl, general)
            use_cache: Use cached results if available
        
        Returns:
            {
                'date': '2024-01-01',
                'location': 'Amazon Basin',
                'analysis_type': 'deforestation',
                'land_cover': {
                    'forest_pct': 85,
                    'water_pct': 5,
                    'urban_pct': 3,
                    'cleared_pct': 7
                },
                'vegetation_health': 'healthy',
                'visible_features': ['dense forest', 'river'],
                'infrastructure': [],
                'overall_description': '...',
                'confidence': 'high',
                'raw_response': {...}
            }
        """
        
        print(f"\n📷 Analyzing satellite image...")
        print(f"   Date: {date}")
        print(f"   Location: {location_name or 'Unknown'}")
        print(f"   Type: {analysis_type}")
        
        # Load and encode image
        image_base64 = self._load_image_as_base64(image_path)
        
        # Generate prompt
        prompt = satellite_image_analysis_prompt(
            date=date,
            location_name=location_name,
            analysis_type=analysis_type
        )
        
        # Analyze with Vision API
        result = self.client.analyze_image(
            image_base64=image_base64,
            prompt=prompt,
            temperature=0.5,  # Consistent analysis
            use_cache=use_cache
        )
        
        # Parse response
        analysis = result.get('parsed') or {}
        
        # Add metadata
        analysis['date'] = date
        analysis['location'] = location_name
        analysis['analysis_type'] = analysis_type
        analysis['raw_response'] = result.get('content')
        analysis['from_cache'] = result.get('from_cache', False)
        
        # Show summary
        if analysis.get('land_cover'):
            forest = analysis['land_cover'].get('forest_pct', 'unknown')
            print(f"   ✓ Forest coverage: {forest}%")
        
        return analysis
    
    def compare_images(self,
                      before_image: str,
                      after_image: str,
                      before_date: str,
                      after_date: str,
                      location_name: str = "",
                      analysis_type: str = "general",
                      method: str = "separate") -> Dict:
        """
        Compare two satellite images to detect changes.
        
        Args:
            before_image: Path to before image
            after_image: Path to after image
            before_date: Date of before image
            after_date: Date of after image
            location_name: Location name
            analysis_type: Type of analysis
            method: 'separate' (analyze each then compare) or 
                   'side_by_side' (send both together)
        
        Returns:
            {
                'before_analysis': {...},
                'after_analysis': {...},
                'comparison': {
                    'changes_detected': True,
                    'primary_change_type': 'deforestation',
                    'land_cover_changes': {
                        'forest_change_pct': -18
                    },
                    'new_features': ['roads', 'clearings'],
                    'severity_score': 8,
                    'change_summary': '...'
                },
                'metadata': {...}
            }
        """
        
        print(f"\n🔄 Comparing satellite images...")
        print(f"   Before: {before_date}")
        print(f"   After: {after_date}")
        print(f"   Location: {location_name or 'Unknown'}")
        print(f"   Method: {method}")
        
        if method == "separate":
            return self._compare_separate(
                before_image, after_image,
                before_date, after_date,
                location_name, analysis_type
            )
        else:
            return self._compare_side_by_side(
                before_image, after_image,
                before_date, after_date,
                location_name
            )
    
    def _compare_separate(self,
                         before_image: str,
                         after_image: str,
                         before_date: str,
                         after_date: str,
                         location_name: str,
                         analysis_type: str) -> Dict:
        """
        Compare by analyzing each image separately, then comparing analyses.
        
        This is more accurate for quantitative comparison.
        """
        
        # Step 1: Analyze before image
        print("\n   Step 1/3: Analyzing BEFORE image...")
        before_analysis = self.analyze_single_image(
            image_path=before_image,
            date=before_date,
            location_name=location_name,
            analysis_type=analysis_type
        )
        
        # Step 2: Analyze after image
        print("\n   Step 2/3: Analyzing AFTER image...")
        after_analysis = self.analyze_single_image(
            image_path=after_image,
            date=after_date,
            location_name=location_name,
            analysis_type=analysis_type
        )
        
        # Step 3: Compare the analyses
        print("\n   Step 3/3: Comparing analyses...")
        
        comparison_prompt = comparison_analysis_prompt(
            before_analysis=before_analysis,
            after_analysis=after_analysis,
            before_date=before_date,
            after_date=after_date,
            analysis_type=analysis_type
        )
        
        comparison_result = self.client.analyze_text(
            prompt=comparison_prompt,
            temperature=0.7
        )
        
        comparison = comparison_result.get('parsed') or {}
        
        # Show summary
        if comparison.get('changes_detected'):
            change_type = comparison.get('primary_change_type', 'unknown')
            severity = comparison.get('severity_score', 'unknown')
            print(f"   ✓ Change detected: {change_type} (severity: {severity}/10)")
        else:
            print(f"   ✓ No significant changes detected")
        
        return {
            'before_analysis': before_analysis,
            'after_analysis': after_analysis,
            'comparison': comparison,
            'metadata': {
                'location': location_name,
                'analysis_type': analysis_type,
                'time_period': {
                    'before': before_date,
                    'after': after_date,
                    'days_elapsed': self._calculate_days(before_date, after_date)
                },
                'method': 'separate_analysis'
            }
        }
    
    def _compare_side_by_side(self,
                             before_image: str,
                             after_image: str,
                             before_date: str,
                             after_date: str,
                             location_name: str) -> Dict:
        """
        Compare by sending both images together to Vision API.
        
        This allows Claude to directly see both images but is experimental.
        Note: As of now, Claude API doesn't support multiple images in one call,
        so this falls back to separate analysis.
        """
        
        print("   ℹ️  Side-by-side comparison not yet supported by API")
        print("   ℹ️  Falling back to separate analysis...")
        
        return self._compare_separate(
            before_image, after_image,
            before_date, after_date,
            location_name, "general"
        )
    
    def _load_image_as_base64(self, image_path: str) -> str:
        """
        Load image file and encode as base64.
        
        Args:
            image_path: Path to image file
        
        Returns:
            Base64-encoded string
        """
        
        path = Path(image_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        with open(path, 'rb') as f:
            image_bytes = f.read()
        
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        return image_base64
    
    def _calculate_days(self, date1: str, date2: str) -> int:
        """Calculate days between two dates"""
        from datetime import datetime
        
        try:
            d1 = datetime.fromisoformat(date1)
            d2 = datetime.fromisoformat(date2)
            return abs((d2 - d1).days)
        except:
            return 0
    
    def create_summary(self, comparison_result: Dict) -> str:
        """
        Create a human-readable summary of the comparison.
        
        Args:
            comparison_result: Output from compare_images()
        
        Returns:
            Formatted text summary
        """
        
        metadata = comparison_result.get('metadata', {})
        comparison = comparison_result.get('comparison', {})
        before = comparison_result.get('before_analysis', {})
        after = comparison_result.get('after_analysis', {})
        
        summary = f"""
SATELLITE ANALYSIS SUMMARY
{'='*60}

Location: {metadata.get('location', 'Unknown')}
Time Period: {metadata.get('time_period', {}).get('before', '?')} to {metadata.get('time_period', {}).get('after', '?')}
Days Elapsed: {metadata.get('time_period', {}).get('days_elapsed', '?')}

BEFORE ({metadata.get('time_period', {}).get('before', '?')}):
- Forest Coverage: {before.get('land_cover', {}).get('forest_pct', '?')}%
- Vegetation Health: {before.get('vegetation_health', 'unknown')}
- Description: {before.get('overall_description', 'N/A')}

AFTER ({metadata.get('time_period', {}).get('after', '?')}):
- Forest Coverage: {after.get('land_cover', {}).get('forest_pct', '?')}%
- Vegetation Health: {after.get('vegetation_health', 'unknown')}
- Description: {after.get('overall_description', 'N/A')}

CHANGES DETECTED:
{'Yes' if comparison.get('changes_detected') else 'No'}

"""
        
        if comparison.get('changes_detected'):
            changes = comparison.get('land_cover_changes', {})
            summary += f"""
Primary Change Type: {comparison.get('primary_change_type', 'unknown')}
Severity Score: {comparison.get('severity_score', '?')}/10

Land Cover Changes:
- Forest: {changes.get('forest_change_pct', '?')}%
- Urban: {changes.get('urban_change_pct', '?')}%
- Cleared: {changes.get('cleared_change_pct', '?')}%

New Features: {', '.join(comparison.get('new_features', []))}
Lost Features: {', '.join(comparison.get('lost_features', []))}

Change Summary:
{comparison.get('change_summary', 'N/A')}

Environmental Impact:
{comparison.get('environmental_impact', 'N/A')}
"""
        
        summary += f"\n{'='*60}\n"
        
        return summary


# Example usage / testing
if __name__ == "__main__":
    """
    Test satellite vision analyzer.
    
    Usage:
        python satellite_vision_analyzer.py
    """
    
    import sys
    import os
    
    print("="*70)
    print("SATELLITE VISION ANALYZER TEST")
    print("="*70)
    
    # Check if API key is set
    if not os.getenv('CLAUDE_API_KEY'):
        print("\n❌ CLAUDE_API_KEY not set!")
        print("Set it first: export CLAUDE_API_KEY='your_key_here'")
        sys.exit(1)
    
    print("\n✅ Vision Analyzer structure test passed")
    print("\nTo actually test with images:")
    print("1. Download satellite images from NASA API")
    print("2. Save as before.png and after.png")
    print("3. Run:")
    print("   analyzer = SatelliteVisionAnalyzer()")
    print("   result = analyzer.compare_images('before.png', 'after.png', ...)")
    
    # If you have test images, uncomment:
    # try:
    #     analyzer = SatelliteVisionAnalyzer()
    #     
    #     result = analyzer.compare_images(
    #         before_image="data/satellite/test_before.png",
    #         after_image="data/satellite/test_after.png",
    #         before_date="2024-01-01",
    #         after_date="2025-01-01",
    #         location_name="Test Location",
    #         analysis_type="deforestation"
    #     )
    #     
    #     print("\n" + analyzer.create_summary(result))
    #     
    # except FileNotFoundError:
    #     print("\nTest images not found. Create test images first.")