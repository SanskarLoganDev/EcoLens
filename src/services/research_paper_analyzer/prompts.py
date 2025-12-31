"""
Prompt Templates for Research Paper Analysis
=============================================
All prompts for Claude API calls in the papers feature.

Contains prompts for:
1. Chart/image analysis (Vision API)
2. Section summarization (Text API)
3. Full paper synthesis (Text API)
4. Citation extraction (Text API)

Used by: vision_analyzer.py, summarizer.py
"""

from typing import Dict, List


def vision_chart_analysis_prompt(caption: str = "") -> str:
    """
    Prompt for Claude Vision API to analyze a chart/graph.
    
    This prompt is sent WITH an image to the Vision API.
    
    Args:
        caption: Optional caption from the PDF (e.g., "Figure 3.2: Ocean pH trends")
    
    Returns:
        Prompt string for Vision API
    """
    
    caption_text = f"\nImage caption: {caption}" if caption else ""
    
    prompt = f"""You are analyzing a scientific chart or graph from a research paper.{caption_text}

Please analyze this image and provide:

1. **Chart Type**: What kind of visualization is this? (line graph, bar chart, scatter plot, map, etc.)

2. **Title/Topic**: What is this chart showing?

3. **Axes/Labels**: What are the x and y axes? What units are used?

4. **Key Data Points**: What are the main values or trends visible?

5. **Trend/Pattern**: What pattern or trend does this show? (increasing, decreasing, cyclical, etc.)

6. **Key Finding**: In ONE sentence, what is the most important insight from this chart?

7. **Confidence/Uncertainty**: Are there error bars, confidence intervals, or uncertainty indicators?

8. **Scientific Implication**: Why does this chart matter? What does it tell us?

Return your analysis as a JSON object with this structure:
{{
  "chart_type": "type of chart",
  "title": "what the chart shows",
  "axes": {{"x": "x-axis description", "y": "y-axis description"}},
  "key_data": "important values or ranges",
  "trend": "overall pattern",
  "key_finding": "one sentence insight",
  "confidence_indicators": "error bars, uncertainty, or 'none'",
  "scientific_implication": "why this matters"
}}

Important: Return ONLY the JSON object, no other text."""
    
    return prompt


def section_summary_prompt(section_title: str, section_text: str) -> str:
    """
    Prompt for summarizing a single section of a paper.
    
    Papers are too long to analyze at once, so we chunk by section.
    
    Args:
        section_title: Name of the section (e.g., "Methodology", "Results")
        section_text: The text content of that section
    
    Returns:
        Prompt string for Text API
    """
    
    prompt = f"""You are analyzing a section from a scientific research paper.

Section: {section_title}

Text:
{section_text}

Please extract:

1. **Main Points**: What are the 3-5 key points from this section?

2. **Methodology** (if applicable): What research methods were used?

3. **Findings** (if applicable): What were the main results or conclusions?

4. **Data/Evidence**: What data or evidence supports the findings?

5. **Confidence Level**: How certain are the authors about their claims? (very high, high, medium, low)

6. **Technical Terms**: List any important technical terms and briefly define them.

Return your analysis as a JSON object:
{{
  "section": "{section_title}",
  "main_points": ["point 1", "point 2", "point 3"],
  "methodology": "methods used (if applicable)",
  "findings": ["finding 1", "finding 2"],
  "evidence": "supporting data or evidence",
  "confidence_level": "high/medium/low",
  "technical_terms": {{"term": "definition", ...}}
}}

Return ONLY the JSON object."""
    
    return prompt


