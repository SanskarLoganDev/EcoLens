# Carbon Footprint Analyzer

An AI-powered carbon footprint analysis tool that categorizes financial transactions and provides personalized recommendations for reducing carbon emissions.

It can be run in two ways:
- **CLI** — run `analyzer.py` directly from the terminal for a pure Python pipeline
- **Web UI** — start the FastAPI backend and open `ui/carbon/index.html` in a browser for a full interactive interface

---

## Overview

The tool analyzes spending patterns from CSV transaction files, calculates associated carbon emissions, and provides actionable coaching recommendations using Claude AI.

### Key Features

- 📊 **Transaction Categorization** — Claude AI reads merchant names and assigns each transaction to one of 9 emission categories
- 🌍 **Emission Calculation** — deterministic math engine applies CO2 factors per category (no AI involved)
- 📈 **Benchmarking** — compares your annual projection against US average, global average, and the Paris Agreement target
- 💡 **AI Coaching** — Claude generates 5 personalized, actionable recommendations with kg savings estimates and difficulty ratings
- 🌐 **Web UI** — browser-based interface connected to a FastAPI backend
- 📁 **Saved Reports** — every analysis is auto-saved as a timestamped JSON file

---

## Project Structure

```
EcoLens/
│
├── src/
│   ├── api/
│   │   └── carbon_api.py              # FastAPI backend — 4 HTTP endpoints
│   │
│   └── services/carbon/
│       ├── README.md                  # This file
│       ├── analyzer.py                # Main orchestrator — runs the full pipeline
│       ├── parser.py                  # CSV reader and validator (pandas + Pydantic)
│       ├── calculator.py              # CO2 math engine (no AI)
│       ├── client.py                  # Claude API wrapper with cost tracking
│       ├── prompts.py                 # Prompt templates for categorization and coaching
│       ├── emission_factors.json      # CO2 factors database and global benchmarks
│       ├── samples/
│       │   └── sample_transactions_5.csv   # 28-transaction sample (May 2025)
│       └── results/                   # Auto-created; stores timestamped JSON reports
│           └── carbon_analysis_*.json
│
├── ui/
│   └── carbon/
│       └── index.html                 # Browser UI — connects to carbon_api.py
│
└── .vscode/
    ├── launch.json                    # F5 run configs for API and individual modules
    ├── tasks.json                     # Build tasks (start server, open UI, pip install)
    └── settings.json                  # Python interpreter and path config
```

### Module Responsibilities

| File | Role | Uses AI? |
|------|------|----------|
| `carbon_api.py` | HTTP front door — receives CSV, calls analyzer, returns JSON | No |
| `analyzer.py` | Orchestrator — calls all other modules in order | No (coordinates) |
| `parser.py` | Reads CSV, validates columns, builds Transaction objects | No |
| `prompts.py` | Builds the exact text instructions sent to Claude | No |
| `client.py` | Sends prompts to Claude API, tracks token costs | Yes (Claude) |
| `calculator.py` | Applies emission formulas from JSON database | No |
| `emission_factors.json` | Stores CO2 factors and global benchmarks | — |

---

## Setup

### Prerequisites

- Python 3.8+
- Anthropic API key — get one from https://console.anthropic.com/

### Installation

**1. Install all dependencies** (from project root):

```bash
pip install -r requirements.txt
```

Required packages:
- `anthropic` — Claude API client
- `pandas` — CSV data processing
- `pydantic` — data validation
- `python-dotenv` — reads the `.env` file
- `fastapi` — web API framework
- `uvicorn[standard]` — ASGI server that runs FastAPI
- `python-multipart` — handles file uploads in FastAPI

**2. Set up your API key:**

Create a `.env` file in the project root (not inside `src/`):

```
CLAUDE_API_KEY="your-api-key-here"
```

---

## Running the Tool

### Option A — Web UI (recommended)

**Step 1:** Start the backend server from the project root:

```bash
uvicorn src.api.carbon_api:app --reload --port 8000
```

Or in VS Code: press `F5` and pick **"🌿 Carbon API (uvicorn)"**.

You should see:
```
INFO: Uvicorn running on http://127.0.0.1:8000
INFO: Application startup complete.
```

**Step 2:** Open the UI. In VS Code terminal:

```bash
start ui\carbon\index.html
```

Or just double-click `ui/carbon/index.html` in Windows Explorer.

**Step 3:** In the browser, click **"Load sample"** or upload your own CSV, then click **"Analyze with Claude AI"**.

The green dot in the UI header confirms the backend is connected. If it shows red, the server is not running.

**Step 4 (optional):** View the auto-generated API docs at:

```
http://localhost:8000/docs
```

This is a Swagger UI where you can test every endpoint directly without the browser UI.

