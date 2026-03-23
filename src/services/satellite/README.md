# Satellite Environmental Monitor

AI-powered satellite image analysis tool that fetches before/after imagery from NASA GIBS, runs Claude Vision to detect environmental changes, and quantifies the results as hard metrics (area lost, carbon emissions, severity score).

---

## The Two Ways to Use This Feature

| Method | When to use |
|---|---|
| **Browser UI** | Best for exploration, viewing results visually, comparing images side-by-side |
| **Terminal / VS Code** | Best for scripting, batch runs, or when you want direct CLI output |

---

## Setup

### Prerequisites

- `CLAUDE_API_KEY` in `.env` (for Vision API calls)
- No NASA API key needed — GIBS is open access

### Install dependencies

```bash
pip install -r requirements.txt
```

Core packages: `anthropic`, `requests`, `Pillow`, `python-dotenv`

---

---

# Method 1 — Browser UI

## How to Start

**Step 1 — Start the Satellite API server**

VS Code Task:
```
Terminal > Run Task > 🛰️ Start Satellite API (:8002)
```

Or F5 → select **"🛰️ Satellite API (uvicorn :8002)"**

Or terminal:
```bash
uvicorn src.api.satellite_api:app --reload --port 8002
```

**Step 2 — Open the UI**

VS Code Task:
```
Terminal > Run Task > 🌐 Open Satellite UI
```

Or double-click `ui/satellite/index.html`.

## UI Walkthrough

**Left panel — Configure your analysis:**

1. **Preset Regions tab** — click any region card to select it. The recommended dates and satellite layer auto-fill. Cloud risk badge (☀️ / ⛅ / ☁️) tells you how likely you are to get clear imagery.

2. **Custom tab** — enter lat/lon, before/after dates, and analysis type manually.

3. **Satellite Layer** — choose the imagery source. For most regions, leave on VIIRS (daily, 375m). Use Sentinel or Landsat for sharper 30m imagery (they have less frequent passes so the retry logic may search ±7 days).

4. **Run Analysis** button — activates once a region is selected. Click to start.

**Right panel — Results:**

- A live progress log appears while the analysis runs (30–90 seconds)
- When complete, the result loads automatically showing:
  - Before/after satellite images side by side
  - Land cover breakdown (forest %, urban %, water %, cleared %)
  - Change summary and environmental impact (written by Claude)
  - Quantified metrics (area changed in km², carbon emissions if applicable)
  - API cost

**Past Results sidebar** — all previous analyses are listed at the bottom of the left panel. Click any to reload without re-running.

---

---

# Method 2 — Terminal / VS Code

## All Commands (run from project root)

### List available preset regions
```bash
python src/services/satellite/analyzer.py --list
```

### Run a preset region (fastest — uses recommended dates and layer)
```bash
python src/services/satellite/analyzer.py dubai
python src/services/satellite/analyzer.py las_vegas
python src/services/satellite/analyzer.py arctic_greenland
python src/services/satellite/analyzer.py amazon_basin
python src/services/satellite/analyzer.py delhi_ncr
python src/services/satellite/analyzer.py congo_basin
python src/services/satellite/analyzer.py california_forests
```

### Run with custom coordinates (single-line, no backslashes)
```bash
python src/services/satellite/analyzer.py --lat 25.2048 --lon 55.2708 --before 2018-02-01 --after 2024-02-01 --name "Dubai UAE" --type urban_sprawl
```

```bash
python src/services/satellite/analyzer.py --lat 28.6139 --lon 77.2090 --before 2019-02-01 --after 2024-02-01 --name "Delhi NCR India" --type urban_sprawl
```

```bash
python src/services/satellite/analyzer.py --lat 12.9716 --lon 77.5946 --before 2019-02-01 --after 2024-02-01 --name "Bengaluru India" --type urban_sprawl
```

