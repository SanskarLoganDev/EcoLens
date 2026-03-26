# EcoLens

An AI-powered environmental intelligence platform with three features: carbon footprint analysis from transaction data, research paper summarization and Q&A, and satellite-based environmental change detection.

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI | Anthropic Claude (text + vision), Voyage AI (embeddings) |
| Backend APIs | FastAPI + Uvicorn |
| Vector DB | ChromaDB |
| Satellite imagery | NASA GIBS (free, no API key) |
| Data | pandas, Pydantic, PyPDF2, Pillow |
| Frontend | Vanilla HTML/CSS/JS |

---

## Setup (all features)

**1. Create and activate a virtual environment** (from project root):
```bash
python -m venv .venv
.venv\Scripts\activate
```

**2. Install all dependencies:**
```bash
pip install -r requirements.txt
```

**3. Create a `.env` file in the project root:**
```
CLAUDE_API_KEY=your_claude_api_key_here
VOYAGE_API_KEY=your_voyage_api_key_here
```

`CLAUDE_API_KEY` is required for all three features. `VOYAGE_API_KEY` is only needed for the RAG Q&A feature inside Feature 2.

---

---

# Feature 1 — Carbon Footprint Analyzer

Analyzes a CSV of financial transactions, categorizes each one into an emission category using Claude, calculates CO2 emissions with a deterministic math engine, benchmarks against Paris Agreement targets, and generates 5 personalized coaching recommendations.

**API cost per run:** ~$0.03 (2 Claude calls — categorization + coaching)

## What it does

- Reads a CSV with `date`, `description`, `amount` columns
- Claude categorizes each merchant into one of 9 emission categories (air travel, ground transport, food, groceries, electricity, gas, electronics, clothing, general goods)
- Deterministic CO2 math engine applies IPCC-based factors per category
- Projects annual emissions and compares against US average (16,000 kg/yr), global average (4,000 kg/yr), and Paris target (2,300 kg/yr)
- Claude generates 5 personalized, actionable coaching recommendations with estimated savings
- Results auto-saved to `src/services/carbon/results/`

## Run via VS Code Tasks

```
Terminal > Run Task > 🌿 Start Carbon API (:8000)
Terminal > Run Task > 🌐 Open Carbon UI
```

Then upload a CSV in the browser and click **Analyze with Claude AI**.

## Run via CLI

```bash
# Uses the built-in sample CSV (28 transactions)
python src/services/carbon/analyzer.py

# With your own CSV
python src/services/carbon/analyzer.py path/to/transactions.csv
```

## Run via F5 (VS Code)

Press `F5` → select **🌿 Carbon API (uvicorn :8000)**, then open `ui/carbon/index.html`.

## API Endpoints (port 8000)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/carbon/sample` | Returns built-in sample CSV |
| POST | `/api/carbon/analyze` | Upload CSV → full analysis |
| GET | `/api/carbon/results` | List all past saved results |
| GET | `/api/carbon/results/{id}` | Retrieve a specific past result |

## CSV Format

```csv
date,description,amount
2025-01-15,Delta Airlines,420.00
2025-01-16,Starbucks,6.50
```

---

---

# Feature 2 — Research Paper Analyzer

Two independent sub-features for working with scientific PDFs. Both read from `src/services/research_paper_analyzer/research_papers/`.

## Sub-feature A — Paper Summarizer

Reads an entire PDF and produces a structured JSON report with metadata, executive summary, key findings with confidence scores, methodology, policy implications, uncertainties, and optional chart/figure analysis via Claude Vision.

**API cost:** $0.05–$0.30 per paper (varies with paper length and whether image analysis is enabled)

### Run via VS Code Tasks

```
Terminal > Run Task > 🔬 Start RAG API (:8001)
Terminal > Run Task > 🌐 Open Research UI (landing page)
```

Navigate to the **Summarizer** card in the UI.

### Run via CLI

```bash
# Summarize a paper (text only)
python src/services/research_paper_analyzer/analyze_papers.py src/services/research_paper_analyzer/research_papers/ocean_acidification.pdf

# With chart/figure analysis (requires Poppler)
python src/services/research_paper_analyzer/analyze_papers.py src/services/research_paper_analyzer/research_papers/ocean_acidification.pdf --analyze-images
```

## Sub-feature B — RAG Q&A

Indexes PDFs into a ChromaDB vector database using Voyage AI embeddings, then answers free-form questions in plain English with citations to exact page numbers and source papers. Requires `VOYAGE_API_KEY`.

