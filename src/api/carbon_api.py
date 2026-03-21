"""
EcoLens — Carbon Footprint API
================================
FastAPI backend that wraps the existing carbon service pipeline.

Endpoints:
  POST /api/carbon/analyze      — upload CSV, run full pipeline, return JSON
  GET  /api/carbon/sample       — return sample CSV content as text
  GET  /api/carbon/results      — list all past result files
  GET  /api/carbon/results/{id} — retrieve a specific past result

Run with:
  uvicorn src.api.carbon_api:app --reload --port 8000
  (from project root)
"""

import sys
import os
import json
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

# ── Path setup ───────────────────────────────────────────────
# Add the carbon service directory to sys.path so we can import
# its modules (parser, calculator, client, prompts) directly.
CARBON_DIR = Path(__file__).parent.parent / "services" / "carbon"
sys.path.insert(0, str(CARBON_DIR))

from analyzer import CarbonAnalyzer  # noqa: E402  (import after path setup)

# ── App ───────────────────────────────────────────────────────
app = FastAPI(
    title="EcoLens Carbon API",
    description="AI-powered carbon footprint analysis from transaction CSVs",
    version="1.0.0",
)

# Allow the local UI (opened as a file:// page or served on any port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # lock this down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    """Quick liveness check — open http://localhost:8000/api/health in browser."""
    return {"status": "ok", "service": "EcoLens Carbon API"}


@app.get("/api/carbon/sample", response_class=PlainTextResponse)
def get_sample_csv():
    """
    Returns the built-in sample CSV so the UI can display it
    or allow the user to download it.
    """
    sample_path = CARBON_DIR / "samples" / "sample_transactions_5.csv"
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample file not found")
    return sample_path.read_text(encoding="utf-8")


@app.post("/api/carbon/analyze")
async def analyze(file: UploadFile = File(...)):
    """
    Main analysis endpoint.

    Accepts a multipart CSV upload, runs the full pipeline:
      1. Parse transactions
      2. Claude AI categorization
      3. Emission calculation
      4. Benchmark comparison
      5. Claude AI coaching

    Returns the complete analysis JSON.
    """
    # Validate file type
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    # Write upload to a temp file (the existing parser expects a file path)
    contents = await file.read()
    with tempfile.NamedTemporaryFile(
        suffix=".csv", delete=False, mode="wb"
    ) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        analyzer = CarbonAnalyzer()
        result = analyzer.analyze_file(tmp_path)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        # Always clean up the temp file
        os.unlink(tmp_path)


@app.get("/api/carbon/results")
def list_results():
    """
    Returns metadata for all previously saved result JSON files,
    newest first.
    """
    results_dir = CARBON_DIR / "results"
    if not results_dir.exists():
        return {"results": []}

    files = sorted(results_dir.glob("carbon_analysis_*.json"), reverse=True)
    items = []
    for f in files:
        stat = f.stat()
        items.append({
            "id": f.stem,
            "filename": f.name,
            "size_kb": round(stat.st_size / 1024, 1),
            "modified": stat.st_mtime,
        })
    return {"results": items}


@app.get("/api/carbon/results/{result_id}")
def get_result(result_id: str):
    """
    Retrieve a specific past analysis by its file stem ID.
    Example: GET /api/carbon/results/carbon_analysis_sample_transactions_5_2025-05-01_12-00-00
    """
    results_dir = CARBON_DIR / "results"
    target = results_dir / f"{result_id}.json"
    if not target.exists():
        raise HTTPException(status_code=404, detail="Result not found")
    return JSONResponse(content=json.loads(target.read_text(encoding="utf-8")))
