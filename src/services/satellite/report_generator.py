"""
Report Generator
================
Generate comprehensive reports from satellite analysis results.

Formats:
- JSON (complete data)
- Markdown (human-readable summary)
- CSV (for spreadsheet analysis)

Used by: analyze_satellite.py
"""

import json
import csv
from typing import Dict, List
from pathlib import Path
from datetime import datetime

try:
    from satellite_config import RESULTS_DIR
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from satellite_config import RESULTS_DIR


class ReportGenerator:
    """
    Generate analysis reports in multiple formats.
    
    Usage:
        generator = ReportGenerator()
        
        report = generator.create_report(
            analysis_result=complete_analysis,
            location_name="Amazon Basin"
        )
        
        # Report saved to:
        # - results/amazon_basin_2025-01-30_analysis.json
        # - results/amazon_basin_2025-01-30_report.md
    """
    
    def __init__(self):
        """Initialize report generator"""
        
        # Ensure results directory exists
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        
        print("✅ Report Generator initialized")
    
    def create_report(self,
                     analysis_result: Dict,
                     location_name: str = "satellite_location") -> Dict:
        """
        Create complete analysis report in multiple formats.
        
        Args:
            analysis_result: Complete analysis output from analyzer
            location_name: Location name for filenames
        
        Returns:
            {
                'json_path': '/path/to/report.json',
                'markdown_path': '/path/to/report.md',
                'csv_path': '/path/to/metrics.csv'
            }
        """
        
        print(f"\n📄 Generating analysis report...")
        
        # Clean location name for filename
        clean_name = self._clean_filename(location_name)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        base_filename = f"{clean_name}_{timestamp}"
        
        # Generate JSON report
        json_path = self._generate_json(analysis_result, base_filename)
        print(f"   ✓ JSON report: {json_path}")
        
        # Generate Markdown summary
        md_path = self._generate_markdown(analysis_result, base_filename)
        print(f"   ✓ Markdown report: {md_path}")
        
        # Generate CSV metrics
        csv_path = self._generate_csv(analysis_result, base_filename)
        print(f"   ✓ CSV metrics: {csv_path}")
        
        print(f"\n✓ Reports saved to: {RESULTS_DIR}")
        
        return {
            'json_path': str(json_path),
            'markdown_path': str(md_path),
            'csv_path': str(csv_path)
        }
    
    def _generate_json(self, data: Dict, base_filename: str) -> Path:
        """Generate complete JSON report"""
        
        filepath = RESULTS_DIR / f"{base_filename}_analysis.json"
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return filepath
    
    def _generate_markdown(self, data: Dict, base_filename: str) -> Path:
        """Generate human-readable Markdown summary"""
        
        filepath = RESULTS_DIR / f"{base_filename}_report.md"
        
        # Build markdown content
        md = self._build_markdown_content(data)
        
        with open(filepath, 'w') as f:
            f.write(md)
        
        return filepath
    
    def _generate_csv(self, data: Dict, base_filename: str) -> Path:
        """Generate CSV of key metrics"""
        
        filepath = RESULTS_DIR / f"{base_filename}_metrics.csv"
        
        # Extract key metrics
        metrics = self._extract_metrics_for_csv(data)
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=metrics[0].keys())
            writer.writeheader()
            writer.writerows(metrics)
        
        return filepath
    
    def _build_markdown_content(self, data: Dict) -> str:
        """Build Markdown report content"""
        
        # Extract data sections
        location = data.get('location', {})
        time_period = data.get('time_period', {})
        changes = data.get('changes', {})
        images = data.get('images', {})
        vision_analysis = data.get('vision_analysis', {})
        
        # Build report
        md = f"""# Satellite Environmental Analysis Report

## 📍 Location Information

**Location**: {location.get('name', 'Unknown')}  
**Coordinates**: {location.get('lat', 'N/A')}°, {location.get('lon', 'N/A')}°  
**Area Monitored**: {changes.get('metrics', {}).get('total_area_km2', 'N/A')} km²

---

## 📅 Time Period

**Before Date**: {time_period.get('before', 'N/A')}  
**After Date**: {time_period.get('after', 'N/A')}  
**Time Span**: {time_period.get('days_elapsed', 'N/A')} days

---

## 🔍 Analysis Summary

**Analysis Date**: {data.get('analysis_date', datetime.now().isoformat())}  
**Change Detected**: {'Yes ⚠️' if changes.get('change_detected') else 'No ✓'}  
**Change Type**: {changes.get('change_type', 'N/A')}  
**Severity**: {changes.get('severity', 'N/A').upper()} ({changes.get('severity_score', 0)}/10)  
**Trend**: {changes.get('trend', 'N/A').title()}  
**Confidence**: {changes.get('confidence', 'N/A').title()}

"""
        
        # Add change details if detected
        if changes.get('change_detected'):
            md += f"""
---

## 📊 Quantified Changes

"""
            metrics = changes.get('metrics', {})
            
            # Format metrics
            for key, value in metrics.items():
                if key == 'primary_metric_name' or key == 'primary_metric_value':
                    continue
                
                # Format the key
                formatted_key = key.replace('_', ' ').title()
                
                # Format the value
                if isinstance(value, float):
                    formatted_value = f"{value:,.2f}"
                elif isinstance(value, int):
                    formatted_value = f"{value:,}"
                else:
                    formatted_value = str(value)
                
                md += f"**{formatted_key}**: {formatted_value}  \n"
            
            # Add detected features
            if changes.get('detected_features'):
                md += f"""
### New Features Detected

"""
                for feature in changes['detected_features']:
                    md += f"- {feature}\n"
            
            # Add lost features
            if changes.get('lost_features'):
                md += f"""
### Features Lost

"""
                for feature in changes['lost_features']:
                    md += f"- {feature}\n"
        
        # Add vision analysis details
        if vision_analysis:
            md += f"""
---

## 👁️ Vision Analysis Details

### Before Image ({time_period.get('before', 'N/A')})

"""
            before = vision_analysis.get('before_analysis', {})
            if before.get('land_cover'):
                md += "**Land Cover**:\n"
                for key, value in before['land_cover'].items():
                    formatted_key = key.replace('_', ' ').title()
                    md += f"- {formatted_key}: {value}\n"
            
            md += f"\n**Description**: {before.get('overall_description', 'N/A')}\n"
            
            md += f"""
### After Image ({time_period.get('after', 'N/A')})

"""
            after = vision_analysis.get('after_analysis', {})
            if after.get('land_cover'):
                md += "**Land Cover**:\n"
                for key, value in after['land_cover'].items():
                    formatted_key = key.replace('_', ' ').title()
                    md += f"- {formatted_key}: {value}\n"
            
            md += f"\n**Description**: {after.get('overall_description', 'N/A')}\n"
        
        # Add environmental impact
        if changes.get('environmental_impact'):
            md += f"""
---

## 🌍 Environmental Impact

{changes['environmental_impact']}
"""
        
        # Add change summary
        if changes.get('change_summary'):
            md += f"""
---

## 📝 Change Summary

{changes['change_summary']}
"""
        
        # Add image links
        if images:
            md += f"""
---

## 🖼️ Satellite Images

**Before Image**: [{images.get('before', {}).get('date', 'N/A')}]({images.get('before', {}).get('image_path', '#')})  
**After Image**: [{images.get('after', {}).get('date', 'N/A')}]({images.get('after', {}).get('image_path', '#')})

**Before Image URL**: {images.get('before', {}).get('image_url', 'N/A')}  
**After Image URL**: {images.get('after', {}).get('image_url', 'N/A')}
"""
        
        # Add API cost
        if data.get('api_cost'):
            cost = data['api_cost']
            md += f"""
---

## 💰 API Usage

**Total API Calls**: {cost.get('total_calls', 'N/A')}  
**Vision Calls**: {cost.get('vision_calls', 'N/A')}  
**Text Calls**: {cost.get('text_calls', 'N/A')}  
**Estimated Cost**: ${cost.get('total_cost_usd', 'N/A')}
"""
        
        # Footer
        md += f"""
---

*Report generated by EcoLens Satellite Monitor*  
*Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return md
    
    def _extract_metrics_for_csv(self, data: Dict) -> List[Dict]:
        """Extract key metrics into CSV format"""
        
        location = data.get('location', {})
        time_period = data.get('time_period', {})
        changes = data.get('changes', {})
        metrics = changes.get('metrics', {})
        
        # Build CSV row
        row = {
            'location_name': location.get('name', ''),
            'latitude': location.get('lat', ''),
            'longitude': location.get('lon', ''),
            'before_date': time_period.get('before', ''),
            'after_date': time_period.get('after', ''),
            'days_elapsed': time_period.get('days_elapsed', ''),
            'change_detected': changes.get('change_detected', False),
            'change_type': changes.get('change_type', ''),
            'severity': changes.get('severity', ''),
            'severity_score': changes.get('severity_score', 0),
            'trend': changes.get('trend', ''),
            'confidence': changes.get('confidence', ''),
        }
        
        # Add all metrics
        for key, value in metrics.items():
            if key not in ['primary_metric_name', 'primary_metric_value']:
                row[key] = value
        
        return [row]
    
    def _clean_filename(self, name: str) -> str:
        """Clean location name for use in filename"""
        
        # Remove invalid characters
        valid_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        cleaned = "".join(c if c in valid_chars else '_' for c in name)
        
        # Remove multiple underscores
        while '__' in cleaned:
            cleaned = cleaned.replace('__', '_')
        
        # Trim
        cleaned = cleaned.strip('_').lower()
        
        # Limit length
        if len(cleaned) > 50:
            cleaned = cleaned[:50]
        
        return cleaned or 'location'


# Example usage / testing
if __name__ == "__main__":
    """
    Test report generator.
    
    Usage:
        python report_generator.py
    """
    
    print("="*70)
    print("REPORT GENERATOR TEST")
    print("="*70)
    
    generator = ReportGenerator()
    
    # Sample analysis result
    sample_result = {
        'location': {
            'name': 'Amazon Rainforest Test Site',
            'lat': -3.4653,
            'lon': -62.2159
        },
        'time_period': {
            'before': '2024-01-01',
            'after': '2025-01-01',
            'days_elapsed': 365
        },
        'changes': {
            'change_detected': True,
            'change_type': 'deforestation',
            'severity': 'high',
            'severity_score': 8,
            'trend': 'accelerating',
            'confidence': 'high',
            'metrics': {
                'total_area_km2': 123.4,
                'forest_loss_km2': 22.2,
                'forest_loss_pct': 18.0,
                'carbon_emissions_tons': 4440,
                'rate_per_day': 0.061
            },
            'detected_features': ['new roads', 'cleared areas', 'logging sites'],
            'lost_features': ['dense forest patches'],
            'change_summary': 'Significant deforestation detected with new road construction and extensive clearing.',
            'environmental_impact': 'High impact to forest ecosystem with substantial carbon emissions and habitat loss.'
        },
        'vision_analysis': {
            'before_analysis': {
                'land_cover': {
                    'forest_pct': 85,
                    'water_pct': 5,
                    'urban_pct': 3,
                    'cleared_pct': 7
                },
                'overall_description': 'Dense tropical rainforest with healthy canopy coverage.'
            },
            'after_analysis': {
                'land_cover': {
                    'forest_pct': 67,
                    'water_pct': 5,
                    'urban_pct': 3,
                    'cleared_pct': 25
                },
                'overall_description': 'Forest fragmentation visible with new cleared areas and road networks.'
            }
        },
        'images': {
            'before': {
                'date': '2024-01-01',
                'image_path': 'data/satellite/downloads/test/2024-01-01.png',
                'image_url': 'https://example.com/before.png'
            },
            'after': {
                'date': '2025-01-01',
                'image_path': 'data/satellite/downloads/test/2025-01-01.png',
                'image_url': 'https://example.com/after.png'
            }
        },
        'api_cost': {
            'total_calls': 3,
            'vision_calls': 2,
            'text_calls': 1,
            'total_cost_usd': 0.08
        },
        'analysis_date': datetime.now().isoformat()
    }
    
    # Generate report
    print("\n" + "="*70)
    print("Generating Report")
    print("="*70)
    
    paths = generator.create_report(
        analysis_result=sample_result,
        location_name='Amazon Test Site'
    )
    
    print(f"\n✅ Report generated successfully!")
    print(f"\nGenerated files:")
    for format_type, path in paths.items():
        print(f"   {format_type}: {path}")
    
    # Show markdown preview
    print(f"\n" + "="*70)
    print("Markdown Preview (first 500 chars)")
    print("="*70)
    
    with open(paths['markdown_path'], 'r') as f:
        preview = f.read()[:500]
        print(preview + "...")
    
    print("\n" + "="*70)
    print("✅ Report generator test complete")
    print("="*70)