---

### Option B — Command Line (no web server needed)

```bash
# From project root — uses the built-in sample CSV
python src/services/carbon/analyzer.py

# With your own CSV file
python src/services/carbon/analyzer.py path/to/your/transactions.csv
```

---

### CSV File Format

Your CSV must have exactly these three columns:

```csv
date,description,amount
2025-01-15,Delta Airlines,420.00
2025-01-16,Starbucks,6.50
2025-01-17,Whole Foods,85.30
```

| Column | Format | Notes |
|--------|--------|-------|
| `date` | YYYY-MM-DD or MM/DD/YYYY | Most formats accepted |
| `description` | Text | Merchant name from your bank statement |
| `amount` | Positive number | Dollar amount, no `$` sign needed |

---

## API Endpoints

When the backend is running, these endpoints are available:

| Method | URL | What it does |
|--------|-----|--------------|
| `GET` | `/api/health` | Confirms server is running |
| `GET` | `/api/carbon/sample` | Returns the sample CSV as plain text |
| `POST` | `/api/carbon/analyze` | Accepts a CSV upload, runs the full pipeline, returns JSON |
| `GET` | `/api/carbon/results` | Lists all past saved result files |
| `GET` | `/api/carbon/results/{id}` | Returns a specific past result by file stem ID |

---

## Analysis Pipeline (Step by Step)

When you upload a CSV and click Analyze, this is what happens in order:

```
1. carbon_api.py     receives the CSV file upload
2. carbon_api.py     writes it to a temp file on disk
3. analyzer.py       is called with the temp file path
4. parser.py         reads and validates every row → Transaction objects
5. prompts.py        builds the categorization instruction text
6. client.py         sends it to Claude → gets back JSON with categories
7. calculator.py     applies emission formulas to each categorized transaction
8. calculator.py     projects annual emissions and runs benchmark comparisons
9. prompts.py        builds the coaching instruction text
10. client.py        sends it to Claude → gets back 5 recommendations
11. analyzer.py      merges all results into one dictionary
12. analyzer.py      saves the result to results/carbon_analysis_*.json
13. carbon_api.py    returns the result as JSON to the browser
14. index.html       renders the charts, bars, and coaching cards
```

---

## Output

Every analysis generates a JSON report saved to `src/services/carbon/results/`:

```
carbon_analysis_sample_transactions_5_2025-05-31_14-30-45.json
```

The report contains:

```json
{
  "total_emissions_kg": 1247.5,
  "total_emissions_tons": 1.248,
  "breakdown": {
    "ground_transport": {
      "emissions_kg": 590.2,
      "percentage": 47.3,
      "count": 10,
      "total_spent": 596.75,
      "items": [...]
    }
  },
  "period_info": {
    "start_date": "2025-05-01",
    "end_date": "2025-05-31",
    "days": 31,
    "transaction_count": 28,
    "total_spent": 1804.80
  },
  "benchmarks": {
    "us_average_annual_kg": 16000,
    "global_average_annual_kg": 4000,
    "paris_target_annual_kg": 2300,
    "your_annual_projection_kg": 14673,
    "comparison": {
      "vs_us_average": 91.7,
      "vs_paris_target": 638.0
    }
  },
  "coaching": {
    "recommendations": [...],
    "overall_strategy": "...",
    "realistic_annual_target_kg": 9500
  },
  "api_cost": {
    "total_calls": 2,
    "total_input_tokens": 2841,
    "total_output_tokens": 1203,
    "input_cost_usd": 0.0085,
    "output_cost_usd": 0.018,
    "total_cost_usd": 0.0265
  }
}
```

---

## Emission Categories

The analyzer recognizes 9 categories:

| Category | Examples | How CO2 is calculated |
|----------|----------|----------------------|
| `air_travel` | Delta, United, Southwest | $300+ = international (1,600 kg), under $300 = domestic (800 kg) |
| `ground_transport` | Uber, Lyft, Shell, Chevron | Estimated miles from cost × 0.45 kg/mile |
| `food_restaurant` | Starbucks, Chipotle, Outback | Estimated meals from cost × 2.5 kg/meal |
| `groceries` | Whole Foods, Safeway, Costco | $1 = 0.10 kg CO2 |
| `electricity` | PG&E, Duke Energy | Estimated kWh from bill × 0.385 kg/kWh |
| `natural_gas` | SoCal Gas, National Gas | Estimated therms from bill × 5.3 kg/therm |
| `goods_electronics` | Apple, Best Buy | $1 = 0.15 kg CO2 |
| `goods_clothing` | Nordstrom, H&M, Gap | $1 = 0.20 kg CO2 |
| `goods_general` | Target, Walmart | $1 = 0.10 kg CO2 |

