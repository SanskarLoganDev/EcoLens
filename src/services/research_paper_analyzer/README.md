# Research Paper Analyzer

This service provides two completely independent features for working with scientific research papers. They share the same PDF files as input but do entirely different things and have no dependency on each other.

---

## The Two Features at a Glance

| | Feature 1: Summarizer | Feature 2: RAG Q&A |
|---|---|---|
| **What it does** | Reads an entire paper and produces a structured JSON report | Lets you ask free-form questions across all your papers |
| **Input** | One PDF at a time | Any question in plain English |
| **Output** | JSON file (findings, methodology, chart analyses, cost) | Conversational answer with citations to exact pages |
| **AI used** | Claude (text + vision) | Voyage AI (embeddings) + Claude (answer synthesis) |
| **When to use** | First time you add a paper — get the full picture | Ongoing — query across your entire paper library |
| **Stores data in** | `results/*.json` | `rag/chroma_store/` (ChromaDB vector database) |
| **Cost per run** | $0.05–$0.30 per paper | ~$0.015–$0.020 per question |

---

## Project Structure

```
research_paper_analyzer/
│
├── analyze_papers.py          ← Summarizer: main orchestrator
├── pdf_processor.py           ← Shared: PDF text + image extraction (PyPDF2 + pdf2image)
├── summarizer.py              ← Summarizer: section-by-section Claude text analysis
├── vision_analyzer.py         ← Summarizer: Claude Vision chart/figure analysis
├── client.py                  ← Shared: Claude API wrapper (text + vision, cost tracking)
├── prompts.py                 ← Shared: prompt templates for both Claude text and vision calls
│
├── rag/                       ← RAG Q&A feature (entirely separate from summarizer)
│   ├── __init__.py
│   ├── chunker.py             ← splits page text into overlapping 400-word chunks
│   ├── indexer.py             ← PDF → chunks → Voyage embeddings → ChromaDB
│   ├── retriever.py           ← question → embed → search → Claude answer
│   └── chroma_store/          ← ChromaDB vector database (auto-created, persists on disk)
│       └── chroma.sqlite3
│
├── research_papers/           ← Put your PDFs here (used by both features)
│   ├── climate_change.pdf
│   ├── geomorphology.pdf
│   └── ocean_acidification.pdf
│
├── results/                   ← Summarizer JSON reports (auto-created)
│   └── paper_analysis_*.json
│
└── README.md                  ← This file
```

---

## Setup

### Prerequisites

- Python 3.8+
- `CLAUDE_API_KEY` in `.env` (for both features)
- `VOYAGE_API_KEY` in `.env` (for the RAG feature only)

### API Keys

Your `.env` file in the project root must contain:

```
CLAUDE_API_KEY="your-claude-key-here"
VOYAGE_API_KEY="your-voyage-key-here"
```

Get keys from:
- Claude: https://console.anthropic.com/
- Voyage: https://dashboard.voyageai.com/

### Install dependencies

```bash
pip install -r requirements.txt
```

Key packages used by this service:

| Package | Used by |
|---|---|
| `anthropic` | Both features (Claude API) |
| `voyageai` | RAG only (Voyage embeddings) |
| `chromadb` | RAG only (vector database) |
| `PyPDF2` | Both features (PDF text extraction) |
| `pdf2image` + `Pillow` | Summarizer only (chart image extraction) |
| `python-dotenv` | Both features |

### System dependency: Poppler (Summarizer only, for image extraction)

`pdf2image` requires Poppler to convert PDF pages into images. Without it, the summarizer runs in text-only mode — no chart analysis.

**Windows:**
1. Download from: https://github.com/oschwartz10612/poppler-windows/releases/
2. Extract to `C:\Program Files\poppler-XX.XX.X`
3. Add `C:\Program Files\poppler-XX.XX.X\Library\bin` to your system PATH
4. Restart VS Code
5. Test: run `pdftoppm -v` in a terminal — if you see a version number, it works

**macOS:** `brew install poppler`

