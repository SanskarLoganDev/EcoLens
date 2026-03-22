"""
EcoLens — RAG + Summarizer API
================================
FastAPI backend for both the RAG Q&A feature and the Paper Summarizer UI.

Runs on port 8001 (separate from the Carbon API on port 8000).

RAG Endpoints:
  GET  /api/rag/health              — liveness check
  GET  /api/rag/papers              — list indexed papers
  GET  /api/rag/available           — list PDFs in research_papers/ (indexed or not)
  POST /api/rag/index               — index a PDF from research_papers/
  POST /api/rag/chat                — ask a question, get a cited answer
  DELETE /api/rag/papers/{name}     — remove a paper from the index

Summarizer Endpoints:
  GET  /api/summarizer/available    — list PDFs available to summarize
  GET  /api/summarizer/results      — list existing summary JSON files
  GET  /api/summarizer/results/{id} — retrieve a specific summary result
  POST /api/summarizer/run          — run the full summarizer pipeline on a PDF

Run with:
  uvicorn src.api.rag_api:app --reload --port 8001
  (from project root)
"""

import sys
import os
import json
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Path setup ────────────────────────────────────────────────────────────────
_SERVICE_DIR = Path(__file__).parent.parent / "services" / "research_paper_analyzer"
_RAG_DIR     = _SERVICE_DIR / "rag"
sys.path.insert(0, str(_SERVICE_DIR))
sys.path.insert(0, str(_RAG_DIR))

from rag.indexer   import RagIndexer    # noqa: E402
from rag.retriever import RagRetriever  # noqa: E402

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "EcoLens Research API",
    description = "RAG Q&A and Paper Summarizer for climate science papers",
    version     = "1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

# ── Paths ─────────────────────────────────────────────────────────────────────
PAPERS_DIR  = _SERVICE_DIR / "research_papers"
RESULTS_DIR = _SERVICE_DIR / "results"

# ── Lazy singletons ───────────────────────────────────────────────────────────
_indexer:   Optional[RagIndexer]   = None
_retriever: Optional[RagRetriever] = None

# Track summarizer jobs so the UI can poll for completion
# key: filename, value: "running" | "done" | "error: <msg>"
_summarizer_jobs: dict = {}


def get_indexer() -> RagIndexer:
    global _indexer
    if _indexer is None:
        _indexer = RagIndexer()
    return _indexer


def get_retriever() -> RagRetriever:
    global _retriever
    if _retriever is None:
        _retriever = RagRetriever()
    return _retriever


# ── Request / response models ─────────────────────────────────────────────────

class IndexRequest(BaseModel):
    filename: str

class ChatMessage(BaseModel):
    role:    str
    content: str

class ChatRequest(BaseModel):
    question: str
    history:  List[ChatMessage] = []

class SummarizeRequest(BaseModel):
    filename:       str   # e.g. "ocean_acidification.pdf"
    analyze_images: bool = False   # default off — Poppler required for True


# ── RAG Routes ────────────────────────────────────────────────────────────────

@app.get("/api/rag/health")
def health():
    return {"status": "ok", "service": "EcoLens Research API", "port": 8001}