### Run with a specific satellite layer
```bash
python src/services/satellite/analyzer.py --lat 28.6139 --lon 77.2090 --before 2019-02-01 --after 2024-02-01 --name "Delhi NCR India" --type urban_sprawl --layer sentinel
```

```bash
python src/services/satellite/analyzer.py --lat 28.6139 --lon 77.2090 --before 2019-02-01 --after 2024-02-01 --name "Delhi NCR India" --type urban_sprawl --layer landsat
```

### Available `--layer` options

| Flag | Satellite | Resolution | Coverage |
|---|---|---|---|
| `viirs_day` | VIIRS SNPP | 375m | Daily ← **default** |
| `modis_terra` | MODIS Terra | 250m | Daily |
| `modis_aqua` | MODIS Aqua | 250m | Daily |
| `sentinel` | Sentinel-2 | 30m | Every 5 days |
| `landsat` | Landsat 8/9 | 30m | Every 16 days |

### Available `--type` options

| Flag | Use for |
|---|---|
| `general` | Unknown/mixed change (default) |
| `deforestation` | Forest loss, carbon emission estimates |
| `urban_sprawl` | Urban expansion, infrastructure growth |
| `ice_melt` | Glacier or sea ice retreat |

## VS Code F5 Launch Configs

The following run configurations are available in `.vscode/launch.json` — press F5 and select from the dropdown:

- **🛰️ Satellite API (uvicorn :8002)** — starts the API server

## Output Files

Results are saved to `src/services/satellite/results/` with three files per run:

| File | Contents |
|---|---|
| `*_analysis.json` | Complete raw data — all metrics, vision responses, image paths, cost |
| `*_report.md` | Human-readable Markdown summary |
| `*_metrics.csv` | Spreadsheet-ready row of key metrics |

Downloaded satellite images are saved to `src/services/satellite/data/downloads/<location_name>/`.

---

## Preset Regions Reference

| Key | Location | Type | Cloud risk | Best months |
|---|---|---|---|---|
| `amazon_basin` | Amazon, Brazil | Deforestation | ☁️ High | Aug–Sep (dry season) |
| `amazon_rondonia` | Rondônia, Brazil | Deforestation | ☁️ High | Aug–Sep |
| `congo_basin` | Congo DRC | Deforestation | ⛅ Medium | Jun–Aug |
| `las_vegas` | Nevada, USA | Urban sprawl | ☀️ Low | Any time |
| `dubai` | UAE | Urban sprawl | ☀️ Low | Any time |
| `delhi_ncr` | India | Urban sprawl | ⛅ Medium | Jan–Feb (avoid Nov for smog) |
| `arctic_greenland` | Greenland | Ice melt | ☀️ Low | Jul–Aug (polar summer) |
| `california_forests` | N. California | Fire damage | ☀️ Low | Sep–Oct (post-fire) |

---

## Why Images Are Sometimes Blurry or Blank

**Blurry** — VIIRS has 375m native resolution. If the bounding box is too small relative to the image canvas size, GIBS has to upscale the pixels, producing a blocky result. The default `0.5°` bbox (~55km) is calibrated for VIIRS. Use `sentinel` or `landsat` for 30m sharp imagery.

**White/blank** — Full cloud cover. The fetcher automatically retries ±7 days from your requested date to find a cloud-free image. If all 14 retry dates are also cloudy, it gives up and raises an error. Avoid the Amazon and Congo during rainy season (Nov–May). Avoid Delhi in November (winter smog).

**"Image not available" placeholder in UI** — The image file was downloaded in a previous run but has since been deleted from `data/downloads/`. Re-run the analysis to regenerate the images.

---

## API Cost

Each analysis makes exactly **3 Claude API calls**:
- 2 Vision calls (before and after images)
- 1 Text call (comparison and change detection)

Typical cost: **$0.02–$0.05 per run**.

NASA GIBS image downloads are free — no API key, no cost, no rate limits.