def full_synthesis_prompt(section_summaries: List[Dict]) -> str:
    """
    Prompt for synthesizing all section summaries into a complete paper summary.
    
    After analyzing each section separately, we combine them into a final summary.
    
    Args:
        section_summaries: List of section summary dicts from previous API calls
    
    Returns:
        Prompt string for final synthesis
    """
    
    # Format section summaries for the prompt
    summaries_text = "\n\n".join([
        f"Section: {s.get('section', 'Unknown')}\n"
        f"Main Points: {', '.join(s.get('main_points', []))}\n"
        f"Findings: {', '.join(s.get('findings', []))}"
        for s in section_summaries
    ])
    
    prompt = f"""You are creating a comprehensive summary of a scientific research paper.

Here are summaries of each section:

{summaries_text}

Based on these section summaries, create an integrated paper summary:

1. **Executive Summary**: Summarize the entire paper in 2-3 sentences (plain English).

2. **Main Findings**: What are the 5 most important findings from this paper?

3. **Methodology Quality**: Assess the research methods (rigorous, adequate, limited, unclear).

4. **Evidence Strength**: How strong is the evidence? (very high, high, medium, low, insufficient).

5. **Key Uncertainties**: What are the main uncertainties or limitations?

6. **Policy Implications**: What are the practical implications for policy or action?

7. **Contradictions**: Are there any internal contradictions or conflicting results?

8. **Novel Contributions**: What's new or different compared to existing research?

Return as JSON:
{{
  "executive_summary": "2-3 sentence overview",
  "main_findings": [
    {{
      "finding": "specific finding",
      "confidence": "very high/high/medium/low",
      "evidence": "supporting evidence"
    }}
  ],
  "methodology_quality": "assessment",
  "evidence_strength": "very high/high/medium/low",
  "key_uncertainties": ["uncertainty 1", "uncertainty 2"],
  "policy_implications": ["implication 1", "implication 2"],
  "contradictions": ["contradiction if any"] or null,
  "novel_contributions": ["what's new"]
}}

Return ONLY the JSON object."""
    
    return prompt


def citation_context_prompt(paper_summary: Dict, cited_papers: List[str]) -> str:
    """
    Prompt for understanding how this paper relates to its citations.
    
    Optional advanced feature: Compare this paper to papers it cites.
    
    Args:
        paper_summary: The summary dict of the current paper
        cited_papers: List of titles of papers cited
    
    Returns:
        Prompt for understanding citation context
    """
    
    findings = paper_summary.get('main_findings', [])
    findings_text = "\n".join([f"- {f.get('finding', '')}" for f in findings[:3]])
    
    citations_text = "\n".join([f"- {title}" for title in cited_papers[:10]])
    
    prompt = f"""You are analyzing how a research paper relates to previous work.

Current Paper's Main Findings:
{findings_text}

Papers Cited (top 10):
{citations_text}

Based on the paper's findings and the citations, answer:

1. **Research Lineage**: Does this paper build on, contradict, or extend previous work?

2. **Key Precedents**: Which cited papers are most important to this research?

3. **Knowledge Gap**: What gap in previous research does this paper fill?

4. **Agreement/Disagreement**: Does this paper agree or disagree with previous findings?

Return as JSON:
{{
  "research_lineage": "builds on / contradicts / extends",
  "key_precedents": [
    {{
      "paper": "paper title",
      "relevance": "how it's relevant"
    }}
  ],
  "knowledge_gap": "what gap this fills",
  "agreements": ["agrees with X about Y"],
  "disagreements": ["contradicts X about Y"] or null
}}

Return ONLY the JSON object."""
    
    return prompt


def extract_metadata_prompt(first_page_text: str) -> str:
    """
    Prompt to extract paper metadata from the first page.
    
    Args:
        first_page_text: Text from the first page of the PDF
    
    Returns:
        Prompt for metadata extraction
    """
    
    prompt = f"""Extract metadata from this research paper's first page.

Text from first page:
{first_page_text}

Extract:
1. **Title**: Full paper title
2. **Authors**: List of author names
3. **Publication Date**: Year or full date
4. **Journal/Conference**: Where was this published?
5. **DOI**: Digital Object Identifier (if present)
6. **Keywords**: Research keywords or topics
7. **Abstract**: The abstract text (if present)

Return as JSON:
{{
  "title": "paper title",
  "authors": ["author 1", "author 2"],
  "publication_date": "YYYY or YYYY-MM-DD",
  "publication_venue": "journal or conference name",
  "doi": "DOI if present",
  "keywords": ["keyword1", "keyword2"],
  "abstract": "abstract text if present"
}}

If any field is not found, use null.
Return ONLY the JSON object."""
    
    return prompt


# Example usage / testing
if __name__ == "__main__":
    """
    Test the prompt templates by printing them.
    """
    
    print("="*70)
    print("VISION CHART ANALYSIS PROMPT")
    print("="*70)
    print(vision_chart_analysis_prompt("Figure 3.2: Ocean pH trends 1950-2020"))
    
    print("\n\n")
    
    print("="*70)
    print("SECTION SUMMARY PROMPT")
    print("="*70)
    sample_text = "We analyzed 500 coral reef sites across 30 years..."
    print(section_summary_prompt("Methodology", sample_text))
    
    print("\n\n")
    
    print("="*70)
    print("METADATA EXTRACTION PROMPT")
    print("="*70)
    sample_first_page = "Ocean Acidification: A Global Crisis\nAuthors: Smith et al.\n2024"
    print(extract_metadata_prompt(sample_first_page))