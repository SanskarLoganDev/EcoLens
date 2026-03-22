"""
Chunker
=======
Splits PDF page text into overlapping chunks suitable for embedding.

Why chunking matters:
- You cannot embed a 20-page paper as one unit — the vector would be
  an average of everything and lose specificity.
- Too-small chunks lose context (a 50-word chunk may be meaningless alone).
- Overlap ensures that a sentence spanning a chunk boundary is captured
  in at least one of the two surrounding chunks.

This module is pure Python — no API calls, no external dependencies.

Chunk strategy:
    - ~400 words per chunk  (~2,400 characters for scientific text)
    - 75-word overlap between consecutive chunks
    - Chunks are word-boundary aligned (never cut mid-word)
    - Each chunk carries metadata: source file, page number, chunk index

Used by: indexer.py
"""

from typing import List, Dict
import re


# ── Constants ─────────────────────────────────────────────────────────────────

CHUNK_SIZE_WORDS  = 400   # target words per chunk
OVERLAP_WORDS     = 75    # words shared between consecutive chunks

# Minimum words a chunk must have to be worth indexing.
# Avoids storing page-number-only fragments like "Page 3 of 20".
MIN_CHUNK_WORDS   = 30


# ── Chunker class ─────────────────────────────────────────────────────────────

class Chunker:
    """
    Split PDF page texts into overlapping word-based chunks with metadata.

    Usage:
        chunker = Chunker()

        chunks = chunker.chunk_pages(
            page_texts=content["page_texts"],   # from PDFProcessor.extract()
            source_file="ocean_acidification.pdf",
            paper_title="OCEAN ACIDIFICATION",
            authors="Bamaniya et al."
        )

        # Each chunk looks like:
        # {
        #     "text":         "Ocean pH has decreased from 8.25...",
        #     "source_file":  "ocean_acidification.pdf",
        #     "paper_title":  "OCEAN ACIDIFICATION",
        #     "authors":      "Bamaniya et al.",
        #     "page_number":  5,
        #     "chunk_index":  2,
        #     "chunk_id":     "ocean_acidification_p5_c2"
        # }
    """

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE_WORDS,
        overlap: int = OVERLAP_WORDS,
        min_words: int = MIN_CHUNK_WORDS,
    ):
        self.chunk_size = chunk_size
        self.overlap    = overlap
        self.min_words  = min_words

    # ── Public API ─────────────────────────────────────────────────────────

    def chunk_pages(
        self,
        page_texts: List[str],
        source_file: str,
        paper_title: str = "Unknown",
        authors: str     = "Unknown",
    ) -> List[Dict]:
        """
        Convert a list of page texts into a flat list of chunk dicts.

        Each page is chunked independently. This keeps page-number
        metadata accurate (a chunk is never spread across two pages).

        Args:
            page_texts:  List of strings, one per PDF page.
                         Comes directly from PDFProcessor.extract()["page_texts"].
            source_file: PDF filename, e.g. "ocean_acidification.pdf".
                         Used as the unique identifier for this paper.
            paper_title: Paper title (from metadata or first-page text).
            authors:     Author string for display in citations.

        Returns:
            List of chunk dicts, each containing text + metadata.
        """

        all_chunks: List[Dict] = []
        # stem is used in chunk IDs — strip extension, lowercase, spaces→underscores
        source_stem = _make_stem(source_file)

        for page_num, page_text in enumerate(page_texts, start=1):
            if not page_text or not page_text.strip():
                continue

            # Clean up PDF extraction artefacts
            cleaned = _clean_text(page_text)

            # Split page into overlapping word-windows
            word_windows = _split_into_windows(
                cleaned, self.chunk_size, self.overlap
            )

            for chunk_idx, chunk_text in enumerate(word_windows):
                # Skip near-empty fragments (headers, footers, page numbers)
                if len(chunk_text.split()) < self.min_words:
                    continue

                chunk_id = f"{source_stem}_p{page_num}_c{chunk_idx}"

                all_chunks.append({
                    "text":        chunk_text,
                    "source_file": source_file,
                    "paper_title": paper_title,
                    "authors":     authors,
                    "page_number": page_num,
                    "chunk_index": chunk_idx,
                    "chunk_id":    chunk_id,
                })

        return all_chunks

    def stats(self, chunks: List[Dict]) -> Dict:
        """
        Return summary statistics for a list of chunks.
        Useful for quick sanity checks after chunking.
        """
        if not chunks:
            return {"total_chunks": 0}

        word_counts = [len(c["text"].split()) for c in chunks]
        pages       = sorted(set(c["page_number"] for c in chunks))

        return {
            "total_chunks":   len(chunks),
            "pages_covered":  len(pages),
            "avg_words":      round(sum(word_counts) / len(word_counts)),
            "min_words":      min(word_counts),
            "max_words":      max(word_counts),
            "source_file":    chunks[0]["source_file"],
        }