@app.get("/api/rag/papers")
def list_indexed_papers():
    try:
        papers = get_indexer().list_indexed_papers()
        return {"papers": papers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/available")
def list_available_pdfs():
    try:
        indexer = get_indexer()
        pdfs    = sorted(PAPERS_DIR.glob("*.pdf"))
        result  = [
            {
                "filename": pdf.name,
                "indexed":  indexer.is_indexed(pdf.name),
                "size_kb":  round(pdf.stat().st_size / 1024, 1),
            }
            for pdf in pdfs
        ]
        return {"papers": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/index")
def index_paper(request: IndexRequest):
    pdf_path = PAPERS_DIR / request.filename
    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"'{request.filename}' not found in research_papers/.",
        )
    try:
        result = get_indexer().index_pdf(str(pdf_path))
        global _retriever
        _retriever = None
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")


@app.post("/api/rag/chat")
def chat(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    try:
        retriever = get_retriever()
        history   = [{"role": m.role, "content": m.content} for m in request.history]
        result    = retriever.answer(question=request.question, chat_history=history)
        return JSONResponse(content=result)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="No papers indexed yet.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")


@app.delete("/api/rag/papers/{filename}")
def delete_paper(filename: str):
    try:
        n = get_indexer().delete_paper(filename)
        global _retriever
        _retriever = None
        return {"deleted": True, "chunks_removed": n, "paper": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Summarizer Routes ─────────────────────────────────────────────────────────

@app.get("/api/summarizer/available")
def summarizer_available_pdfs():
    """
    List all PDFs in research_papers/ along with whether a summary
    result already exists for each one.
    """
    pdfs    = sorted(PAPERS_DIR.glob("*.pdf"))
    results = list(RESULTS_DIR.glob("paper_analysis_*.json")) if RESULTS_DIR.exists() else []

    # Build a set of stems that have been summarised
    # e.g. "paper_analysis_ocean_acidification_2025-12-31_17-44.json" → "ocean_acidification"
    summarised_stems = set()
    for r in results:
        # strip "paper_analysis_" prefix and the timestamp suffix
        name = r.stem  # e.g. "paper_analysis_ocean_acidification_2025-12-31_17-44-05"
        name = name.replace("paper_analysis_", "", 1)
        # drop the timestamp: last two _-separated parts are date and time
        parts = name.rsplit("_", 2)
        stem  = parts[0] if len(parts) == 3 else name
        summarised_stems.add(stem)

    result = []
    for pdf in pdfs:
        pdf_stem = pdf.stem  # e.g. "ocean_acidification"
        result.append({
            "filename":    pdf.name,
            "size_kb":     round(pdf.stat().st_size / 1024, 1),
            "has_summary": pdf_stem in summarised_stems,
            "job_status":  _summarizer_jobs.get(pdf.name, None),
        })

    return {"papers": result}


@app.get("/api/summarizer/results")
def list_summary_results():
    """
    List all existing paper_analysis_*.json files, newest first.
    Returns lightweight metadata — not the full JSON content.
    """
    if not RESULTS_DIR.exists():
        return {"results": []}

    files = sorted(RESULTS_DIR.glob("paper_analysis_*.json"), reverse=True)
    items = []
    for f in files:
        # Try to read just the file_info and metadata blocks cheaply
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            items.append({
                "id":           f.stem,
                "filename":     f.name,
                "pdf_name":     data.get("file_info", {}).get("filename", ""),
                "title":        data.get("metadata", {}).get("title", f.stem),
                "pages":        data.get("file_info", {}).get("pages", "?"),
                "analyzed_date": data.get("file_info", {}).get("analyzed_date", ""),
                "total_cost":   data.get("api_cost",  {}).get("total_cost_usd", 0),
                "size_kb":      round(f.stat().st_size / 1024, 1),
            })
        except Exception:
            items.append({"id": f.stem, "filename": f.name})

    return {"results": items}


@app.get("/api/summarizer/results/{result_id}")
def get_summary_result(result_id: str):
    """Retrieve the full JSON for a specific summary by its file stem."""
    if not RESULTS_DIR.exists():
        raise HTTPException(status_code=404, detail="No results directory found.")

    target = RESULTS_DIR / f"{result_id}.json"
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Result '{result_id}' not found.")

    return JSONResponse(content=json.loads(target.read_text(encoding="utf-8")))


@app.post("/api/summarizer/run")
def run_summarizer(request: SummarizeRequest, background_tasks: BackgroundTasks):
    """
    Start a summarizer analysis on a PDF.

    This runs as a FastAPI background task so the HTTP response returns
    immediately while the analysis runs (it takes 30–90 seconds).

    The UI polls GET /api/summarizer/available to watch job_status change
    from "running" → "done" or "error: <msg>".

    Request body:
        {
            "filename":       "ocean_acidification.pdf",
            "analyze_images": false
        }

    Immediate response:
        { "status": "started", "filename": "ocean_acidification.pdf" }
    """
    pdf_path = PAPERS_DIR / request.filename
    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"'{request.filename}' not found in research_papers/.",
        )

    if _summarizer_jobs.get(request.filename) == "running":
        return {"status": "already_running", "filename": request.filename}

    background_tasks.add_task(
        _run_summarizer_task,
        request.filename,
        str(pdf_path),
        request.analyze_images,
    )

    _summarizer_jobs[request.filename] = "running"
    return {"status": "started", "filename": request.filename}


def _run_summarizer_task(filename: str, pdf_path: str, analyze_images: bool):
    """Background task that runs PaperAnalyzer and updates _summarizer_jobs."""
    try:
        # Import here (inside the task) to avoid circular import issues
        # and to ensure a fresh sys.path is available
        from analyze_papers import PaperAnalyzer  # noqa: E402
        analyzer = PaperAnalyzer()
        analyzer.analyze_paper(pdf_path, analyze_images=analyze_images)
        _summarizer_jobs[filename] = "done"
    except Exception as e:
        _summarizer_jobs[filename] = f"error: {e}"
