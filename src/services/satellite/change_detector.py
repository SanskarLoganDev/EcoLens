"""
Environmental Change Detector
==============================
Quantify and analyze environmental changes from satellite image comparisons.

Features:
- Calculate forest loss/gain
- Estimate carbon emissions
- Severity scoring
- Trend analysis
- Change classification

Used by: analyze_satellite.py
Depends on: geo_utils.py, config.py
"""

from typing import Dict

try:
    from satellite_config import (
        CARBON_EMISSION_FACTORS,
        SEVERITY_THRESHOLDS,
        DEFAULT_BBOX_SIZE
    )
    from geo_utils import (
        calculate_area_km2,
        estimate_carbon_emissions
    )
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from satellite_config import *
    from geo_utils import calculate_area_km2, estimate_carbon_emissions


class ChangeDetector:
    """
    Detect and quantify environmental changes.
    
    Takes output from SatelliteVisionAnalyzer and converts it into
    quantified metrics like area lost, carbon emissions, severity.
    
    Usage:
        detector = ChangeDetector()
        
        # Analyze vision comparison results
        changes = detector.analyze_changes(
            vision_comparison=comparison_result,
            lat=-3.0,
            analysis_type='deforestation'
        )
        
        print(f"Forest lost: {changes['forest_loss_km2']} km²")
        print(f"Carbon emissions: {changes['carbon_emissions_tons']} tons")
    """
    
    def __init__(self):
        """Initialize change detector"""
        print("✅ Change Detector initialized")
    
    def analyze_changes(self,
                       vision_comparison: Dict,
                       lat: float,
                       dim: float = DEFAULT_BBOX_SIZE,
                       analysis_type: str = "general") -> Dict:
        """
        Analyze and quantify changes from vision comparison.
        
        Args:
            vision_comparison: Output from SatelliteVisionAnalyzer.compare_images()
            lat: Latitude (for area calculation)
            dim: Image dimension in degrees
            analysis_type: Type of analysis (deforestation, ice_melt, urban_sprawl)
        
        Returns:
            {
                'change_detected': True/False,
                'change_type': 'deforestation',
                'severity': 'high',
                'severity_score': 8,
                'metrics': {
                    'total_area_km2': 123.4,
                    'forest_loss_km2': 22.2,
                    'forest_loss_pct': 18,
                    'carbon_emissions_tons': 4440,
                    'rate_per_day': 0.06
                },
                'detected_features': [...],
                'trend': 'accelerating',
                'confidence': 'high'
            }
        """
        
        print(f"\n📊 Analyzing environmental changes...")
        
        # Extract comparison data
        comparison = vision_comparison.get('comparison', {})
        metadata = vision_comparison.get('metadata', {})
        
        # Calculate total area monitored
        total_area_km2 = calculate_area_km2(dim, lat)
        print(f"   Area monitored: {total_area_km2:.2f} km²")
        
        # Check if changes detected
        changes_detected = comparison.get('changes_detected', False)
        
        if not changes_detected:
            print(f"   ✓ No significant changes detected")
            return self._no_change_result(total_area_km2, metadata)
        
        # Extract change metrics
        change_type = comparison.get('primary_change_type', 'unknown')
        severity_score = comparison.get('severity_score', 0)
        land_cover_changes = comparison.get('land_cover_changes', {})
        
        print(f"   Change type: {change_type}")
        print(f"   Severity: {severity_score}/10")
        
        # Analyze based on type
        if analysis_type == "deforestation" or change_type == "deforestation":
            metrics = self._analyze_deforestation(
                land_cover_changes,
                total_area_km2,
                metadata.get('time_period', {})
            )
        
        elif analysis_type == "ice_melt" or change_type == "ice_melt":
            metrics = self._analyze_ice_melt(
                land_cover_changes,
                total_area_km2,
                metadata.get('time_period', {})
            )
        
        elif analysis_type == "urban_sprawl" or change_type == "urban":
            metrics = self._analyze_urban_sprawl(
                land_cover_changes,
                total_area_km2,
                metadata.get('time_period', {})
            )
        
        else:
            metrics = self._analyze_general(
                land_cover_changes,
                total_area_km2,
                metadata.get('time_period', {})
            )
        
        # Determine severity level
        severity = self._calculate_severity(severity_score, metrics)
        
        # Determine trend
        trend = self._determine_trend(comparison, metrics)
        
        # Show summary
        print(f"   ✓ {metrics.get('primary_metric_name', 'Change')}: {metrics.get('primary_metric_value', 'N/A')}")
        
        return {
            'change_detected': True,
            'change_type': change_type,
            'severity': severity,
            'severity_score': severity_score,
            'metrics': metrics,
            'detected_features': comparison.get('new_features', []),
            'lost_features': comparison.get('lost_features', []),
            'trend': trend,
            'confidence': comparison.get('confidence', 'medium'),
            'change_summary': comparison.get('change_summary', ''),
            'environmental_impact': comparison.get('environmental_impact', '')
        }
    
    def _analyze_deforestation(self,
                               land_cover_changes: Dict,
                               total_area_km2: float,
                               time_period: Dict) -> Dict:
        """Analyze deforestation-specific metrics"""
        
        # Get forest change percentage
        forest_change_pct = land_cover_changes.get('forest_change_pct', 0)
        
        if forest_change_pct >= 0:
            # Forest gain (reforestation)
            return {
                'total_area_km2': total_area_km2,
                'forest_gain_km2': total_area_km2 * (forest_change_pct / 100),
                'forest_change_pct': forest_change_pct,
                'carbon_sequestered_tons': 0,  # Simplified
                'rate_per_day': 0,
                'primary_metric_name': 'Forest gain',
                'primary_metric_value': f"{forest_change_pct}%"
            }
        
        # Forest loss (deforestation)
        forest_loss_pct = abs(forest_change_pct)
        forest_loss_km2 = total_area_km2 * (forest_loss_pct / 100)
        
        # Estimate carbon emissions
        carbon_tons = estimate_carbon_emissions(
            area_lost_km2=forest_loss_km2,
            region_type='tropical_forest'
        )
        
        # Calculate rate
        days_elapsed = time_period.get('days_elapsed', 365)
        if days_elapsed > 0:
            rate_per_day = forest_loss_km2 / days_elapsed
        else:
            rate_per_day = 0
        
        return {
            'total_area_km2': round(total_area_km2, 2),
            'forest_loss_km2': round(forest_loss_km2, 2),
            'forest_loss_pct': round(forest_loss_pct, 1),
            'carbon_emissions_tons': round(carbon_tons, 0),
            'rate_per_day': round(rate_per_day, 3),
            'primary_metric_name': 'Forest loss',
            'primary_metric_value': f"{forest_loss_pct}% ({forest_loss_km2:.2f} km²)"
        }
    
    def _analyze_ice_melt(self,
                         land_cover_changes: Dict,
                         total_area_km2: float,
                         time_period: Dict) -> Dict:
        """Analyze ice melt metrics"""
        
        # Assuming ice is tracked as "water_pct" increasing
        water_change = land_cover_changes.get('water_change_pct', 0)
        
        ice_loss_pct = abs(water_change) if water_change > 0 else 0
        ice_loss_km2 = total_area_km2 * (ice_loss_pct / 100)
        
        days_elapsed = time_period.get('days_elapsed', 365)
        rate_per_day = ice_loss_km2 / days_elapsed if days_elapsed > 0 else 0
        
        return {
            'total_area_km2': round(total_area_km2, 2),
            'ice_loss_km2': round(ice_loss_km2, 2),
            'ice_loss_pct': round(ice_loss_pct, 1),
            'melt_rate_km2_per_day': round(rate_per_day, 3),
            'primary_metric_name': 'Ice melt',
            'primary_metric_value': f"{ice_loss_pct}% ({ice_loss_km2:.2f} km²)"
        }
    
    def _analyze_urban_sprawl(self,
                             land_cover_changes: Dict,
                             total_area_km2: float,
                             time_period: Dict) -> Dict:
        """Analyze urban expansion metrics"""
        
        urban_change_pct = land_cover_changes.get('urban_change_pct', 0)
        urban_expansion_km2 = total_area_km2 * (urban_change_pct / 100)
        
        # Also check cleared land
        cleared_change = land_cover_changes.get('cleared_change_pct', 0)
        
        days_elapsed = time_period.get('days_elapsed', 365)
        rate_per_day = urban_expansion_km2 / days_elapsed if days_elapsed > 0 else 0
        
        return {
            'total_area_km2': round(total_area_km2, 2),
            'urban_expansion_km2': round(urban_expansion_km2, 2),
            'urban_expansion_pct': round(urban_change_pct, 1),
            'natural_area_lost_km2': round(total_area_km2 * (cleared_change / 100), 2),
            'expansion_rate_km2_per_day': round(rate_per_day, 3),
            'primary_metric_name': 'Urban expansion',
            'primary_metric_value': f"{urban_change_pct}% ({urban_expansion_km2:.2f} km²)"
        }
    
    def _analyze_general(self,
                        land_cover_changes: Dict,
                        total_area_km2: float,
                        time_period: Dict) -> Dict:
        """Analyze general land cover changes"""
        
        return {
            'total_area_km2': round(total_area_km2, 2),
            'land_cover_changes': land_cover_changes,
            'primary_metric_name': 'Land cover change',
            'primary_metric_value': str(land_cover_changes)
        }
    
    def _calculate_severity(self, severity_score: int, metrics: Dict) -> str:
        """
        Calculate severity level from score and metrics.
        
        Args:
            severity_score: 1-10 score from vision analysis
            metrics: Calculated metrics
        
        Returns:
            'critical', 'high', 'moderate', 'low', or 'minimal'
        """
        
        # Also check percentage loss if available
        loss_pct = (
            metrics.get('forest_loss_pct') or
            metrics.get('ice_loss_pct') or
            metrics.get('urban_expansion_pct') or
            0
        )
        
        # Use thresholds
        if severity_score >= 9 or loss_pct >= SEVERITY_THRESHOLDS['critical']:
            return 'critical'
        elif severity_score >= 7 or loss_pct >= SEVERITY_THRESHOLDS['high']:
            return 'high'
        elif severity_score >= 5 or loss_pct >= SEVERITY_THRESHOLDS['moderate']:
            return 'moderate'
        elif severity_score >= 3 or loss_pct >= SEVERITY_THRESHOLDS['low']:
            return 'low'
        else:
            return 'minimal'
    
    def _determine_trend(self, comparison: Dict, metrics: Dict) -> str:
        """
        Determine if change is accelerating, stable, or slowing.
        
        This is a simplified heuristic based on available data.
        """
        
        # Check if vision analysis mentioned trend
        impact = comparison.get('environmental_impact', '').lower()
        summary = comparison.get('change_summary', '').lower()
        
        accelerating_keywords = ['rapid', 'accelerat', 'increasing', 'growing', 'expanding']
        slowing_keywords = ['slow', 'decreas', 'declining', 'reducing']
        
        text = impact + ' ' + summary
        
        if any(k in text for k in accelerating_keywords):
            return 'accelerating'
        elif any(k in text for k in slowing_keywords):
            return 'slowing'
        else:
            return 'stable'
    
    def _no_change_result(self, total_area_km2: float, metadata: Dict) -> Dict:
        """Return result for no change detected"""
        
        return {
            'change_detected': False,
            'change_type': 'none',
            'severity': 'minimal',
            'severity_score': 0,
            'metrics': {
                'total_area_km2': round(total_area_km2, 2)
            },
            'detected_features': [],
            'lost_features': [],
            'trend': 'stable',
            'confidence': 'high',
            'change_summary': 'No significant changes detected',
            'environmental_impact': 'Minimal'
        }