**API cost:** ~$0.015–$0.020 per question (Voyage embedding ~$0.000001 + Claude synthesis ~$0.015)

### Setup — index papers first

```
Terminal > Run Task > 📥 RAG: Index ALL papers
```

Or CLI:
```bash
python src/services/research_paper_analyzer/rag/indexer.py --all
```

### Run via VS Code Tasks

```
Terminal > Run Task > 🔬 Start RAG API (:8001)
Terminal > Run Task > 🌐 Open Research UI (landing page)
```

Navigate to the **Research Assistant (Q&A)** card in the UI and ask questions.

### Check what is indexed

```
Terminal > Run Task > 📋 RAG: List indexed papers
```

Or CLI:
```bash
python src/services/research_paper_analyzer/rag/indexer.py --list
```

## API Endpoints (port 8001)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/rag/health` | Liveness check |
| GET | `/api/rag/papers` | List indexed papers |
| GET | `/api/rag/available` | List all PDFs with indexed status |
| POST | `/api/rag/index` | Index a PDF `{"filename": "paper.pdf"}` |
| POST | `/api/rag/chat` | Ask a question `{"question": "...", "history": [...]}` |
| DELETE | `/api/rag/papers/{filename}` | Remove a paper from the index |
| GET | `/api/summarizer/available` | List PDFs with summary status |
| GET | `/api/summarizer/results` | List all summary JSON results |
| GET | `/api/summarizer/results/{id}` | Retrieve a specific summary |
| POST | `/api/summarizer/run` | Run summarizer on a PDF |

---

---

# Feature 3 — Satellite Environmental Monitor

Fetches before/after satellite imagery from NASA GIBS (free, no API key needed), sends both images to Claude Vision for land cover analysis, compares the two analyses to detect changes, quantifies results as hard metrics (area changed in km², carbon emissions in tons, severity score), and generates reports in JSON, Markdown, and CSV.

**API cost per analysis:** ~$0.02–$0.05 (2 Claude Vision calls + 1 text call)

## What it does

- Downloads satellite images from NASA GIBS for two dates at a given location
- Supports 4 satellite layers: VIIRS (375m, daily), MODIS Terra (250m, daily), Sentinel-2 (30m, 5-day), Landsat 8/9 (30m, 16-day)
- Claude Vision reads land cover percentages (forest, urban, water, cleared) from each image
- Compares before/after to detect change type, severity (1–10), and new/lost features
- Calculates physical metrics: area monitored (km²), forest lost (km²), carbon emissions (tons CO2), expansion rate (km²/day)
- Auto-retries ±7 days if requested date has cloud cover or no data
- Preset regions include Amazon, Dubai, Las Vegas, Delhi NCR, Greenland, California

## Run via VS Code Tasks

```
Terminal > Run Task > 🛰️ Start Satellite API (:8002)
Terminal > Run Task > 🌐 Open Satellite UI
```

1. Click a **preset region card** (☀️ = low cloud risk, ⛅ = medium, ☁️ = high)
2. Select a **satellite layer** (VIIRS recommended for daily availability)
3. Click **Run Analysis** — a live progress log appears, ~30–90 seconds
4. Before/after images appear side by side with land cover breakdown, change summary, and metrics

## Run via CLI

```bash
# Preset region (uses recommended dates and layer)
python src/services/satellite/analyzer.py dubai
python src/services/satellite/analyzer.py las_vegas
python src/services/satellite/analyzer.py arctic_greenland

# Custom coordinates (single line)
python src/services/satellite/analyzer.py --lat 25.2048 --lon 55.2708 --before 2018-02-01 --after 2024-02-01 --name "Dubai UAE" --type urban_sprawl

# With a specific satellite layer
python src/services/satellite/analyzer.py --lat 28.6139 --lon 77.2090 --before 2019-02-01 --after 2024-02-01 --name "Delhi NCR" --type urban_sprawl --layer sentinel

# List all preset regions
python src/services/satellite/analyzer.py --list
```

## Run via F5 (VS Code)

Press `F5` → select **🛰️ Satellite API (uvicorn :8002)**, then open `ui/satellite/index.html`.

## CLI Options

| Flag | Values | Default | Description |
|---|---|---|---|
| `--layer` | `viirs_day`, `modis_terra`, `sentinel`, `landsat` | `viirs_day` | Satellite imagery source |
| `--type` | `general`, `deforestation`, `urban_sprawl`, `ice_melt` | `general` | Focuses Claude's analysis |
| `--before` | `YYYY-MM-DD` | — | Before date |
| `--after` | `YYYY-MM-DD` | — | After date |
| `--name` | string | coordinates | Location label used in filenames |
| `--list` | — | — | Print all preset regions and exit |

