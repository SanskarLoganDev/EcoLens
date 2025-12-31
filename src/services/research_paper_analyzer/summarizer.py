"""
Paper Summarizer
================
Summarize research paper text using Claude API.

This module:
1. Chunks long papers into manageable sections
2. Analyzes each section separately
3. Synthesizes a comprehensive summary
4. Extracts key findings, methodology, confidence levels

Used by: analyzer.py
Depends on: papers_client.py, papers_prompts.py
"""

import json
from typing import Dict, List
from client import ClaudeClient
from prompts import (
    section_summary_prompt,
    full_synthesis_prompt,
    extract_metadata_prompt
)


class PaperSummarizer:
    """
    Summarize research paper text content.
    
    Usage:
        summarizer = PaperSummarizer()
        
        # Quick summary
        summary = summarizer.summarize_text(paper_text)
        
        # Detailed analysis
        analysis = summarizer.full_analysis(paper_text, page_texts)
    """
    
    def __init__(self, claude_client: ClaudeClient = None):
        """
        Initialize paper summarizer.
        
        Args:
            claude_client: Optional existing Claude client (for shared cost tracking)
        """
        self.claude = claude_client or ClaudeClient()
        print("✅ Paper Summarizer initialized")
    
    def extract_metadata_from_text(self, first_page_text: str) -> Dict:
        """
        Extract paper metadata from the first page.
        
        Many PDFs don't have proper metadata, so we extract from text.
        
        Args:
            first_page_text: Text from the first page
        
        Returns:
            {
                'title': 'Paper title',
                'authors': ['Author 1', 'Author 2'],
                'publication_date': '2024',
                ...
            }
        """
        
        print("\nℹ️  Extracting metadata from first page...")
        
        prompt = extract_metadata_prompt(first_page_text)
        
        try:
            response = self.claude.call(
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.3  # Low temp for factual extraction
            )
            
            metadata = json.loads(response['content'])
            print(f"   ✓ Extracted: {metadata.get('title', 'Unknown')}")
            return metadata
            
        except Exception as e:
            print(f"   ⚠️  Could not extract metadata: {e}")
            return {}
    
    def summarize_text(self, 
                      text: str,
                      max_length: int = 8000) -> Dict:
        """
        Quick summary of paper text.
        
        For short papers or when you want a quick overview.
        
        Args:
            text: Full paper text (or relevant excerpt)
            max_length: Max characters to analyze at once
        
        Returns:
            {
                'summary': 'Executive summary',
                'key_points': [...],
                'methodology': '...',
                ...
            }
        """
        
        print("\n📝 Creating quick summary...")
        
        # Truncate if too long
        if len(text) > max_length:
            print(f"   ⚠️  Text too long ({len(text)} chars), truncating to {max_length}")
            text = text[:max_length] + "..."
        
        prompt = section_summary_prompt("Full Paper", text)
        
        try:
            response = self.claude.call(
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.5
            )
            
            summary = json.loads(response['content'])
            print(f"   ✓ Summary created")
            return summary
            
        except Exception as e:
            print(f"   ❌ Error creating summary: {e}")
            return {
                'error': str(e),
                'raw_response': response['content'] if 'response' in locals() else None
            }
    
    def analyze_by_sections(self, 
                          page_texts: List[str],
                          pages_per_section: int = 5) -> List[Dict]:
        """
        Analyze paper by splitting into sections.
        
        Better for long papers - analyzes in chunks then synthesizes.
        
        Args:
            page_texts: List of text from each page
            pages_per_section: How many pages to group into a section
        
        Returns:
            List of section summaries
        """
        
        print(f"\n📚 Analyzing paper in sections ({pages_per_section} pages each)...")
        
        section_summaries = []
        total_pages = len(page_texts)
        
        # Group pages into sections
        for i in range(0, total_pages, pages_per_section):
            section_num = (i // pages_per_section) + 1
            section_pages = page_texts[i:i + pages_per_section]
            section_text = "\n\n".join(section_pages)
            
            print(f"\nSection {section_num} (pages {i+1}-{min(i+pages_per_section, total_pages)}):")
            
            # Truncate very long sections
            if len(section_text) > 6000:
                print(f"   ⚠️  Section too long, truncating...")
                section_text = section_text[:6000] + "..."
            
            # Analyze section
            prompt = section_summary_prompt(f"Section {section_num}", section_text)
            
            try:
                response = self.claude.call(
                    messages=[{'role': 'user', 'content': prompt}],
                    temperature=0.5
                )
                
                summary = json.loads(response['content'])
                section_summaries.append(summary)
                
                # Show progress
                main_points = summary.get('main_points', [])
                if main_points:
                    print(f"   ✓ Main point: {main_points[0][:60]}...")
                
            except Exception as e:
                print(f"   ❌ Error analyzing section: {e}")
                section_summaries.append({
                    'section': f"Section {section_num}",
                    'error': str(e)
                })
        
        print(f"\n✅ Analyzed {len(section_summaries)} sections")
        return section_summaries
    
    def synthesize_sections(self, section_summaries: List[Dict]) -> Dict:
        """
        Synthesize section summaries into a complete paper summary.
        
        Args:
            section_summaries: List of section summary dicts
        
        Returns:
            {
                'executive_summary': '...',
                'main_findings': [...],
                'methodology_quality': '...',
                ...
            }
        """
        
        print("\n🔄 Synthesizing all sections...")
        
        prompt = full_synthesis_prompt(section_summaries)
        
        try:
            response = self.claude.call(
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.7  # Higher for synthesis
            )
            
            synthesis = json.loads(response['content'])
            print(f"   ✓ Synthesis complete")
            
            # Show executive summary
            exec_summary = synthesis.get('executive_summary', '')
            if exec_summary:
                print(f"\n📋 Executive Summary:")
                print(f"   {exec_summary[:150]}...")
            
            return synthesis
            
        except Exception as e:
            print(f"   ❌ Error synthesizing: {e}")
            return {
                'error': str(e),
                'section_summaries': section_summaries  # Fallback to sections
            }
    
    def full_analysis(self, 
                     text: str,
                     page_texts: List[str],
                     first_page: str = None) -> Dict:
        """
        Complete analysis pipeline.
        
        Recommended approach for comprehensive papers.
        
        Steps:
        1. Extract metadata from first page
        2. Analyze by sections
        3. Synthesize into complete summary
        
        Args:
            text: Full paper text (for reference)
            page_texts: Text from each page (for section analysis)
            first_page: Text from first page (for metadata)
        
        Returns:
            Complete analysis dict
        """
        
        print("\n" + "="*60)
        print("STARTING FULL PAPER ANALYSIS")
        print("="*60)
        
        # Step 1: Extract metadata
        metadata = {}
        if first_page or (page_texts and len(page_texts) > 0):
            first_page_text = first_page or page_texts[0]
            metadata = self.extract_metadata_from_text(first_page_text)
        
        # Step 2: Analyze sections
        section_summaries = self.analyze_by_sections(page_texts)
        
        # Step 3: Synthesize
        synthesis = self.synthesize_sections(section_summaries)
        
        # Combine results
        print("\n" + "="*60)
        print("ANALYSIS COMPLETE")
        print("="*60)
        
        return {
            'metadata': metadata,
            'section_summaries': section_summaries,
            'synthesis': synthesis,
            'total_pages': len(page_texts)
        }


# Example usage / testing
if __name__ == "__main__":
    """
    Test summarizer with sample text.
    """
    
    import sys
    import os
    
    print("="*60)
    print("PAPER SUMMARIZER TEST")
    print("="*60)
    
    try:
        print("\n📍 Step: Checking environment...")

        # Check API key
        if not os.getenv('CLAUDE_API_KEY'):
            print("\n❌ CLAUDE_API_KEY not set!")
            print("Set it first:")
            print("  PowerShell: $env:CLAUDE_API_KEY='your_key_here'")
            print("  Bash: export CLAUDE_API_KEY='your_key_here'")
            print("  Or add to .env file in project root")
            sys.exit(1)

        print("✓ API key found")

        # Test with sample text
        sample_text = """
        Ocean Acidification: A Global Crisis

        Authors: Smith et al.
        Published: 2024

        Abstract: This paper examines the impact of increasing atmospheric CO2
        on ocean chemistry. We analyzed 500 coral reef sites across 30 years
        and found a 30% increase in ocean acidity since pre-industrial times.

        Methodology: We collected water samples from 500 sites globally...

        Results: Ocean pH has decreased from 8.25 to 8.06, representing...

        Conclusion: Immediate action is required to reduce CO2 emissions...
        """

        print("\n📍 Step: Initializing summarizer...")
        summarizer = PaperSummarizer()

        print("\n📍 Step: Testing quick summary...")
        summary = summarizer.summarize_text(sample_text)

        print("\n📊 Summary Result:")
        print(json.dumps(summary, indent=2))

        print("\n✅ Summarizer test complete")

    except ImportError as e:
        print(f"\n❌ ImportError: {e}")
        print(f"\n📍 Location: Missing required module")
        print("\nMake sure all dependencies are installed:")
        print("  pip install anthropic python-dotenv")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()

    except ValueError as e:
        print(f"\n❌ ValueError: {e}")
        print(f"\n📍 Location: API initialization or validation failed")
        print("\nPossible causes:")
        print("  - Invalid API key")
        print("  - API key format issue")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()

    except Exception as e:
        print(f"\n❌ Unexpected error ({type(e).__name__}): {e}")
        print(f"\n📍 Location: Error details below")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()