"""
Satellite Analysis Prompts
===========================
Prompts for Claude Vision API to analyze satellite images.

Used by: vision_comparator.py
"""

from typing import Dict


def satellite_image_analysis_prompt(
    date: str,
    location_name: str = "",
    analysis_type: str = "general"
) -> str:
    """
    Prompt for analyzing a single satellite image.
    
    Args:
        date: Date of the image (e.g., "2024-01-01")
        location_name: Optional location name
        analysis_type: Type of analysis (deforestation, ice_melt, urban, general)
    
    Returns:
        Prompt string for Vision API
    """
    
    location_text = f" of {location_name}" if location_name else ""
    
    # Base prompt for all types
    base_prompt = f"""You are analyzing a satellite image{location_text} from {date}.

This is an Earth observation satellite image (likely from Landsat or Sentinel).

Please analyze this image and provide:

1. **Land Cover Assessment**: What types of land cover do you see?
   - Forest/vegetation (estimate % of image)
   - Water bodies
   - Urban/developed areas
   - Bare ground/cleared land
   - Other features

2. **Vegetation Health**: Describe the vegetation condition
   - Healthy dense forest (dark green)
   - Sparse or degraded vegetation (light green/brown)
   - Dead or stressed vegetation

3. **Human Infrastructure**: Identify any human-made features
   - Roads, highways
   - Buildings, settlements
   - Agricultural patterns
   - Industrial areas

4. **Natural Features**: Identify natural landmarks
   - Rivers, lakes
   - Mountains, terrain
   - Geological features

5. **Overall Assessment**: Describe the scene in 2-3 sentences"""
    
    # Add type-specific guidance
    if analysis_type == "deforestation":
        specific_prompt = """

**DEFORESTATION FOCUS**:
Pay special attention to:
- Forest density and coverage
- Cleared areas or patches
- Linear patterns indicating roads/logging
- Signs of agricultural conversion
- Edge effects at forest boundaries"""
    
    elif analysis_type == "ice_melt":
        specific_prompt = """

**ICE/SNOW FOCUS**:
Pay special attention to:
- Ice/snow coverage (white/bright areas)
- Exposed land or water (darker areas)
- Glacier boundaries
- Meltwater or crevasses"""
    
    elif analysis_type == "urban_sprawl":
        specific_prompt = """

**URBAN DEVELOPMENT FOCUS**:
Pay special attention to:
- Built-up areas (gray/white patches)
- Road networks
- Residential vs commercial areas
- New development on urban edges
- Infrastructure expansion"""
    
    else:
        specific_prompt = ""
    
    # JSON output format
    json_format = """

Return your analysis as a JSON object:
{
  "land_cover": {
    "forest_pct": 0-100,
    "water_pct": 0-100,
    "urban_pct": 0-100,
    "cleared_pct": 0-100,
    "dominant_type": "forest/urban/water/mixed"
  },
  "vegetation_health": "healthy/moderate/degraded/sparse",
  "visible_features": ["feature1", "feature2", ...],
  "infrastructure": ["road networks", "settlements", ...] or [],
  "natural_features": ["river", "mountains", ...],
  "overall_description": "2-3 sentence description",
  "confidence": "high/medium/low",
  "image_quality_notes": "cloud cover, clarity issues, etc."
}

Return ONLY the JSON object, no other text."""
    
    return base_prompt + specific_prompt + json_format


def comparison_analysis_prompt(
    before_analysis: Dict,
    after_analysis: Dict,
    before_date: str,
    after_date: str,
    analysis_type: str = "general"
) -> str:
    """
    Prompt for comparing two satellite image analyses.
    
    Args:
        before_analysis: Analysis dict from before image
        after_analysis: Analysis dict from after image
        before_date: Date of before image
        after_date: Date of after image
        analysis_type: Type of analysis
    
    Returns:
        Prompt string for comparison
    """
    
    # Format analyses for the prompt
    before_text = f"""
Before Image ({before_date}):
- Forest: {before_analysis.get('land_cover', {}).get('forest_pct', 'unknown')}%
- Urban: {before_analysis.get('land_cover', {}).get('urban_pct', 'unknown')}%
- Cleared: {before_analysis.get('land_cover', {}).get('cleared_pct', 'unknown')}%
- Features: {', '.join(before_analysis.get('visible_features', []))}
- Description: {before_analysis.get('overall_description', 'N/A')}
"""
    
    after_text = f"""
After Image ({after_date}):
- Forest: {after_analysis.get('land_cover', {}).get('forest_pct', 'unknown')}%
- Urban: {after_analysis.get('land_cover', {}).get('urban_pct', 'unknown')}%
- Cleared: {after_analysis.get('land_cover', {}).get('cleared_pct', 'unknown')}%
- Features: {', '.join(after_analysis.get('visible_features', []))}
- Description: {after_analysis.get('overall_description', 'N/A')}
"""
    
    base_prompt = f"""You are comparing two satellite image analyses to detect changes.

{before_text}

{after_text}

Time period: {before_date} to {after_date}

Please analyze the changes between these two time periods:

1. **Land Cover Changes**: Calculate the change in each category
   - Forest change (%)
   - Urban change (%)
   - Cleared land change (%)

2. **New Features**: What new infrastructure or features appeared?

3. **Lost Features**: What features disappeared or were removed?

4. **Change Severity**: Rate the environmental impact (1-10 scale)

5. **Change Type**: Categorize the primary change
   - Deforestation
   - Urban expansion
   - Ice melt
   - Agricultural conversion
   - Natural disaster impact
   - Minimal/no change"""
    
    # Add type-specific analysis
    if analysis_type == "deforestation":
        specific_prompt = """

**DEFORESTATION ANALYSIS**:
- Estimate area of forest lost (in %)
- Identify deforestation patterns (logging, agriculture, roads)
- Assess severity of ecological impact
- Note any signs of illegal logging or rapid clearing"""
    
    elif analysis_type == "ice_melt":
        specific_prompt = """

**ICE MELT ANALYSIS**:
- Estimate ice coverage change (in %)
- Assess melt rate and severity
- Identify exposed land or water
- Note any concerning accelerations"""
    
    elif analysis_type == "urban_sprawl":
        specific_prompt = """

**URBAN EXPANSION ANALYSIS**:
- Estimate new development area (in %)
- Identify growth patterns (sprawl, infill, planned)
- Assess impact on natural areas
- Note infrastructure expansion"""
    
    else:
        specific_prompt = ""
    
    json_format = """

Return your analysis as a JSON object:
{
  "changes_detected": true/false,
  "primary_change_type": "deforestation/urban/ice_melt/agricultural/minimal",
  "land_cover_changes": {
    "forest_change_pct": -18,  # negative = loss, positive = gain
    "urban_change_pct": 5,
    "cleared_change_pct": 15
  },
  "new_features": ["new roads", "cleared areas", ...],
  "lost_features": ["forest patches", ...],
  "severity_score": 1-10,
  "severity_explanation": "why this severity score",
  "environmental_impact": "description of ecological impact",
  "change_summary": "2-3 sentence summary of what changed",
  "confidence": "high/medium/low",
  "concerns": ["concern1", "concern2", ...] or []
}

Return ONLY the JSON object, no other text."""
    
    return base_prompt + specific_prompt + json_format


