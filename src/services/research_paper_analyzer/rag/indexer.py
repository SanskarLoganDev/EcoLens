"""
RAG Indexer
===========
Reads a PDF, chunks its text, embeds each chunk via Voyage AI
(voyageai package), and stores everything in ChromaDB.

This is the "write" side of RAG.  Run it once per paper.
The retriever.py is the "read" side that answers questions.

Pipeline:
    PDF file
        │
        ▼
    PDFProcessor.extract()          ← existing module, unchanged
        │  page_texts: List[str]
        ▼
    Chunker.chunk_pages()           ← overlapping word windows
        │  chunks: List[Dict]
        ▼
    voyageai.Client().embed()       ← voyage-3.5-lite model, input_type="document"
        │  vectors: List[List[float]]
        ▼
    ChromaDB.collection.add()       ← persistent vector store on disk
        │
        ▼
    chroma_store/                   ← files saved here, survives restarts

Usage (from project root):
    python src/services/research_paper_analyzer/rag/indexer.py \\
        src/services/research_paper_analyzer/research_papers/ocean_acidification.pdf

    # Index ALL papers in research_papers/
    python src/services/research_paper_analyzer/rag/indexer.py --all

    # List what is already indexed
    python src/services/research_paper_analyzer/rag/indexer.py --list

Dependencies:
    pip install chromadb voyageai
    VOYAGE_API_KEY must be set in .env
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Optional

# ── Path setup ────────────────────────────────────────────────────────────────
_SERVICE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_SERVICE_DIR))

from pdf_processor import PDFProcessor  # noqa: E402
from rag.chunker import Chunker          # noqa: E402

import chromadb                          # noqa: E402
import voyageai                          # noqa: E402
from dotenv import load_dotenv, find_dotenv  # noqa: E402

# Load .env from project root
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)

# ── Constants ─────────────────────────────────────────────────────────────────

CHROMA_PATH      = Path(__file__).parent / "chroma_store"
COLLECTION_NAME  = "climate_papers"

# voyage-3.5-lite: optimised for latency and cost, ideal for this use case.
# voyage-3.5 is higher quality but ~3x the cost — upgrade later if needed.
# Source: https://docs.voyageai.com/docs/embeddings
EMBEDDING_MODEL  = "voyage-3.5-lite"

# Voyage allows up to 128 texts per batch; stay safely below that.
EMBED_BATCH_SIZE = 96


# ── RagIndexer ────────────────────────────────────────────────────────────────

class RagIndexer:
    """
    Index research paper PDFs into ChromaDB for RAG retrieval.

    Usage:
        indexer = RagIndexer()

        # Index one paper
        result = indexer.index_pdf("research_papers/ocean_acidification.pdf")
        print(result)
        # {"status": "indexed", "chunks_added": 34, "paper": "ocean_acidification.pdf"}

        # Check what is already indexed
        papers = indexer.list_indexed_papers()

        # Remove a paper from the index
        indexer.delete_paper("ocean_acidification.pdf")
    """

    def __init__(self):
        # ── Voyage AI client ──────────────────────────────────────────────
        voyage_key = os.getenv("VOYAGE_API_KEY")
        if not voyage_key:
            raise ValueError(
                "VOYAGE_API_KEY not found in environment.\n"
                "Add it to your .env file:\n"
                "  VOYAGE_API_KEY=\"your-key-here\"\n"
                "Get a free key at: https://dash.voyageai.com/"
            )
        # voyageai.Client() automatically reads VOYAGE_API_KEY from env,
        # but passing it explicitly avoids any ambiguity.
        self.voyage = voyageai.Client(api_key=voyage_key)

        # ── ChromaDB — persistent on disk ─────────────────────────────────
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        self.chroma = chromadb.PersistentClient(path=str(CHROMA_PATH))

        # cosine similarity is standard for normalised text embeddings
        self.collection = self.chroma.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        # ── Helpers ───────────────────────────────────────────────────────
        self.pdf_processor = PDFProcessor()
        self.chunker        = Chunker()

        existing = self._count_total_chunks()
        print(f"✅ RagIndexer ready")
        print(f"   ChromaDB : {CHROMA_PATH}")
        print(f"   Model    : {EMBEDDING_MODEL}")
        print(f"   Collection: '{COLLECTION_NAME}' ({existing} chunks already stored)")

    # ── Public methods ─────────────────────────────────────────────────────

    def index_pdf(self, pdf_path: str) -> Dict:
        """
        Full pipeline: PDF → chunks → embeddings → ChromaDB.

        Safe to call multiple times on the same file — already-indexed
        chunks are skipped automatically.

        Returns:
            {
                "status":         "indexed" | "already_indexed" | "partially_indexed",
                "paper":          "ocean_acidification.pdf",
                "chunks_added":   34,
                "chunks_skipped": 0,
                "pages":          20,
            }
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        source_file = pdf_path.name
        print(f"\n📄 Indexing: {source_file}")
        print("=" * 60)

        # ── Step 1: Extract text ──────────────────────────────────────────
        print("\n📖 Step 1/4: Extracting text from PDF...")
        content     = self.pdf_processor.extract(str(pdf_path), extract_images=False)
        pages       = content["pages"]
        meta        = content.get("metadata", {})
        paper_title = meta.get("title") or source_file
        authors_raw = meta.get("author") or "Unknown"
        print(f"   ✓ {pages} pages, {len(content['text']):,} characters")

        # ── Step 2: Chunk ─────────────────────────────────────────────────
        print("\n✂️  Step 2/4: Splitting into overlapping chunks...")
        chunks = self.chunker.chunk_pages(
            page_texts  = content["page_texts"],
            source_file = source_file,
            paper_title = paper_title,
            authors     = authors_raw,
        )
        stats = self.chunker.stats(chunks)
        print(f"   ✓ {stats['total_chunks']} chunks "
              f"(avg {stats['avg_words']} words, "
              f"{stats['pages_covered']} pages)")

        # ── Step 3: Deduplication ─────────────────────────────────────────
        print("\n🔍 Step 3/4: Checking for already-indexed chunks...")
        new_chunks, skipped = self._filter_new_chunks(chunks)

        if skipped > 0:
            print(f"   ⏭  {skipped} chunks already in index — skipping")
        if not new_chunks:
            print("   ✓ This paper is already fully indexed!")
            return {
                "status":         "already_indexed",
                "paper":          source_file,
                "chunks_added":   0,
                "chunks_skipped": skipped,
                "pages":          pages,
            }
        print(f"   ✓ {len(new_chunks)} new chunks to embed")

        # ── Step 4: Embed + store ─────────────────────────────────────────
        print(f"\n🔢 Step 4/4: Embedding {len(new_chunks)} chunks "
              f"via {EMBEDDING_MODEL}...")
        chunks_added = self._embed_and_store(new_chunks)

        status = "indexed" if skipped == 0 else "partially_indexed"
        print(f"\n✅ Done! {chunks_added} chunks added to ChromaDB.")

        return {
            "status":         status,
            "paper":          source_file,
            "chunks_added":   chunks_added,
            "chunks_skipped": skipped,
            "pages":          pages,
        }

    def index_all(self, papers_dir: str) -> List[Dict]:
        """Index every PDF in the given directory."""
        papers_dir = Path(papers_dir)
        pdfs       = sorted(papers_dir.glob("*.pdf"))

        if not pdfs:
            print(f"⚠️  No PDFs found in {papers_dir}")
            return []

        print(f"\n📚 Found {len(pdfs)} PDFs to process")
        results = []

        for pdf in pdfs:
            try:
                result = self.index_pdf(str(pdf))
                results.append(result)
            except Exception as e:
                print(f"❌ Failed to index {pdf.name}: {e}")
                results.append({"status": "error", "paper": pdf.name, "error": str(e)})

        print(f"\n✅ Indexing complete: {len(results)} papers processed")
        return results

    def list_indexed_papers(self) -> List[Dict]:
        """Return metadata about every paper currently in the index."""
        if self._count_total_chunks() == 0:
            return []

        result    = self.collection.get(include=["metadatas"])
        metadatas = result.get("metadatas", [])

        papers: Dict[str, Dict] = {}
        for meta in metadatas:
            src = meta.get("source_file", "unknown")
            if src not in papers:
                papers[src] = {
                    "source_file": src,
                    "paper_title": meta.get("paper_title", src),
                    "authors":     meta.get("authors", "Unknown"),
                    "chunk_count": 0,
                }
            papers[src]["chunk_count"] += 1

        return sorted(papers.values(), key=lambda p: p["source_file"])

    def is_indexed(self, source_file: str) -> bool:
        """Return True if at least one chunk from source_file is in the index."""
        result = self.collection.get(
            where={"source_file": source_file},
            limit=1,
            include=["metadatas"],
        )
        return len(result.get("ids", [])) > 0

    def delete_paper(self, source_file: str) -> int:
        """Remove all chunks for a given paper from the index."""
        result = self.collection.get(
            where={"source_file": source_file},
            include=["metadatas"],
        )
        ids_to_delete = result.get("ids", [])

        if not ids_to_delete:
            print(f"⚠️  '{source_file}' not found in index")
            return 0

        self.collection.delete(ids=ids_to_delete)
        print(f"🗑️  Deleted {len(ids_to_delete)} chunks for '{source_file}'")
        return len(ids_to_delete)

    # ── Private helpers ────────────────────────────────────────────────────

    def _filter_new_chunks(self, chunks: List[Dict]):
        """Return only chunks whose chunk_id is not already in ChromaDB."""
        if not chunks:
            return [], 0

        existing_ids = set(
            self.collection.get(
                ids=[c["chunk_id"] for c in chunks],
                include=[],
            ).get("ids", [])
        )

        new     = [c for c in chunks if c["chunk_id"] not in existing_ids]
        skipped = len(chunks) - len(new)
        return new, skipped

    def _embed_and_store(self, chunks: List[Dict]) -> int:
        """
        Embed chunks in batches using voyageai.Client().embed()
        with input_type="document", then store in ChromaDB.

        Returns total number of chunks stored.
        """
        total_stored = 0
        batches      = _make_batches(chunks, EMBED_BATCH_SIZE)

        for batch_idx, batch in enumerate(batches, start=1):
            texts = [c["text"] for c in batch]

            print(f"   Batch {batch_idx}/{len(batches)}: "
                  f"embedding {len(texts)} chunks...", end=" ", flush=True)

            t0 = time.time()

            # voyageai.Client().embed() is the correct call.
            # input_type="document" tells Voyage to optimise these vectors
            # for storage/retrieval (as opposed to query-side vectors).
            result  = self.voyage.embed(
                texts,
                model      = EMBEDDING_MODEL,
                input_type = "document",
            )
            vectors = result.embeddings   # List[List[float]]
            elapsed = time.time() - t0

            print(f"done ({elapsed:.1f}s)")

            # Store text + vector + metadata in ChromaDB
            self.collection.add(
                ids        = [c["chunk_id"]  for c in batch],
                documents  = texts,
                embeddings = vectors,
                metadatas  = [
                    {
                        "source_file": c["source_file"],
                        "paper_title": c["paper_title"],
                        "authors":     c["authors"],
                        "page_number": c["page_number"],
                        "chunk_index": c["chunk_index"],
                    }
                    for c in batch
                ],
            )

            total_stored += len(batch)

        return total_stored

    def _count_total_chunks(self) -> int:
        """Return total number of chunks across all papers."""
        return self.collection.count()


