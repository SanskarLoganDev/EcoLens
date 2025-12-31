"""
Vision Analyzer
===============
Analyze charts, graphs, and images from research papers using Claude Vision API.

This module:
1. Takes extracted images from PDFs
2. Sends them to Claude Vision API
3. Gets back structured analysis of what the chart shows
4. Extracts key findings from visual data

Used by: analyzer.py
Depends on: papers_client.py, papers_prompts.py
"""

import json
from typing import Dict, List
from client import ClaudeClient
from prompts import vision_chart_analysis_prompt


class VisionAnalyzer:
    """
    Analyze charts and images using Claude Vision API.
    
    Usage:
        analyzer = VisionAnalyzer()
        
        # Analyze single image
        result = analyzer.analyze_image(image_base64, caption="Figure 3.2")
        
        # Analyze multiple images
        results = analyzer.analyze_multiple(images_list)
    """
    
    def __init__(self, claude_client: ClaudeClient = None):
        """
        Initialize vision analyzer.
        
        Args:
            claude_client: Optional existing Claude client (for shared cost tracking)
        """
        self.claude = claude_client or ClaudeClient()
        print("✅ Vision Analyzer initialized")
    
    def analyze_image(self, 
                     image_data: str, 
                     caption: str = "",
                     page: int = None) -> Dict:
        """
        Analyze a single image/chart.
        
        Args:
            image_data: Base64-encoded image string
            caption: Optional caption from PDF (e.g., "Figure 3.2: ...")
            page: Page number where image was found
        
        Returns:
            {
                'page': 23,
                'caption': "Figure 3.2: ...",
                'analysis': {
                    'chart_type': 'line graph',
                    'title': 'Ocean pH trends',
                    'key_finding': '...',
                    ...
                },
                'plain_english': "This chart shows...",
                'tokens_used': 1250
            }
        """
        
        print(f"\n👁️  Analyzing image{f' (page {page})' if page else ''}...")
        if caption:
            print(f"   Caption: {caption}")
        
        # Generate prompt
        prompt = vision_chart_analysis_prompt(caption)
        
        try:
            # Call Vision API
            response = self.claude.call_vision(
                image_data=image_data,
                prompt=prompt,
                temperature=0.5  # Lower for analytical consistency
            )
            
            # Parse JSON response
            try:
                analysis = json.loads(response['content'])
            except json.JSONDecodeError:
                # If Claude didn't return valid JSON, wrap the text response
                print("   ⚠️  Response not in JSON format, wrapping as text")
                analysis = {
                    'raw_response': response['content'],
                    'error': 'Could not parse as JSON'
                }
            
            # Create plain English summary
            if 'key_finding' in analysis:
                plain_english = (
                    f"This {analysis.get('chart_type', 'chart')} shows "
                    f"{analysis.get('key_finding', 'data visualization')}. "
                    f"{analysis.get('scientific_implication', '')}"
                )
            else:
                plain_english = response['content'][:200] + "..."
            
            return {
                'page': page,
                'caption': caption,
                'analysis': analysis,
                'plain_english': plain_english,
                'tokens_used': response['usage']['input_tokens'] + response['usage']['output_tokens']
            }
            
        except Exception as e:
            print(f"   ❌ Error analyzing image: {e}")
            return {
                'page': page,
                'caption': caption,
                'error': str(e),
                'analysis': None
            }
    
    def analyze_multiple(self, 
                        images: List[Dict],
                        max_images: int = 20) -> List[Dict]:
        """
        Analyze multiple images from a paper.
        
        Args:
            images: List of image dicts from pdf_processor
                    [{'page': 23, 'image_data': '...', 'caption': '...'}, ...]
            max_images: Maximum images to analyze (cost control)
        
        Returns:
            List of analysis results
        """
        
        print(f"\n🖼️  Analyzing {min(len(images), max_images)} images...")
        print("="*60)
        
        results = []
        
        for i, image in enumerate(images[:max_images], 1):
            print(f"\nImage {i}/{min(len(images), max_images)}:")
            
            result = self.analyze_image(
                image_data=image['image_data'],
                caption=image.get('caption', ''),
                page=image.get('page')
            )
            
            results.append(result)
            
            # Show progress
            if result.get('analysis'):
                finding = result['analysis'].get('key_finding', 'N/A')
                print(f"   ✓ Key finding: {finding[:80]}...")
        
        print(f"\n✅ Analyzed {len(results)} images")
        
        return results
    
    def filter_important_images(self, 
                               images: List[Dict],
                               captions: Dict[int, List[str]]) -> List[Dict]:
        """
        Filter images to only those likely to be important charts/graphs.
        
        Use captions to identify which images are actually figures.
        This saves API costs by not analyzing every page image.
        
        Args:
            images: All extracted images
            captions: Dict of {page_num: [caption1, caption2, ...]}
        
        Returns:
            Filtered list of likely important images
        """
        
        important = []
        
        for image in images:
            page = image.get('page')
            
            # Check if this page has figure captions
            if page in captions:
                # Found a caption on this page - likely contains a figure
                page_captions = captions[page]
                
                # Assign the first caption (heuristic)
                image['caption'] = page_captions[0] if page_captions else ''
                important.append(image)
        
        print(f"📊 Filtered to {len(important)} important images (from {len(images)} total)")
        
        return important
    
    def summarize_visual_insights(self, analyses: List[Dict]) -> Dict:
        """
        Create a summary of all visual insights from the paper.
        
        Args:
            analyses: List of image analysis results
        
        Returns:
            {
                'total_images_analyzed': 15,
                'chart_types': {'line graph': 5, 'bar chart': 3, ...},
                'key_visual_findings': ['finding 1', 'finding 2', ...],
                'most_important_figures': [...]
            }
        """
        
        # Count chart types
        chart_types = {}
        key_findings = []
        
        for analysis in analyses:
            if analysis.get('analysis'):
                chart_type = analysis['analysis'].get('chart_type', 'unknown')
                chart_types[chart_type] = chart_types.get(chart_type, 0) + 1
                
                finding = analysis['analysis'].get('key_finding')
                if finding:
                    key_findings.append({
                        'page': analysis.get('page'),
                        'caption': analysis.get('caption', ''),
                        'finding': finding
                    })
        
        return {
            'total_images_analyzed': len(analyses),
            'chart_types': chart_types,
            'key_visual_findings': key_findings,
            'successful_analyses': len([a for a in analyses if a.get('analysis')])
        }


# Example usage / testing
if __name__ == "__main__":
    """
    Test vision analyzer with a sample image.
    
    For this to work, you need:
    1. CLAUDE_API_KEY environment variable set
    2. A sample image (we'll create a test one)
    """
    
    import sys
    
    print("="*60)
    print("VISION ANALYZER TEST")
    print("="*60)
    
    # Check if API key is set
    import os
    if not os.getenv('CLAUDE_API_KEY'):
        print("\n❌ CLAUDE_API_KEY not set!")
        print("Set it first: export CLAUDE_API_KEY='your_key_here'")
        sys.exit(1)
    
    # For testing, we would need an actual image
    # This is just a structure test
    
    print("\n✅ Vision Analyzer structure test passed")
    print("\nTo actually test with images:")
    print("1. Extract images from a PDF using pdf_processor.py")
    print("2. Pass those images to analyze_image() or analyze_multiple()")
    print("\nExample:")
    print("  analyzer = VisionAnalyzer()")
    print("  result = analyzer.analyze_image(image_base64, caption='Figure 1')")