All factors are stored in `emission_factors.json` and can be edited to reflect your region or updated data.

---

## Cost Estimates

API pricing for Claude Sonnet 4 (verified March 2026 — source: https://platform.claude.com/docs/en/about-claude/pricing):

- **Input tokens:** $3.00 per million
- **Output tokens:** $15.00 per million

**Per full analysis (28 transactions):**

| Step | Approximate cost |
|------|-----------------|
| Categorization (Call 1) | ~$0.01 |
| Coaching (Call 2) | ~$0.02 |
| **Total** | **~$0.03** |

The exact cost for every run is printed in the terminal and included in the JSON report under `api_cost`.

---

## Testing Individual Components

Each module can be run directly to test it in isolation:

```bash
# Test CSV parsing only
python src/services/carbon/parser.py

# Test emission math only (no API needed)
python src/services/carbon/calculator.py

# Test Claude API connection (uses ~$0.001)
python src/services/carbon/client.py

# Preview the prompts that get sent to Claude
python src/services/carbon/prompts.py
```

---

## VS Code Integration

Three config files in `.vscode/` make development easier:

**`launch.json`** — press `F5` and pick from:
- `🌿 Carbon API (uvicorn)` — starts the web server with auto-reload
- `🧪 Run: analyzer.py (sample data)` — runs the CLI pipeline
- `🧪 Run: parser.py` — tests just the CSV parser
- `🧪 Run: calculator.py` — tests just the emission calculator
- `🧪 Run: client.py (API key test)` — tests the Claude connection

**`tasks.json`** — from Terminal → Run Task:
- `🌿 Start Carbon API` — starts uvicorn
- `🌐 Open Carbon UI in browser` — opens `ui/carbon/index.html`
- `📦 Install / upgrade requirements` — runs pip install
- `📦 Install FastAPI + uvicorn` — installs web dependencies only

---

## Configuration

### Emission Factors

Edit `emission_factors.json` to customize CO2 factors for your region or update with newer IPCC data. The structure is:

```json
{
  "categories": {
    "category_name": { "factor_name": value }
  },
  "benchmarks": {
    "us_average_annual_kg": 16000,
    "paris_target_annual_kg": 2300
  }
}
```

### API Settings

In `client.py`:
- `self.model` — Claude model string (default: `claude-sonnet-4-20250514`)
- `self.max_tokens` — max tokens Claude can generate per call (default: 4000)
- `INPUT_COST_PER_1M` / `OUTPUT_COST_PER_1M` — pricing constants for cost tracking

In `analyzer.py`:
- Categorization temperature: `0.3` (low = consistent, deterministic)
- Coaching temperature: `0.7` (higher = more creative suggestions)

---

## Troubleshooting

### "Claude API key not found"
- Confirm `.env` exists in the **project root** (`EcoLens/.env`), not inside `src/`
- Check there are no spaces around `=`: `CLAUDE_API_KEY="key"` ✅ not `CLAUDE_API_KEY = "key"` ❌
- Make sure `python-dotenv` is installed

### "CSV file not found"
- Always run commands from the project root (`EcoLens/`), not from inside `src/`
- Check the path with `dir` in the terminal to confirm the file exists

### "Only .csv files are accepted" (API error)
- The web UI only accepts `.csv` files — check your file extension

### "Module not found" (ImportError)
- Run `pip install -r requirements.txt` from the project root with your virtual environment active
- Confirm your VS Code interpreter is set to `.venv/Scripts/python.exe`

### "Application startup complete" but UI shows red dot
- Open `http://localhost:8000/api/health` in the browser to confirm the server is actually responding
- If it returns JSON, the server is fine — try refreshing the UI page

### "Analysis failed: 500" in the UI
- Check the terminal where uvicorn is running for the full error traceback
- Most common cause: invalid CSV format or Claude API key issue

---

## Benchmarks Reference

| Benchmark | kg CO2 / year | Notes |
|-----------|---------------|-------|
| US Average | 16,000 | Highest in developed world |
| European Average | 6,800 | |
| Global Average | 4,000 | |
| Paris Agreement Target | 2,300 | Required to limit warming to 1.5°C |

---

## Adding New Emission Categories

To add a new category (e.g., `streaming_services`):

1. Add it to `emission_factors.json` under `"categories"` with its CO2 factor
2. Add it to the `AVAILABLE CATEGORIES` list in `prompts.py` so Claude knows to use it
3. Add a calculation branch in `calculator.py` under `calculate_transaction()`
4. Add it to the category label and color maps in `ui/carbon/index.html`
5. Update the table in this README

---

## License

This project is part of the EcoLens AI Environmental Intelligence Platform.
