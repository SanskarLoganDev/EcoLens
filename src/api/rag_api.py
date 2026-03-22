"""
EcoLens — RAG API
=================
FastAPI backend for the research paper RAG (Retrieval-Augmented Generation) feature.

Runs on port 8001 (separate from the Carbon API on port 8000).

Endpoints:
  GET  /api/rag/health           — liveness check
  GET  /api/rag/papers           — list indexed papers
  GET  /api/rag/available        — list PDFs in research_papers/ (indexed or not)
  POST /api/rag/index            — index a PDF from research_papers/
  POST /api/rag/chat             — ask a question, get a cited answer
  DELETE /api/rag/papers/{name}  — remove a paper from the index

Run with:
  uvicorn src.api.rag_api:app --reload --port 8001
  (from project root)
"""

import sys
import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Path setup ────────────────────────────────────────────────────────────────
# Make the research_paper_analyzer service importable
_SERVICE_DIR = Path(__file__).parent.parent / "services" / "research_paper_analyzer"
_RAG_DIR     = _SERVICE_DIR / "rag"
sys.path.insert(0, str(_SERVICE_DIR))
sys.path.insert(0, str(_RAG_DIR))

from rag.indexer   import RagIndexer    # noqa: E402
from rag.retriever import RagRetriever  # noqa: E402

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "EcoLens RAG API",
    description = "Ask questions across indexed climate science research papers",
    version     = "1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

# ── Lazy singletons ───────────────────────────────────────────────────────────
# We initialise these on first use so that starting the server doesn't
# require ChromaDB to already exist (it might not on a fresh install).
_indexer:   Optional[RagIndexer]   = None
_retriever: Optional[RagRetriever] = None

PAPERS_DIR = _SERVICE_DIR / "research_papers"


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
    filename: str   # e.g. "ocean_acidification.pdf"

class ChatMessage(BaseModel):
    role:    str    # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    question: str
    history:  List[ChatMessage] = []


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/rag/health")
def health():
    """Confirm the RAG API is running."""
    return {"status": "ok", "service": "EcoLens RAG API", "port": 8001}


@app.get("/api/rag/papers")
def list_indexed_papers():
    """
    Return all papers that have been indexed into ChromaDB.

    Response:
        {
            "papers": [
                {
                    "source_file": "ocean_acidification.pdf",
                    "paper_title": "OCEAN ACIDIFICATION",
                    "authors":     "Bamaniya et al.",
                    "chunk_count": 34
                }
            ]
        }
    """
    try:
        indexer = get_indexer()
        papers  = indexer.list_indexed_papers()
        return {"papers": papers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/available")
def list_available_pdfs():
    """
    Return all PDFs in the research_papers/ folder, with an
    'indexed' flag showing whether each one is in ChromaDB.

    Response:
        {
            "papers": [
                {
                    "filename": "ocean_acidification.pdf",
                    "indexed":  true,
                    "size_kb":  1240
                }
            ]
        }
    """
    try:
        indexer = get_indexer()
        pdfs    = sorted(PAPERS_DIR.glob("*.pdf"))

        result = []
        for pdf in pdfs:
            result.append({
                "filename": pdf.name,
                "indexed":  indexer.is_indexed(pdf.name),
                "size_kb":  round(pdf.stat().st_size / 1024, 1),
            })

        return {"papers": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/index")
def index_paper(request: IndexRequest):
    """
    Index a PDF from the research_papers/ folder.

    The file must already exist in:
        src/services/research_paper_analyzer/research_papers/

    This is a synchronous call — it blocks until indexing is complete
    (typically 5-30 seconds depending on paper length).

    Request body:
        { "filename": "ocean_acidification.pdf" }

    Response:
        {
            "status":         "indexed",
            "paper":          "ocean_acidification.pdf",
            "chunks_added":   34,
            "chunks_skipped": 0,
            "pages":          20
        }
    """
    pdf_path = PAPERS_DIR / request.filename

    if not pdf_path.exists():
        raise HTTPException(
            status_code = 404,
            detail = (
                f"'{request.filename}' not found in research_papers/. "
                f"Available files: {[p.name for p in PAPERS_DIR.glob('*.pdf')]}"
            ),
        )

    try:
        indexer = get_indexer()
        result  = indexer.index_pdf(str(pdf_path))

        # Reset retriever so it picks up the new chunks next request
        global _retriever
        _retriever = None

        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")


@app.post("/api/rag/chat")
def chat(request: ChatRequest):
    """
    Answer a question using retrieved passages from indexed papers.

    Request body:
        {
            "question": "What happens to coral reefs when pH drops?",
            "history": [
                {"role": "user",      "content": "What is ocean acidification?"},
                {"role": "assistant", "content": "Ocean acidification is..."}
            ]
        }

    Response:
        {
            "answer": "According to the ocean acidification paper (page 5)...",
            "sources": [
                {
                    "source_file": "ocean_acidification.pdf",
                    "paper_title": "OCEAN ACIDIFICATION",
                    "page_number": 5,
                    "passage_num": 1
                }
            ],
            "passages_used": 4,
            "no_relevant_content": false
        }
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        retriever = get_retriever()

        # Convert Pydantic models to plain dicts for the retriever
        history = [
            {"role": m.role, "content": m.content}
            for m in request.history
        ]

        result = retriever.answer(
            question     = request.question,
            chat_history = history,
        )

        return JSONResponse(content=result)

    except RuntimeError as e:
        # ChromaDB not initialised — no papers indexed yet
        raise HTTPException(
            status_code = 503,
            detail = (
                "No papers are indexed yet. "
                "Use POST /api/rag/index to index a paper first."
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")


@app.delete("/api/rag/papers/{filename}")
def delete_paper(filename: str):
    """
    Remove a paper's chunks from the ChromaDB index.

    This does NOT delete the original PDF from research_papers/.

    Response:
        { "deleted": true, "chunks_removed": 34, "paper": "ocean_acidification.pdf" }
    """
    try:
        indexer  = get_indexer()
        n_deleted = indexer.delete_paper(filename)

        # Reset retriever so it no longer returns chunks from this paper
        global _retriever
        _retriever = None

        return {
            "deleted":        True,
            "chunks_removed": n_deleted,
            "paper":          filename,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
