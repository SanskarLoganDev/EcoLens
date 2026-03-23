"""
EcoLens — Satellite Monitor API
================================
FastAPI backend for the Satellite Environmental Monitor UI.
Runs on port 8002.

Endpoints:
  GET  /api/satellite/health           — liveness check
  GET  /api/satellite/regions          — list preset regions
  GET  /api/satellite/layers           — list available satellite layers
  GET  /api/satellite/results          — list past analysis results
  GET  /api/satellite/results/{id}     — retrieve a specific result JSON
  GET  /api/satellite/image            — serve a downloaded PNG as base64
  POST /api/satellite/analyze          — start an analysis (background thread)
  GET  /api/satellite/status/{job_id}  — poll job status and progress log

Run with:
  uvicorn src.api.satellite_api:app --reload --port 8002
"""

import sys
import os
import json
import uuid
import base64
import threading
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Path setup ────────────────────────────────────────────────────────────────
_SATELLITE_DIR = Path(__file__).parent.parent / "services" / "satellite"
sys.path.insert(0, str(_SATELLITE_DIR))

from satellite_config import REGIONS, GIBS_LAYERS, DEFAULT_LAYER  # noqa: E402

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="EcoLens Satellite API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Paths ─────────────────────────────────────────────────────────────────────
RESULTS_DIR   = _SATELLITE_DIR / "results"
DOWNLOADS_DIR = _SATELLITE_DIR / "data" / "downloads"

# ── In-memory job store ───────────────────────────────────────────────────────
_jobs: Dict[str, dict] = {}


# ── Request models ────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    region_key:    Optional[str]   = None
    lat:           Optional[float] = None
    lon:           Optional[float] = None
    before_date:   Optional[str]   = None
    after_date:    Optional[str]   = None
    location_name: Optional[str]   = None
    analysis_type: str             = "general"
    layer:         str             = DEFAULT_LAYER


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/satellite/health")
def health():
    return {"status": "ok", "service": "EcoLens Satellite API", "port": 8002}


@app.get("/api/satellite/regions")
def list_regions():
    CLOUD_RISK = {
        "amazon_basin":      "high",
        "amazon_rondonia":   "high",
        "congo_basin":       "medium",
        "las_vegas":         "low",
        "dubai":             "low",
        "delhi_ncr":         "medium",
        "arctic_greenland":  "low",
        "california_forests":"low",
        "test_location":     "high",
    }
    TYPE_EMOJI = {
        "deforestation": "🌳",
        "urban_sprawl":  "🏙️",
        "ice_melt":      "🧊",
        "fire_damage":   "🔥",
        "test":          "🧪",
    }
    result = []
    for key, region in REGIONS.items():
        result.append({
            "key":               key,
            "name":              region["name"],
            "lat":               region["lat"],
            "lon":               region["lon"],
            "type":              region["type"],
            "description":       region.get("description", ""),
            "before_date":       region["recommended_dates"]["before"],
            "after_date":        region["recommended_dates"]["after"],
            "recommended_layer": region.get("recommended_layer", DEFAULT_LAYER),
            "cloud_risk":        CLOUD_RISK.get(key, "medium"),
            "emoji":             TYPE_EMOJI.get(region["type"], "🛰️"),
        })
    return {"regions": result}


@app.get("/api/satellite/layers")
def list_layers():
    return {"layers": [
        {"key": "viirs_day",   "name": "VIIRS (Daily)",        "resolution": "375m", "frequency": "Daily",         "description": "Best availability. Recommended for most regions."},
        {"key": "modis_terra", "name": "MODIS Terra (Daily)",  "resolution": "250m", "frequency": "Daily",         "description": "Daily coverage, slightly sharper than VIIRS."},
        {"key": "sentinel",    "name": "Sentinel-2 (5-day)",   "resolution": "30m",  "frequency": "Every 5 days",  "description": "High resolution. Sharp imagery, may miss some dates."},
        {"key": "landsat",     "name": "Landsat 8/9 (16-day)", "resolution": "30m",  "frequency": "Every 16 days", "description": "Highest resolution. Fewest available dates."},
    ]}


@app.get("/api/satellite/results")
def list_results():
    if not RESULTS_DIR.exists():
        return {"results": []}
    # Sort by file modification time, newest first
    files = sorted(RESULTS_DIR.glob("*_analysis.json"),
                   key=lambda f: f.stat().st_mtime, reverse=True)
    items = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            loc  = data.get("location", {})
            tp   = data.get("time_period", {})
            chg  = data.get("changes", {})
            cost = data.get("api_cost", {})
            items.append({
                "id":              f.stem,
                "location_name":   loc.get("name", f.stem),
                "before_date":     tp.get("before", ""),
                "after_date":      tp.get("after", ""),
                "analysis_type":   data.get("analysis_type", ""),
                "change_detected": chg.get("change_detected", False),
                "severity":        chg.get("severity", ""),
                "severity_score":  chg.get("severity_score", 0),
                "total_cost_usd":  cost.get("total_cost_usd", 0),
                "analysis_date":   data.get("analysis_date", ""),
                "layer":           data.get("images", {}).get("before", {}).get("layer", ""),
            })
        except Exception:
            pass
    return {"results": items}