# ── Helper ────────────────────────────────────────────────────────────────────

def _make_batches(items: list, batch_size: int) -> List[list]:
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


# ── Standalone CLI ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    From project root:

        # Index a single paper
        python src/services/research_paper_analyzer/rag/indexer.py \\
            src/services/research_paper_analyzer/research_papers/ocean_acidification.pdf

        # Index ALL papers in research_papers/
        python src/services/research_paper_analyzer/rag/indexer.py --all

        # List what is already indexed
        python src/services/research_paper_analyzer/rag/indexer.py --list

        # Remove a paper from the index
        python src/services/research_paper_analyzer/rag/indexer.py --delete ocean_acidification.pdf
    """
    import argparse

    parser = argparse.ArgumentParser(description="EcoLens RAG Indexer")
    parser.add_argument("pdf",     nargs="?", help="Path to PDF to index")
    parser.add_argument("--all",   action="store_true", help="Index all PDFs in research_papers/")
    parser.add_argument("--list",  action="store_true", help="List indexed papers")
    parser.add_argument("--delete", metavar="FILENAME",  help="Delete a paper from the index")
    args = parser.parse_args()

    indexer = RagIndexer()

    if args.list:
        papers = indexer.list_indexed_papers()
        if not papers:
            print("\n📭 No papers indexed yet.")
        else:
            print(f"\n📚 {len(papers)} paper(s) in index:")
            for p in papers:
                print(f"   • {p['source_file']:<40} {p['chunk_count']:>3} chunks")

    elif args.delete:
        indexer.delete_paper(args.delete)

    elif args.all:
        papers_dir = _SERVICE_DIR / "research_papers"
        results    = indexer.index_all(str(papers_dir))
        print("\n📊 Summary:")
        for r in results:
            print(f"   {r['paper']}: {r['status']} "
                  f"({r.get('chunks_added', 0)} chunks added)")

    elif args.pdf:
        result = indexer.index_pdf(args.pdf)
        print(f"\n📊 Result:\n{json.dumps(result, indent=2)}")

    else:
        parser.print_help()