**Ubuntu/Debian:** `sudo apt install poppler-utils`

---

---

# Feature 1 — Paper Summarizer

## What It Does

Reads an entire PDF research paper from cover to cover and produces a structured JSON report containing:

- **Metadata** — title, authors, DOI, publication venue, abstract, keywords (extracted from the first page using Claude)
- **Section summaries** — the paper is split into 5-page chunks; Claude summarises each chunk separately
- **Synthesis** — all section summaries are sent to Claude again for a final integrated report containing: executive summary, main findings with confidence levels, methodology quality assessment, evidence strength, key uncertainties, policy implications, and internal contradictions
- **Visual insights** — if Poppler is installed, each page is converted to an image and Claude Vision analyses any charts, graphs, or figures it finds
- **API cost tracking** — exact token counts and dollar cost for every API call

## How It Works (Pipeline)

```
PDF file
   │
   ▼
pdf_processor.py     extracts text page-by-page (PyPDF2)
                     converts pages to images (pdf2image, optional)
   │
   ▼
summarizer.py        Step 1: extract metadata from page 1 (1 Claude call)
                     Step 2: summarise each 5-page section (N Claude calls)
                     Step 3: synthesise all sections into final report (1 Claude call)
   │
   ▼  (if images extracted)
vision_analyzer.py   sends each chart image to Claude Vision with analysis prompt
                     aggregates findings into visual_insights dict
   │
   ▼
analyze_papers.py    merges text analysis + visual insights
                     saves timestamped JSON to results/
```

## Running the Summarizer

### VS Code (recommended)

Use the F5 launch configurations — press `F5` and select from the dropdown:

| Config name | What it does |
|---|---|
| (no dedicated launch config — use terminal) | Run from terminal as shown below |

### Terminal commands (from project root)

```bash
# Analyze a paper WITH image/chart analysis (requires Poppler)
python src/services/research_paper_analyzer/analyze_papers.py \
    src/services/research_paper_analyzer/research_papers/ocean_acidification.pdf

# Analyze a paper WITHOUT image analysis (faster, no Poppler needed)
python src/services/research_paper_analyzer/analyze_papers.py \
    src/services/research_paper_analyzer/research_papers/ocean_acidification.pdf --no-images

# All three included papers
python src/services/research_paper_analyzer/analyze_papers.py \
    src/services/research_paper_analyzer/research_papers/climate_change.pdf --no-images

python src/services/research_paper_analyzer/analyze_papers.py \
    src/services/research_paper_analyzer/research_papers/geomorphology.pdf --no-images
```

### Output

Results are saved to `src/services/research_paper_analyzer/results/` with timestamped filenames:

```
paper_analysis_ocean_acidification_2025-12-31_17-44-05.json
```

The JSON structure:

```json
{
  "file_info":    { "filename": "...", "pages": 20, "analyzed_date": "..." },
  "metadata":     { "title": "...", "authors": [...], "doi": "...", "abstract": "..." },
  "text_analysis": {
    "synthesis": {
      "executive_summary": "2-3 sentence overview",
      "main_findings":     [ { "finding": "...", "confidence": "high", "evidence": "..." } ],
      "methodology_quality": "rigorous / adequate / limited",
      "evidence_strength":   "high / medium / low",
      "key_uncertainties":   [ "..." ],
      "policy_implications": [ "..." ],
      "contradictions":      [ "..." ]
    },
    "section_count": 4
  },
  "visual_insights": { "total_images_analyzed": 4, "key_visual_findings": [...] },
  "api_cost":     { "total_calls": 10, "text_calls": 6, "vision_calls": 4, "total_cost_usd": 0.116 }
}
```

## Cost Estimates (Summarizer)

All costs use Claude Sonnet 4 pricing: $3.00 per million input tokens, $15.00 per million output tokens.

| Paper length | Without images | With images |
|---|---|---|
| Short (10–20 pages) | $0.05–$0.10 | $0.08–$0.15 |
| Medium (20–40 pages) | $0.10–$0.20 | $0.15–$0.30 |

