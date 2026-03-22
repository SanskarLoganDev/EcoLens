"""
RAG Retriever
=============
Given a user question, finds the most relevant text chunks from ChromaDB
and asks Claude to answer using only those chunks as evidence.

This is the "read" side of RAG.  The indexer.py is the "write" side.

Pipeline:
    User question (string)
        │
        ▼
    voyageai.Client().embed()       ← voyage-3.5-lite, input_type="query"
        │  query_vector: List[float]
        ▼
    ChromaDB similarity search          ← cosine distance over all stored vectors
        │  top_k chunks with metadata
        ▼
    Build Claude prompt                 ← inject chunks + conversation history
        │
        ▼
    Claude answer                       ← grounded, cited response
        │
        ▼
    Return { answer, sources }

Key design decisions:
    - input_type="query" on the question embedding (vs "document" for chunks)
      This asymmetry is intentional — Voyage optimises each direction separately.
    - Claude is instructed to cite passage numbers [1], [2], etc.
    - Claude is told to say "I don't know" if passages don't answer the question.
    - Conversation history is included so Claude handles follow-up questions.

Usage:
    from rag.retriever import RagRetriever

    retriever = RagRetriever()
    result = retriever.answer("What happens to coral reefs when pH drops?")
    print(result["answer"])
    print(result["sources"])
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# ── Path setup ────────────────────────────────────────────────────────────────
_SERVICE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_SERVICE_DIR))

from client import ClaudeClient          # noqa: E402

import chromadb                          # noqa: E402
import voyageai                          # noqa: E402
from dotenv import load_dotenv, find_dotenv  # noqa: E402

dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)

# ── Constants ─────────────────────────────────────────────────────────────────

CHROMA_PATH     = Path(__file__).parent / "chroma_store"
COLLECTION_NAME = "climate_papers"

# Must match the model used in indexer.py — vectors must be in the same space.
EMBEDDING_MODEL = "voyage-3.5-lite"

DEFAULT_TOP_K   = 6     # chunks to retrieve per question

# Cosine distance threshold (0 = identical, 2 = opposite).
# Chunks further than this are considered irrelevant and excluded.
MAX_DISTANCE    = 0.65


# ── RagRetriever ──────────────────────────────────────────────────────────────

class RagRetriever:
    """
    Answer questions using retrieved passages from indexed research papers.

    Usage:
        retriever = RagRetriever()

        # Simple question
        result = retriever.answer("What is ocean acidification?")
        print(result["answer"])

        # With conversation history (for follow-up questions)
        history = [
            {"role": "user",      "content": "What is ocean acidification?"},
            {"role": "assistant", "content": "Ocean acidification is..."},
        ]
        result = retriever.answer("How does it affect coral reefs?", history)
    """

    def __init__(self):
        # ── Voyage AI — for embedding questions ──────────────────────────
        voyage_key = os.getenv("VOYAGE_API_KEY")
        if not voyage_key:
            raise ValueError(
                "VOYAGE_API_KEY not found in environment.\n"
                "Add it to your .env file:\n"
                "  VOYAGE_API_KEY=\"your-key-here\""
            )
        self.voyage = voyageai.Client(api_key=voyage_key)

        # ── Claude — for generating grounded answers ──────────────────────
        claude_key = os.getenv("CLAUDE_API_KEY")
        if not claude_key:
            raise ValueError("CLAUDE_API_KEY not found in environment.")
        self.claude = ClaudeClient(api_key=claude_key)

        # ── ChromaDB — must already contain indexed chunks ────────────────
        if not CHROMA_PATH.exists():
            raise RuntimeError(
                f"ChromaDB store not found at {CHROMA_PATH}.\n"
                "Run the indexer first:\n"
                "  python src/services/research_paper_analyzer/rag/indexer.py --all"
            )

        self.chroma     = chromadb.PersistentClient(path=str(CHROMA_PATH))
        self.collection = self.chroma.get_collection(name=COLLECTION_NAME)

        chunk_count = self.collection.count()
        if chunk_count == 0:
            print("⚠️  ChromaDB collection is empty — no papers indexed yet.")
        else:
            print(f"✅ RagRetriever ready ({chunk_count} chunks in index)")

    # ── Public API ─────────────────────────────────────────────────────────

    def answer(
        self,
        question: str,
        chat_history: Optional[List[Dict]] = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> Dict:
        """
        Answer a question using retrieved passages from indexed papers.

        Args:
            question:     The user's question.
            chat_history: Previous turns for follow-up context.
                          [{"role": "user"|"assistant", "content": "..."}]
            top_k:        Number of chunks to retrieve (default 6).

        Returns:
            {
                "answer":              "According to...",
                "sources":             [{"source_file": ..., "page_number": ...}],
                "passages_used":       4,
                "no_relevant_content": False
            }
        """
        if not question.strip():
            return {
                "answer":              "Please ask a question.",
                "sources":             [],
                "passages_used":       0,
                "no_relevant_content": True,
            }

        # Step 1: embed the question
        query_vector = self._embed_query(question)

        # Step 2: find similar chunks in ChromaDB
        passages = self._retrieve(query_vector, top_k)

        if not passages:
            return {
                "answer": (
                    "I couldn't find relevant information in the indexed papers "
                    "to answer your question. Try rephrasing, or make sure the "
                    "relevant paper has been indexed."
                ),
                "sources":             [],
                "passages_used":       0,
                "no_relevant_content": True,
            }

        # Step 3: ask Claude to answer using those passages
        prompt      = _build_rag_prompt(question, passages, chat_history or [])
        response    = self.claude.call(
            messages    = [{"role": "user", "content": prompt}],
            temperature = 0.3,
        )
        answer_text = response["content"]

        # Step 4: build clean source list
        sources = _deduplicate_sources(passages)

        return {
            "answer":              answer_text,
            "sources":             sources,
            "passages_used":       len(passages),
            "no_relevant_content": False,
        }

    def list_papers(self) -> List[Dict]:
        """Return metadata about every paper currently in the index."""
        if self.collection.count() == 0:
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

    # ── Private helpers ────────────────────────────────────────────────────

    def _embed_query(self, question: str) -> List[float]:
        """
        Embed the user's question using voyageai.Client().embed()
        with input_type="query".

        input_type="query" tells Voyage to produce a retrieval-optimised
        vector — slightly different from the "document" vectors stored
        during indexing. This asymmetry is intentional and improves search
        quality over using the same embedding direction for both.
        """
        result = self.voyage.embed(
            [question],
            model      = EMBEDDING_MODEL,
            input_type = "query",
        )
        return result.embeddings[0]   # List[float]

    def _retrieve(self, query_vector: List[float], top_k: int) -> List[Dict]:
        """
        Search ChromaDB for the top_k most similar chunks.
        Excludes chunks with cosine distance > MAX_DISTANCE.
        """
        results = self.collection.query(
            query_embeddings = [query_vector],
            n_results        = top_k,
            include          = ["documents", "metadatas", "distances"],
        )

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        passages = []
        for i, (doc, meta, dist) in enumerate(
            zip(documents, metadatas, distances), start=1
        ):
            if dist > MAX_DISTANCE:
                continue

            passages.append({
                "passage_num": i,
                "text":        doc,
                "source_file": meta.get("source_file", "unknown"),
                "paper_title": meta.get("paper_title", "unknown"),
                "authors":     meta.get("authors", "Unknown"),
                "page_number": meta.get("page_number", "?"),
                "distance":    round(dist, 4),
            })

        return passages


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_rag_prompt(
    question: str,
    passages: List[Dict],
    chat_history: List[Dict],
) -> str:
    """Build the Claude prompt with injected retrieved passages."""

    passage_lines = []
    for p in passages:
        passage_lines.append(
            f"[{p['passage_num']}] "
            f"Source: {p['source_file']} | Page {p['page_number']}\n"
            f"{p['text']}"
        )
    passages_block = "\n\n" + ("-" * 60 + "\n").join(passage_lines)

    history_block = ""
    if chat_history:
        recent = chat_history[-6:]
        lines  = [
            f"{t.get('role','user').capitalize()}: {t.get('content','')}"
            for t in recent
        ]
        history_block = "\n\nCONVERSATION SO FAR:\n" + "\n".join(lines)

    return f"""You are a climate science research assistant. You have access to passages retrieved from scientific research papers.

