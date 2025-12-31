"""
Paper Analyzer - Main Orchestrator
===================================
Ties all components together into a complete paper analysis pipeline.

Pipeline:
1. Process PDF → extract text + images
2. Analyze images → understand charts
3. Summarize text → get key findings
4. Combine results → complete analysis

This is the main file you'll run!

Usage:
    analyzer = PaperAnalyzer()
    result = analyzer.analyze_paper("research_paper.pdf")
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict

# Import our components
from pdf_processor import PDFProcessor
from vision_analyzer import VisionAnalyzer
from summarizer import PaperSummarizer
from client import ClaudeClient


class PaperAnalyzer:
    """
    Main paper analysis orchestrator.
    
    Usage:
        analyzer = PaperAnalyzer()
        result = analyzer.analyze_paper("paper.pdf")
        print(result)
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize analyzer with all components.
        
        Args:
            api_key: Claude API key (optional, uses env var if not provided)
        """
        print("\n📚 Initializing Paper Analyzer...")
        print("="*70)
        
        # Initialize shared Claude client (for cost tracking across all components)
        self.claude = ClaudeClient(api_key=api_key)
        
        # Initialize components
        self.pdf_processor = PDFProcessor()
        self.vision_analyzer = VisionAnalyzer(claude_client=self.claude)
        self.summarizer = PaperSummarizer(claude_client=self.claude)
        
        print("="*70)
        print("✅ All components ready!\n")
    
    def analyze_paper(self, 
                     pdf_path: str,
                     analyze_images: bool = True,
                     max_images: int = 20) -> Dict:
        """
        Complete analysis pipeline for a research paper PDF.
        
        Steps:
        1. Extract text and images from PDF
        2. Analyze charts/graphs with Vision API (if enabled)
        3. Summarize text content
        4. Combine everything into comprehensive analysis
        5. Save results
        
        Args:
            pdf_path: Path to PDF file
            analyze_images: Whether to analyze charts (costs API credits)
            max_images: Maximum images to analyze (cost control)
        
        Returns:
            Complete analysis dictionary
        """
        
        print("\n" + "="*70)
        print("STARTING RESEARCH PAPER ANALYSIS")
        print("="*70)
        print(f"File: {pdf_path}")
        print(f"Analyze images: {analyze_images}")
        if analyze_images:
            print(f"Max images: {max_images}")
        
        # STEP 1: Process PDF
        print("\n" + "="*70)
        print("STEP 1: PROCESSING PDF")
        print("="*70)
        
        content = self.pdf_processor.extract(
            pdf_path,
            extract_images=analyze_images
        )
        
        print(f"\n✓ Extracted:")
        print(f"   Pages: {content['pages']}")
        print(f"   Characters: {len(content['text']):,}")
        if analyze_images:
            print(f"   Images: {len(content['images'])}")
        
        # STEP 2: Analyze Images (if enabled)
        visual_insights = None
        if analyze_images and content['images']:
            print("\n" + "="*70)
            print("STEP 2: ANALYZING CHARTS AND GRAPHS")
            print("="*70)
            
            # Detect figure captions to filter important images
            captions = self.pdf_processor.detect_figure_captions(content['page_texts'])
            
            if captions:
                print(f"📊 Found {sum(len(c) for c in captions.values())} figure captions")
                
                # Filter to only images with captions (likely figures)
                important_images = self.vision_analyzer.filter_important_images(
                    content['images'],
                    captions
                )
            else:
                print(f"⚠️  No figure captions detected, analyzing all images")
                important_images = content['images']
            
            # Analyze images
            image_analyses = self.vision_analyzer.analyze_multiple(
                important_images,
                max_images=max_images
            )
            
            # Summarize visual insights
            visual_insights = self.vision_analyzer.summarize_visual_insights(image_analyses)
            visual_insights['detailed_analyses'] = image_analyses
            
            print(f"\n✓ Analyzed {visual_insights['successful_analyses']} images successfully")
        else:
            print("\n⏭️  STEP 2: Skipping image analysis")
        
        # STEP 3: Summarize Text
        print("\n" + "="*70)
        print("STEP 3: ANALYZING TEXT CONTENT")
        print("="*70)
        
        text_analysis = self.summarizer.full_analysis(
            text=content['text'],
            page_texts=content['page_texts'],
            first_page=content['page_texts'][0] if content['page_texts'] else None
        )
        
        # STEP 4: Combine Results
        print("\n" + "="*70)
        print("STEP 4: CREATING COMPREHENSIVE ANALYSIS")
        print("="*70)
        
        result = {
            'file_info': {
                'filename': content['file_name'],
                'pages': content['pages'],
                'analyzed_date': datetime.now().isoformat()
            },
            'metadata': text_analysis.get('metadata', {}),
            'text_analysis': {
                'synthesis': text_analysis.get('synthesis', {}),
                'section_count': len(text_analysis.get('section_summaries', []))
            },
            'visual_insights': visual_insights,
            'api_cost': self.claude.get_cost_estimate()
        }
        
        # STEP 5: Save Results
        output_path = self._save_results(result, pdf_path)
        print(f"\n💾 Results saved to: {output_path}")
        
        # Print summary
        self._print_summary(result)
        
        return result
    
    def _save_results(self, result: Dict, original_file: str) -> str:
        """
        Save analysis results to JSON file.

        Creates filename based on original PDF:
            research_paper.pdf → paper_analysis_research_paper_2025-01-30.json

        Saves to: src/services/research_paper_analyzer/results/
        """
        # Create output filename
        original_name = Path(original_file).stem
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_name = f"paper_analysis_{original_name}_{timestamp}.json"

        # Save in results folder within the research_paper_analyzer directory
        analyzer_dir = Path(__file__).parent  # src/services/research_paper_analyzer
        results_dir = analyzer_dir / "results"
        output_path = results_dir / output_name

        # Create results directory if needed
        results_dir.mkdir(exist_ok=True)

        # Save as formatted JSON
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)

        return str(output_path)
    
    def _print_summary(self, result: Dict):
        """Print a nice summary of the analysis"""
        
        print("\n" + "="*70)
        print("ANALYSIS SUMMARY")
        print("="*70)
        
        # Metadata
        metadata = result.get('metadata', {})
        if metadata and metadata.get('title'):
            print(f"\n📄 Paper: {metadata.get('title', 'Unknown')}")
            authors = metadata.get('authors', [])
            if authors and authors != ['Unknown']:
                print(f"👥 Authors: {', '.join(authors[:3])}")
                if len(authors) > 3:
                    print(f"           ... and {len(authors) - 3} more")
            print(f"📅 Published: {metadata.get('publication_date', 'Unknown')}")
        
        # Executive summary
        synthesis = result.get('text_analysis', {}).get('synthesis', {})
        exec_summary = synthesis.get('executive_summary', '')
        if exec_summary:
            print(f"\n📋 Executive Summary:")
            print(f"   {exec_summary}")
        
        # Main findings
        findings = synthesis.get('main_findings', [])
        if findings:
            print(f"\n🔍 Top Findings:")
            for i, finding in enumerate(findings[:3], 1):
                if isinstance(finding, dict):
                    text = finding.get('finding', '')
                    confidence = finding.get('confidence', '')
                    print(f"   {i}. {text}")
                    if confidence:
                        print(f"      (Confidence: {confidence})")
        
        # Visual insights
        visual = result.get('visual_insights')
        if visual:
            print(f"\n📊 Visual Analysis:")
            print(f"   Images analyzed: {visual.get('successful_analyses', 0)}")
            chart_types = visual.get('chart_types', {})
            if chart_types:
                print(f"   Chart types: {', '.join(f'{k} ({v})' for k, v in chart_types.items())}")
        
        # Cost
        cost = result.get('api_cost', {})
        print(f"\n💰 API Cost:")
        print(f"   Total calls: {cost.get('total_calls', 0)}")
        print(f"   Text calls: {cost.get('text_calls', 0)}")
        print(f"   Vision calls: {cost.get('vision_calls', 0)}")
        print(f"   Total cost: ${cost.get('total_cost_usd', 0):.4f}")
        
        print("\n" + "="*70)
        print("✅ Analysis complete! Check the results file for full details.")
        print("="*70)


# Main execution
if __name__ == "__main__":
    """
    Run the paper analyzer on a PDF.
    
    Usage:
        python analyzer.py research_paper.pdf
        
    Or with options:
        python analyzer.py research_paper.pdf --no-images
    """
    
    import sys
    
    print("\n" + "="*70)
    print("ECOLENS - RESEARCH PAPER ANALYZER")
    print("="*70)
    
    # Get file path from command line
    if len(sys.argv) < 2:
        print("\n❌ Error: No PDF file specified")
        print("\nUsage: python analyzer.py <pdf_file>")
        print("\nExample: python analyzer.py research_paper.pdf")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    
    # Check if file exists
    if not Path(pdf_file).exists():
        print(f"\n❌ Error: File not found: {pdf_file}")
        sys.exit(1)
    
    # Check for options
    analyze_images = '--no-images' not in sys.argv
    
    try:
        # Create analyzer
        print("\n📍 Step: Initializing Paper Analyzer...")
        analyzer = PaperAnalyzer()

        # Run analysis
        print(f"\n📍 Step: Starting analysis of {pdf_file}...")
        result = analyzer.analyze_paper(
            pdf_file,
            analyze_images=analyze_images,
            max_images=20
        )

        print("\n✅ Success! Results saved to results/ directory")

    except FileNotFoundError as e:
        print(f"\n❌ FileNotFoundError: {e}")
        print(f"\n📍 Location: File lookup failed")
        print(f"   File attempted: {pdf_file}")
        print(f"   Current directory: {Path.cwd()}")
        print(f"   File exists: {Path(pdf_file).exists()}")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()

    except ValueError as e:
        print(f"\n❌ ValueError: {e}")
        print(f"\n📍 Location: Validation or initialization failed")
        print("\nPossible causes:")
        print("  - Invalid PDF file format")
        print("  - Missing API key")
        print("  - Corrupted PDF data")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()

    except ImportError as e:
        print(f"\n❌ ImportError: {e}")
        print(f"\n📍 Location: Missing required module")
        print("\nRequired dependencies:")
        print("  - PyPDF2")
        print("  - pdf2image")
        print("  - anthropic")
        print("  - python-dotenv")
        print("\nInstall with: pip install -r requirements.txt")
        print("\nAdditional system requirements:")
        print("  - poppler (for pdf2image)")
        print("    macOS: brew install poppler")
        print("    Ubuntu: sudo apt install poppler-utils")
        print("    Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()

    except Exception as e:
        print(f"\n❌ Unexpected error ({type(e).__name__}): {e}")
        print(f"\n📍 Location: Error details below")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()