## API Endpoints (port 8002)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/satellite/health` | Liveness check |
| GET | `/api/satellite/regions` | All preset regions with cloud risk badges |
| GET | `/api/satellite/layers` | Available satellite layers with metadata |
| GET | `/api/satellite/results` | List past analyses, newest first |
| GET | `/api/satellite/results/{id}` | Full JSON for a specific result |
| GET | `/api/satellite/image?path=...` | Serve a downloaded PNG as base64 |
| POST | `/api/satellite/analyze` | Start analysis (returns `job_id` immediately) |
| GET | `/api/satellite/status/{job_id}` | Poll job status and live progress log |

## Preset Regions Reference

| Key | Location | Type | Cloud risk | Best dates |
|---|---|---|---|---|
| `dubai` | Dubai, UAE | Urban sprawl | ☀️ Low | Any month |
| `las_vegas` | Nevada, USA | Urban sprawl | ☀️ Low | Any month |
| `arctic_greenland` | Greenland | Ice melt | ☀️ Low | Jul–Aug |
| `california_forests` | N. California | Fire damage | ☀️ Low | Sep–Oct |
| `delhi_ncr` | India | Urban sprawl | ⛅ Medium | Jan–Feb (avoid Nov: smog) |
| `congo_basin` | DRC | Deforestation | ⛅ Medium | Jun–Aug |
| `amazon_basin` | Brazil | Deforestation | ☁️ High | Aug–Sep (dry season only) |
| `amazon_rondonia` | Rondônia, Brazil | Deforestation | ☁️ High | Aug–Sep |

---

---

# VS Code Quick Reference

## All Tasks (`Terminal > Run Task`)

| Task | What it does |
|---|---|
| 🌿 Start Carbon API (:8000) | Starts FastAPI for Feature 1 |
| 🔬 Start RAG API (:8001) | Starts FastAPI for Feature 2 |
| 🛰️ Start Satellite API (:8002) | Starts FastAPI for Feature 3 |
| 🌐 Open Carbon UI | Opens `ui/carbon/index.html` |
| 🌐 Open Research UI (landing page) | Opens `ui/research/index.html` |
| 🌐 Open Satellite UI | Opens `ui/satellite/index.html` |
| 📥 RAG: Index ALL papers | Indexes all PDFs in `research_papers/` |
| 📋 RAG: List indexed papers | Shows what is currently in ChromaDB |
| 📦 Install / upgrade requirements | Runs `pip install -r requirements.txt` |
| 📦 Install RAG dependencies (chromadb) | Installs ChromaDB separately if needed |

## F5 Launch Configs

| Config | What it starts |
|---|---|
| 🌿 Carbon API (uvicorn :8000) | Feature 1 backend |
| 🔬 RAG API (uvicorn :8001) | Feature 2 backend |
| 🛰️ Satellite API (uvicorn :8002) | Feature 3 backend |
| 📥 RAG: Index all papers | Indexing pipeline |
| 📋 RAG: List indexed papers | Index status |
| 💬 RAG: Terminal Q&A | CLI Q&A test |
| 🧪 Carbon: Run analyzer.py | CLI pipeline with sample data |

---

## Project Structure

```
EcoLens/
├── .env                          CLAUDE_API_KEY, VOYAGE_API_KEY, NASA_API_KEY
├── requirements.txt
├── .vscode/
│   ├── launch.json               F5 run configs for all three features
│   ├── tasks.json                Build tasks (start APIs, open UIs, pip install)
│   └── settings.json
│
├── src/
│   ├── api/
│   │   ├── carbon_api.py         FastAPI :8000 — Feature 1
│   │   ├── rag_api.py            FastAPI :8001 — Feature 2
│   │   └── satellite_api.py      FastAPI :8002 — Feature 3
│   │
│   └── services/
│       ├── carbon/               Feature 1 — transaction parsing, CO2 math, Claude coaching
│       ├── research_paper_analyzer/  Feature 2 — summarizer + RAG + ChromaDB
│       └── satellite/            Feature 3 — GIBS fetcher, Claude Vision, change detection
│
└── ui/
    ├── carbon/index.html         Feature 1 UI
    ├── research/                 Feature 2 UI (landing page + chat + summarizer)
    └── satellite/index.html      Feature 3 UI
```