The exact cost for every run is printed in the terminal and stored in `api_cost` in the output JSON.

## Testing Individual Summarizer Components

Each module runs standalone for isolated testing (no other modules needed):

```bash
# Test PDF text extraction only — no API key required
python src/services/research_paper_analyzer/pdf_processor.py \
    src/services/research_paper_analyzer/research_papers/ocean_acidification.pdf

# Test Claude text summarisation with a short sample (~$0.01)
python src/services/research_paper_analyzer/summarizer.py

# Test Claude API connection (text + vision) (~$0.001)
python src/services/research_paper_analyzer/client.py

# Preview all prompt templates (no API call)
python src/services/research_paper_analyzer/prompts.py
```

---

---

# Feature 2 — RAG Q&A (Retrieval-Augmented Generation)

## What It Does

Lets you ask free-form questions about your research papers in natural language and receive answers grounded in the actual text of the papers, with citations to the specific page each claim came from.

**Example questions:**
- *"What specific pH values does the ocean acidification paper report for pre-industrial vs current oceans?"*
- *"How does climate change affect water availability in India and what numbers are cited?"*
- *"What dating method was used in the Pyrenees glacier study and how accurate is it?"*
- *"Do any of my papers discuss policy recommendations? What do they suggest?"*

## Why Two Different AI Services Are Used

This is a common point of confusion. The RAG pipeline has two completely separate jobs:

**Job 1 — Finding relevant text (Voyage AI, very cheap)**

Your question is converted into a vector of numbers by Voyage AI. ChromaDB then searches its index to find the 6 stored text chunks whose vectors are most mathematically similar to your question's vector. This is pure similarity search — no language model, no generation, no "thinking." The result is 6 raw passages of actual text extracted from your PDFs.

**Job 2 — Writing a readable answer (Claude, small cost)**

The 6 raw passages are handed to Claude alongside your question. Claude's only job here is to act as a text synthesiser — it reads the passages, identifies which are relevant, combines the information coherently, and writes a clear cited answer. Claude does not look anything up or use its own training knowledge about climate change. It only reads and summarises what the retriever already found.

Without Job 2 you would receive 6 disconnected paragraphs of raw scientific text dumped on screen, which is hard to read. Without Job 1 you would have to send the entire corpus of PDFs to Claude on every question, which would cost 100× more and hit context limits.

This two-stage design is why RAG is so effective: Voyage handles the cheap search, Claude handles the cheap synthesis.

## How It Works (Pipeline)

### Indexing (done once per paper)

```
PDF file
   │
   ▼
pdf_processor.py     extracts text page-by-page (same as summarizer, text only)
   │
   ▼
rag/chunker.py       splits each page into overlapping 400-word windows
                     (75-word overlap between consecutive chunks)
                     tags each chunk with: source_file, page_number, chunk_id
   │
   ▼
Voyage AI API        converts each chunk to a 1024-float vector
(voyage-3.5-lite)    using input_type="document"
   │
   ▼
ChromaDB             stores (chunk text + vector + metadata) permanently on disk
(rag/chroma_store/)  survives restarts — only needs to run once per paper
```

### Answering a question (done on every chat message)

```
User question (string)
   │
   ▼
Voyage AI API        converts question to vector using input_type="query"
(voyage-3.5-lite)    note: "query" mode is different from "document" mode —
                     Voyage optimises each direction separately for better retrieval
   │
   ▼
ChromaDB             finds the 6 stored chunks whose vectors are closest
                     to the question vector (cosine similarity search)
                     returns: chunk text + source_file + page_number
   │
   ▼
rag/retriever.py     builds a Claude prompt:
                       "Answer using ONLY these passages. Cite [1], [2], etc."
                       + the 6 retrieved passages (with source labels)
                       + conversation history (for follow-up questions)
   │
   ▼
Claude API           reads the passages, writes a cited answer
(claude-sonnet-4)    does NOT use its own knowledge — only what is in the passages
   │
   ▼
Return to caller     { "answer": "...", "sources": [...], "passages_used": 4 }
```