INSTRUCTIONS:
- Answer the question using ONLY the information in the passages below.
- Cite sources using [passage number], e.g. "Ocean pH has dropped [1]."
- If the question asks for specific data (numbers, percentages, dates), quote them exactly from the passages.
- If the passages do not contain enough information to answer the question, say clearly: "The indexed papers don't contain sufficient information about this topic."
- Do NOT make up information that is not in the passages.
- Write in clear, plain English suitable for a non-specialist reader.

RETRIEVED PASSAGES:
{passages_block}
{history_block}

QUESTION: {question}

Answer:"""


def _deduplicate_sources(passages: List[Dict]) -> List[Dict]:
    """One citation per unique (source_file, page_number) pair."""
    seen, sources = set(), []
    for p in passages:
        key = (p["source_file"], p["page_number"])
        if key not in seen:
            seen.add(key)
            sources.append({
                "source_file": p["source_file"],
                "paper_title": p["paper_title"],
                "authors":     p["authors"],
                "page_number": p["page_number"],
                "passage_num": p["passage_num"],
            })
    return sources


# ── Standalone interactive CLI ────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Interactive terminal Q&A.

    From project root:
        python src/services/research_paper_analyzer/rag/retriever.py
    """
    print("\n" + "=" * 60)
    print("EcoLens RAG — Research Paper Q&A")
    print("=" * 60)
    print("Type a question. Type 'papers' to list indexed papers. 'quit' to exit.\n")

    try:
        retriever = RagRetriever()
    except Exception as e:
        print(f"\n❌ Could not start retriever: {e}")
        sys.exit(1)

    history = []

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        if question.lower() == "papers":
            papers = retriever.list_papers()
            if not papers:
                print("📭 No papers indexed yet.")
            else:
                for p in papers:
                    print(f"   • {p['source_file']} ({p['chunk_count']} chunks)")
            print()
            continue

        print("🔍 Searching...\n")
        result = retriever.answer(question, chat_history=history)
        print(f"Assistant: {result['answer']}")

        if result["sources"]:
            print(f"\n📚 Sources:")
            for s in result["sources"]:
                print(f"   [{s['passage_num']}] {s['source_file']}, p.{s['page_number']}")
        print()

        history.append({"role": "user",      "content": question})
        history.append({"role": "assistant", "content": result["answer"]})
