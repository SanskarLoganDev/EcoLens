"""
RAG (Retrieval-Augmented Generation) package for EcoLens research papers.

This package enables semantic search and question-answering over
the raw text of scientific PDFs — completely separate from the
summary feature in analyze_papers.py.

Components:
    chunker.py   — splits PDF page text into overlapping chunks
    indexer.py   — embeds chunks via Voyage AI and stores in ChromaDB
    retriever.py — searches ChromaDB and generates answers via Claude

Usage:
    from rag.indexer import RagIndexer
    from rag.retriever import RagRetriever

    # Index a paper (do once per paper)
    indexer = RagIndexer()
    indexer.index_pdf("research_papers/ocean_acidification.pdf")

    # Ask questions (do any time)
    retriever = RagRetriever()
    result = retriever.answer("What happens to coral reefs when pH drops?")
    print(result["answer"])
"""

from .indexer import RagIndexer
from .retriever import RagRetriever
from .chunker import Chunker

__all__ = ["RagIndexer", "RagRetriever", "Chunker"]