## Running the RAG Feature

### Step 1 — Index your papers (one time only)

**VS Code Task:**
```
Terminal > Run Task > 📥 RAG: Index ALL papers
```

**Terminal command:**
```bash
# Index all papers in research_papers/
python src/services/research_paper_analyzer/rag/indexer.py --all

# Index a single paper
python src/services/research_paper_analyzer/rag/indexer.py \
    src/services/research_paper_analyzer/research_papers/ocean_acidification.pdf

# Check what is already indexed
python src/services/research_paper_analyzer/rag/indexer.py --list

# Remove a paper from the index
python src/services/research_paper_analyzer/rag/indexer.py --delete ocean_acidification.pdf
```

The indexer is safe to run multiple times — it skips chunks already in the database. Only new chunks are embedded and stored.

### Step 2 — Start the RAG API server

**VS Code Task:**
```
Terminal > Run Task > 🔬 Start RAG API (:8001)
```

**VS Code F5 launch:**
Press `F5` → select **"🔬 RAG API (uvicorn :8001)"**

**Terminal command:**
```bash
uvicorn src.api.rag_api:app --reload --port 8001
```

You should see:
```
INFO: Uvicorn running on http://127.0.0.1:8001
INFO: Application startup complete.
```

### Step 3 — Open the chat UI

**VS Code Task:**
```
Terminal > Run Task > 🌐 Open Research Chat UI
```

Or double-click `ui/research/chat.html` in Windows Explorer.

The left sidebar shows all indexed papers. Papers in `research_papers/` that are not yet indexed appear as **"+ Index"** — click the badge to index them directly from the UI without using the terminal.

### Step 4 — Ask questions

Type a question in the chat box and press `Enter` (or `Shift+Enter` for a new line). The answer appears with source badges showing which paper and page each claim came from.

Conversation history is maintained within the session — follow-up questions like *"Can you expand on point 3?"* work naturally.

### Optional: Terminal Q&A (no UI, good for quick testing)

**VS Code F5 launch:**
Press `F5` → select **"💬 RAG: Terminal Q&A (retriever test)"**

**Terminal command:**
```bash
python src/services/research_paper_analyzer/rag/retriever.py
```

This starts an interactive prompt loop in the terminal. Type questions, get answers with page citations. Type `papers` to list indexed papers. Type `quit` to exit.

## Adding New Papers Later

1. Drop the new PDF into `research_papers/`
2. Run the indexer on it:
   ```bash
   python src/services/research_paper_analyzer/rag/indexer.py \
       src/services/research_paper_analyzer/research_papers/new_paper.pdf
   ```
   Or click **"+ Index"** next to it in the chat UI sidebar.

That's it. The new paper is immediately searchable alongside existing ones.

## RAG API Endpoints

When the server is running on port 8001, these endpoints are available (also browseable at `http://localhost:8001/docs`):

| Method | URL | What it does |
|---|---|---|
| `GET` | `/api/rag/health` | Confirms server is running |
| `GET` | `/api/rag/papers` | Lists all indexed papers with chunk counts |
| `GET` | `/api/rag/available` | Lists all PDFs in research_papers/, indexed or not |
| `POST` | `/api/rag/index` | Indexes a named PDF: `{"filename": "ocean_acidification.pdf"}` |
| `POST` | `/api/rag/chat` | Answers a question: `{"question": "...", "history": [...]}` |
| `DELETE` | `/api/rag/papers/{filename}` | Removes a paper from the index |

## Testing Individual RAG Components

```bash
# Test chunker only — no API key required, instant
python src/services/research_paper_analyzer/rag/chunker.py
# (defaults to ocean_acidification.pdf, pass a path to test another)

# Test chunker on a specific paper
python src/services/research_paper_analyzer/rag/chunker.py \
    src/services/research_paper_analyzer/research_papers/geomorphology.pdf
```

**VS Code F5 launch for chunker:**
Press `F5` → select **"✂️  RAG: Test chunker"**