# ── Private helpers ───────────────────────────────────────────────────────────

def _make_stem(filename: str) -> str:
    """
    Turn "Ocean Acidification (2024).pdf" → "ocean_acidification_2024_"
    so it's safe to use in IDs and filenames.
    """
    stem = filename.rsplit(".", 1)[0]          # drop extension
    stem = stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "_", stem)   # non-alphanumeric → underscore
    stem = stem.strip("_")
    return stem


def _clean_text(text: str) -> str:
    """
    Remove common PDF extraction noise:
    - Hyphenated line-breaks ("acidifi-\ncation" → "acidification")
    - Excessive whitespace / control characters
    - Lone page-number lines
    """
    # Rejoin hyphenated words split across lines
    text = re.sub(r"-\n(\s*)", "", text)
    # Normalise whitespace (tabs, multiple spaces → single space)
    text = re.sub(r"[ \t]+", " ", text)
    # Normalise newlines (2+ consecutive → single paragraph break)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_into_windows(
    text: str, chunk_size: int, overlap: int
) -> List[str]:
    """
    Split text into overlapping word windows.

    Example with chunk_size=5, overlap=2:
        words = [A B C D E F G H I J]
        window 0: [A B C D E]        (words 0-4)
        window 1: [D E F G H]        (words 3-7)  ← 2-word overlap with window 0
        window 2: [G H I J]          (words 6-9)  ← 2-word overlap with window 1

    The step size is (chunk_size - overlap), so consecutive windows
    share `overlap` words.
    """
    words = text.split()
    if not words:
        return []

    step    = max(1, chunk_size - overlap)
    windows = []

    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        windows.append(" ".join(words[start:end]))
        start += step

    return windows


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Quick test — run from project root:
        python src/services/research_paper_analyzer/rag/chunker.py
    """
    import sys
    import json
    from pathlib import Path

    # Add parent dir so we can import PDFProcessor
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pdf_processor import PDFProcessor

    if len(sys.argv) < 2:
        # Default to ocean acidification paper
        pdf_path = (
            Path(__file__).parent.parent
            / "research_papers"
            / "ocean_acidification.pdf"
        )
    else:
        pdf_path = Path(sys.argv[1])

    print(f"\n📄 Chunking: {pdf_path.name}")
    print("=" * 60)

    processor = PDFProcessor()
    content   = processor.extract(str(pdf_path), extract_images=False)

    chunker = Chunker()
    chunks  = chunker.chunk_pages(
        page_texts  = content["page_texts"],
        source_file = pdf_path.name,
        paper_title = content["metadata"].get("title", "Unknown"),
        authors     = content["metadata"].get("author", "Unknown"),
    )

    print(f"\n📊 Stats:")
    print(json.dumps(chunker.stats(chunks), indent=2))

    print(f"\n📝 First chunk preview:")
    print(f"   ID   : {chunks[0]['chunk_id']}")
    print(f"   Page : {chunks[0]['page_number']}")
    print(f"   Words: {len(chunks[0]['text'].split())}")
    print(f"   Text : {chunks[0]['text'][:200]}...")

    print(f"\n📝 Second chunk preview (shows overlap with first):")
    if len(chunks) > 1:
        print(f"   Text : {chunks[1]['text'][:200]}...")

    print("\n✅ Chunker test complete!")
