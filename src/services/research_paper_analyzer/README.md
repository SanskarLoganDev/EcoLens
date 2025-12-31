# Research Paper Analyzer

An AI-powered tool that analyzes scientific research papers using Claude AI with vision capabilities. It extracts metadata, summarizes content, analyzes figures and charts, and provides comprehensive insights from academic PDFs.

## Features

- **Metadata Extraction**: Automatically extracts title, authors, abstract, DOI, and publication details
- **Text Analysis**: Summarizes key findings, methodology, and conclusions
- **Visual Insights**: Analyzes charts, graphs, and figures using Claude's vision capabilities
- **Structured Output**: Generates comprehensive JSON reports with all extracted information
- **Cost Tracking**: Monitors API usage and costs for each analysis

## Project Structure

```
research_paper_analyzer/
├── analyze_papers.py      # Main orchestrator script
├── pdf_processor.py       # PDF text and image extraction
├── summarizer.py          # Claude AI text analysis
├── client.py              # Enhanced Claude API wrapper with vision support
├── research_papers/       # Input PDFs go here
│   ├── geomorphology.pdf
│   └── ocean_acidification.pdf
├── results/               # Output JSON reports saved here
│   └── paper_analysis_*.json
└── README.md
```

## Prerequisites

### Python Packages
```bash
pip install anthropic python-dotenv PyPDF2 pdf2image Pillow
```

### System Dependencies

**Windows:**
1. Download Poppler: https://github.com/oschwartz10612/poppler-windows/releases/
2. Extract to: `C:\Program Files\poppler-XX.XX.X`
3. Add to PATH: `C:\Program Files\poppler-XX.XX.X\Library\bin`
4. Restart terminal/IDE
5. Test with: `pdftoppm -v`

**macOS:**
```bash
brew install poppler
```

**Ubuntu/Debian:**
```bash
sudo apt install poppler-utils
```

### Environment Variables

Create a `.env` file in the project root:
```
CLAUDE_API_KEY=your_api_key_here
```

## How to Run

### Basic Usage

From the project root directory:

```bash
python src/services/research_paper_analyzer/analyze_papers.py <path_to_pdf>
```

### Examples

**Analyze a single paper:**
```bash
python src/services/research_paper_analyzer/analyze_papers.py src/services/research_paper_analyzer/research_papers/geomorphology.pdf
```

**Analyze another paper:**
```bash
python src/services/research_paper_analyzer/analyze_papers.py src/services/research_paper_analyzer/research_papers/ocean_acidification.pdf
```

**Analyze a paper with no images:**
```bash
python src\services\research_paper_analyzer\analyze_papers.py E:\Coding-practice\Projects\EcoLens\src\services\research_paper_analyzer\research_papers\climate_change.pdf --no-images
```

### Output

Results are saved in the `results/` folder with timestamped filenames:
```
results/paper_analysis_geomorphology_2025-12-31_16-55-46.json
```

Each result includes:
- **metadata**: Paper details (title, authors, DOI, abstract, etc.)
- **text_analysis**: Comprehensive summary, key findings, methodology
- **visual_insights**: Analysis of charts, graphs, and figures (requires poppler)
- **cost_tracking**: API usage and cost information

## Sample Output Structure

```json
{
  "filename": "geomorphology.pdf",
  "analyzed_at": "2025-12-31T16:55:46",
  "metadata": {
    "title": "Paper Title",
    "authors": ["Author 1", "Author 2"],
    "abstract": "...",
    "doi": "10.1234/example",
    "publication_year": "2024"
  },
  "text_analysis": {
    "synthesis": "Overall summary...",
    "key_findings": ["Finding 1", "Finding 2"],
    "methodology": "Research approach...",
    "sections": {...}
  },
  "visual_insights": {
    "summary": "Overview of visual data...",
    "figures": [...]
  },
  "cost_tracking": {
    "total_cost": 0.045,
    "input_tokens": 15000,
    "output_tokens": 2000
  }
}
```

## Troubleshooting

### "Claude API key not found!"
- Ensure `.env` file exists in project root
- Verify `CLAUDE_API_KEY` is set correctly
- No spaces around the `=` sign

### "Visual insights are null"
- Install poppler (see Prerequisites)
- Ensure poppler's `bin` folder is in PATH
- Restart terminal/IDE after installation
- Test with: `pdftoppm -v`

### "PDF file not found"
- Use absolute paths or paths relative to project root
- Ensure PDF is in `research_papers/` folder
- Check file path uses forward slashes or escaped backslashes

### Import errors
- Install all required packages: `pip install anthropic python-dotenv PyPDF2 pdf2image Pillow`
- Ensure Python 3.8+ is installed

## API Costs

The analyzer uses Claude Sonnet 4.5. Typical costs per paper:
- Short papers (10-20 pages): $0.02 - $0.05
- Medium papers (20-40 pages): $0.05 - $0.15
- Long papers (40+ pages): $0.15 - $0.30

Costs include both text and image analysis. All costs are tracked in the output JSON.

## Notes

- First run will show the location of the loaded `.env` file
- Image extraction requires poppler for pdf2image to work
- The analyzer gracefully continues with text-only analysis if poppler is missing
- Maximum 5 images are extracted per paper to control API costs
- Results are saved with timestamps to prevent overwriting