## Cost Estimates (RAG)

### Indexing (paid once per paper, then free forever)

| Model | Rate | Cost per paper (~113 chunks total across all 3) |
|---|---|---|
| Voyage `voyage-3.5-lite` | $0.02 per million tokens | ~$0.001 total for all 3 papers |
| Free tier | 200M tokens included | All 3 papers fit easily in free tier |

### Answering questions (paid per question)

| Component | Cost per question | Notes |
|---|---|---|
| Voyage embedding (question) | ~$0.000001 | ~20 tokens |
| ChromaDB search | $0.00 | Local, no API |
| Claude answer synthesis | ~$0.015–$0.020 | ~3,200 input + ~400 output tokens |
| **Total** | **~$0.015–$0.020** | ~1.5–2 cents |

### Why Claude is called on every question

The vector search returns raw text chunks from your papers — exact passages from the PDF. Claude's job is purely to synthesise those passages into a readable, cited answer. It does not use its own knowledge about climate change. If you asked 100 questions in a session, you would spend roughly $1.50–$2.00 on Claude calls. The Voyage embedding cost for those same 100 questions would be $0.0001 — effectively zero.

### Voyage AI free tier and rate limits

Without a payment method: 3 RPM / 10K TPM (too slow for indexing multiple papers in one go).
After adding a payment method (no charge until you exceed 200M free tokens): 2,000 RPM / 16M TPM.

Your three papers use approximately 44,000 tokens total — 0.022% of the 200M free tier. You will not be charged for Voyage usage in normal use of this project.

---

---

## Troubleshooting

### Summarizer issues

**"Claude API key not found"**
- Confirm `.env` exists in the project root (`EcoLens/.env`), not inside `src/`
- No spaces around `=`: `CLAUDE_API_KEY="key"` ✅ not `CLAUDE_API_KEY = "key"` ❌

**"Visual insights are null" / image extraction fails**
- Poppler is not installed or not in PATH
- Test with: `pdftoppm -v` in a terminal
- See the Poppler installation steps in the Setup section above

**"PDF file not found"**
- Always run commands from the project root (`EcoLens/`), not from inside `src/`

### RAG issues

**"VOYAGE_API_KEY not found"**
- Add `VOYAGE_API_KEY="your-key"` to `.env`
- Get a free key at https://dashboard.voyageai.com/

**"ChromaDB store not found"**
- You have not run the indexer yet
- Run: `python src/services/research_paper_analyzer/rag/indexer.py --all`

**Indexer fails with 429 rate limit error**
- You have not added a payment method to your Voyage account
- Go to https://dashboard.voyageai.com/organization/billing/payment-methods
- Adding a card unlocks Tier 1 rate limits (2,000 RPM / 16M TPM) at no cost
- Your 200M free tokens still apply after adding the card

**RAG gives answers unrelated to the question**
- The `MAX_DISTANCE` threshold (0.65) may need tuning for your papers
- Try rephrasing the question with more specific terminology from the papers
- Check that the relevant paper is actually indexed: run `--list`

**Chat UI shows red dot / "Offline"**
- The RAG API server is not running
- Start it: `uvicorn src.api.rag_api:app --reload --port 8001`
- Confirm it's running by visiting `http://localhost:8001/api/rag/health` in your browser

---

## Key Design Decision: Why Two Separate Features?

The summarizer and the RAG system intentionally do not share output. The summarizer produces structured JSON reports designed to be read by a human who wants a holistic understanding of one paper. The RAG system indexes the raw PDF text directly — not the summaries — because summaries compress and discard most of the specific numbers, sentences, and details that make RAG answers accurate.

If the RAG system searched over summary JSONs instead of raw text, it would fail on specific questions like *"what exact pH values does the paper report?"* because the summarizer condenses those into paraphrased findings. By indexing the original PDF text, the RAG system can retrieve and cite the exact sentence from the exact page where a number or claim appears.

Both features serve different purposes and are better for it.