@app.get("/api/satellite/results/{result_id}")
def get_result(result_id: str):
    if not RESULTS_DIR.exists():
        raise HTTPException(status_code=404, detail="No results directory.")
    target = RESULTS_DIR / f"{result_id}.json"
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Result '{result_id}' not found.")
    return JSONResponse(content=json.loads(target.read_text(encoding="utf-8")))


@app.get("/api/satellite/image")
def get_image(path: str):
    """Read a satellite PNG from disk and return it as a base64 data URI."""
    img_path = Path(path)
    if not img_path.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {path}")
    b64 = base64.b64encode(img_path.read_bytes()).decode("utf-8")
    return {"data_uri": f"data:image/png;base64,{b64}"}


@app.post("/api/satellite/analyze")
def start_analysis(request: AnalyzeRequest):
    """Start a satellite analysis as a background thread. Returns job_id immediately."""
    if not request.region_key:
        if not all([request.lat is not None, request.lon is not None,
                    request.before_date, request.after_date]):
            raise HTTPException(
                status_code=400,
                detail="Provide region_key OR all of: lat, lon, before_date, after_date"
            )
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status":       "running",
        "progress_log": [],
        "result_id":    None,
        "error":        None,
        "started_at":   datetime.now().isoformat(),
    }
    threading.Thread(target=_run_analysis_job, args=(job_id, request), daemon=True).start()
    return {"job_id": job_id, "status": "started"}


@app.get("/api/satellite/status/{job_id}")
def get_job_status(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    job = _jobs[job_id]
    return {
        "status":       job["status"],
        "progress_log": job["progress_log"],
        "result_id":    job.get("result_id"),
        "error":        job["error"],
    }


# ── Background job ────────────────────────────────────────────────────────────

def _log(job_id: str, msg: str):
    _jobs[job_id]["progress_log"].append(msg)


def _run_analysis_job(job_id: str, request: AnalyzeRequest):
    """
    Runs inside a background thread.

    HOW WE FIND THE CORRECT RESULT FILE
    ─────────────────────────────────────
    The old approach did:
        result_files = sorted(RESULTS_DIR.glob("*_analysis.json"), reverse=True)
        result_id = result_files[0].stem

    This sorted alphabetically and took the first item. That is wrong because:
      - Filenames start with the location name, not the timestamp.
      - "california_forests_..." sorts before "greenland_...", so running
        Greenland after California always returned the California file.

    The correct approach:
      1. Record the wall-clock time just before the analysis starts.
      2. After it finishes, find all JSON files whose modification time
         (st_mtime) is >= that start timestamp.
      3. Among those candidates, take the one with the newest mtime.

    This is robust to alphabetical ordering, multiple simultaneous jobs,
    and any number of pre-existing result files.
    """
    try:
        _log(job_id, "⚙️  Loading satellite analyzer...")
        from satellite_config import get_region   # noqa
        from analyzer import SatelliteAnalyzer    # noqa

        analyzer = SatelliteAnalyzer(layer=request.layer)
        _log(job_id, f"✅ Analyzer ready  (layer: {request.layer})")

        if request.region_key:
            region = get_region(request.region_key)
            lat, lon    = region["lat"], region["lon"]
            before      = region["recommended_dates"]["before"]
            after       = region["recommended_dates"]["after"]
            name, atype = region["name"], region["type"]
        else:
            lat, lon = request.lat, request.lon
            before   = request.before_date
            after    = request.after_date
            name     = request.location_name or f"{lat}, {lon}"
            atype    = request.analysis_type

        _log(job_id, f"📍 Location: {name}")
        _log(job_id, f"📅 Period: {before}  →  {after}")
        _log(job_id, "🛰️  Fetching satellite images from NASA GIBS...")

        # ── Snapshot the clock BEFORE the analysis writes any files ──────────
        job_start_time = datetime.now().timestamp()

        analyzer.analyze_location(
            lat=lat, lon=lon,
            before_date=before, after_date=after,
            location_name=name, analysis_type=atype
        )

        _log(job_id, "🤖 Claude Vision analysis complete")
        _log(job_id, "📊 Change detection complete")

        # ── Find the result file created by THIS job ──────────────────────────
        # Collect every analysis JSON whose mtime is at or after job_start_time.
        # If multiple somehow match (shouldn't happen in serial use), take newest.
        candidates = [
            f for f in RESULTS_DIR.glob("*_analysis.json")
            if f.stat().st_mtime >= job_start_time
        ]

        if candidates:
            # Pick the most recently written among candidates (handles edge cases)
            result_file = max(candidates, key=lambda f: f.stat().st_mtime)
            _jobs[job_id]["result_id"] = result_file.stem
        else:
            # Fallback: no file newer than start time found (filesystem clock skew?)
            # Log a warning and fall back to newest file overall.
            _log(job_id, "⚠️  Could not identify result by timestamp — using newest file")
            all_files = sorted(RESULTS_DIR.glob("*_analysis.json"),
                               key=lambda f: f.stat().st_mtime, reverse=True)
            _jobs[job_id]["result_id"] = all_files[0].stem if all_files else None

        _jobs[job_id]["status"] = "done"
        _log(job_id, "✅ Analysis complete!")

    except Exception as e:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"]  = str(e)
        _log(job_id, f"❌ Failed: {e}")