def side_by_side_comparison_prompt(
    before_date: str,
    after_date: str,
    location_name: str = ""
) -> str:
    """
    Prompt for direct visual comparison of two images side-by-side.
    
    This is used when sending both images together to Claude Vision API.
    
    Args:
        before_date: Date of before image
        after_date: Date of after image
        location_name: Optional location name
    
    Returns:
        Prompt string for side-by-side comparison
    """
    
    location_text = f" of {location_name}" if location_name else ""
    
    prompt = f"""You are viewing two satellite images{location_text} taken at different times.

Left image: {before_date}
Right image: {after_date}

Please directly compare these two images and identify:

1. **Visual Differences**: What changed between the images?
   - Color changes (greens to browns, dark to light, etc.)
   - Texture changes (smooth to patchy, uniform to fragmented)
   - New patterns or structures

2. **Spatial Changes**: Where did changes occur?
   - Concentrated in certain areas?
   - Uniform across the image?
   - Edge vs center changes

3. **Magnitude**: How significant are the changes?
   - Dramatic transformation
   - Moderate changes
   - Subtle differences
   - Minimal/no change

4. **Change Indicators**: What visual clues indicate environmental change?
   - Loss of vegetation (green to brown)
   - New development (gray patches, linear features)
   - Water changes (blue areas expanding/shrinking)

Return your analysis as a JSON object:
{
  "visual_differences": "detailed description of what changed",
  "change_locations": "where changes are concentrated",
  "change_magnitude": "dramatic/moderate/subtle/minimal",
  "forest_change_visible": true/false,
  "forest_change_description": "what you see",
  "new_infrastructure_visible": true/false,
  "infrastructure_description": "roads, buildings, etc.",
  "estimated_impact": "high/medium/low",
  "change_summary": "one sentence summary",
  "confidence": "high/medium/low"
}

Return ONLY the JSON object."""
    
    return prompt


# Example usage / testing
if __name__ == "__main__":
    """
    Test prompt generation.
    
    Usage:
        python prompts.py
    """
    
    print("="*70)
    print("SATELLITE ANALYSIS PROMPTS")
    print("="*70)
    
    # Test single image analysis prompt
    print("\n1. SINGLE IMAGE ANALYSIS PROMPT (Deforestation)")
    print("="*70)
    prompt1 = satellite_image_analysis_prompt(
        date="2024-01-01",
        location_name="Amazon Basin",
        analysis_type="deforestation"
    )
    print(prompt1[:500] + "...")
    
    # Test comparison prompt
    print("\n\n2. COMPARISON ANALYSIS PROMPT")
    print("="*70)
    
    sample_before = {
        'land_cover': {'forest_pct': 85, 'urban_pct': 5, 'cleared_pct': 10},
        'visible_features': ['dense forest', 'river'],
        'overall_description': 'Healthy dense forest with a river'
    }
    
    sample_after = {
        'land_cover': {'forest_pct': 67, 'urban_pct': 5, 'cleared_pct': 28},
        'visible_features': ['patchy forest', 'roads', 'clearings'],
        'overall_description': 'Forest fragmented with new roads and clearings'
    }
    
    prompt2 = comparison_analysis_prompt(
        before_analysis=sample_before,
        after_analysis=sample_after,
        before_date="2024-01-01",
        after_date="2025-01-01",
        analysis_type="deforestation"
    )
    print(prompt2[:500] + "...")
    
    print("\n\n✅ Prompts generated successfully")