# Example usage / testing
if __name__ == "__main__":
    """
    Test change detector.
    
    Usage:
        python change_detector.py
    """
    
    print("="*70)
    print("CHANGE DETECTOR TEST")
    print("="*70)
    
    detector = ChangeDetector()
    
    # Simulate vision comparison result
    sample_comparison = {
        'comparison': {
            'changes_detected': True,
            'primary_change_type': 'deforestation',
            'severity_score': 8,
            'land_cover_changes': {
                'forest_change_pct': -18,  # 18% loss
                'urban_change_pct': 2,
                'cleared_change_pct': 15
            },
            'new_features': ['roads', 'cleared areas', 'logging sites'],
            'lost_features': ['dense forest patches'],
            'confidence': 'high',
            'change_summary': 'Significant deforestation with new road construction',
            'environmental_impact': 'High impact to forest ecosystem'
        },
        'metadata': {
            'location': {'name': 'Test Amazon Location'},
            'time_period': {
                'before': '2024-01-01',
                'after': '2025-01-01',
                'days_elapsed': 365
            }
        }
    }
    
    # Analyze changes
    print("\n" + "="*70)
    print("TEST: Deforestation Analysis")
    print("="*70)
    
    result = detector.analyze_changes(
        vision_comparison=sample_comparison,
        lat=-3.0,
        dim=0.10,
        analysis_type='deforestation'
    )
    
    print(f"\n📋 Analysis Results:")
    print(f"   Change detected: {result['change_detected']}")
    print(f"   Change type: {result['change_type']}")
    print(f"   Severity: {result['severity']} ({result['severity_score']}/10)")
    print(f"   Trend: {result['trend']}")
    print(f"\n📊 Metrics:")
    for key, value in result['metrics'].items():
        print(f"   {key}: {value}")
    
    print(f"\n🌳 Detected features:")
    for feature in result['detected_features']:
        print(f"   • {feature}")
    
    print("\n" + "="*70)
    print("✅ Change detector test complete")
    print("="*70)