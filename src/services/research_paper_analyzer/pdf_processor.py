"""
PDF Processor
=============
Extract text and images from PDF research papers.

This module:
1. Reads PDF files
2. Extracts all text content
3. Extracts images (charts, graphs, diagrams)
4. Detects document structure (sections, headings)
5. Converts images to base64 for Vision API

Dependencies:
- PyPDF2: For basic PDF reading
- pdf2image: For converting PDF pages to images
- Pillow (PIL): For image processing

Used by: analyzer.py
"""

import base64
import io
import re
from typing import Dict, List, Optional
from pathlib import Path
from PyPDF2 import PdfReader
import pdf2image


class PDFProcessor:
    """
    Extract text and images from PDF research papers.
    
    Usage:
        processor = PDFProcessor()
        content = processor.extract("paper.pdf")
        
        # Access extracted data
        text = content['text']
        images = content['images']
        metadata = content['metadata']
    """
    
    def __init__(self):
        """Initialize PDF processor"""
        print("✅ PDF Processor initialized")
    
    def extract(self, pdf_path: str, extract_images: bool = True) -> Dict:
        """
        Extract all content from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            extract_images: Whether to extract images (can be slow for large PDFs)
        
        Returns:
            {
                'text': "full paper text",
                'pages': 127,
                'metadata': {'title': ..., 'author': ...},
                'images': [
                    {
                        'page': 23,
                        'image_data': 'base64...',
                        'caption': 'Figure 3.2: ...'
                    }
                ],
                'sections': [...]
            }
        """
        
        print(f"\n📄 Processing PDF: {pdf_path}")
        print("="*60)
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # Extract text
        print("📖 Extracting text...")
        text_data = self._extract_text(pdf_path)
        
        # Extract metadata
        print("ℹ️  Extracting metadata...")
        metadata = self._extract_metadata(pdf_path)
        
        # Extract images (optional, can be slow)
        images = []
        if extract_images:
            print("🖼️  Extracting images (this may take a while)...")
            images = self._extract_images(pdf_path)
        else:
            print("⏭️  Skipping image extraction (set extract_images=True to enable)")
        
        print(f"\n✅ PDF processing complete!")
        print(f"   Pages: {text_data['pages']}")
        print(f"   Characters: {len(text_data['text']):,}")
        print(f"   Images: {len(images)}")
        
        return {
            'text': text_data['text'],
            'pages': text_data['pages'],
            'page_texts': text_data['page_texts'],
            'metadata': metadata,
            'images': images,
            'file_name': pdf_path.name
        }
    
    def _extract_text(self, pdf_path: Path) -> Dict:
        """
        Extract text from PDF.
        
        Returns:
            {
                'text': "combined text from all pages",
                'pages': total_page_count,
                'page_texts': ["page 1 text", "page 2 text", ...]
            }
        """
        
        try:
            reader = PdfReader(str(pdf_path))
            page_texts = []
            
            for page_num, page in enumerate(reader.pages, 1):
                # Extract text from page
                text = page.extract_text()
                page_texts.append(text)
                
                if page_num % 10 == 0:
                    print(f"   Processed {page_num} pages...")
            
            # Combine all pages
            full_text = "\n\n".join(page_texts)
            
            return {
                'text': full_text,
                'pages': len(page_texts),
                'page_texts': page_texts
            }
            
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {e}")
    
    def _extract_metadata(self, pdf_path: Path) -> Dict:
        """
        Extract PDF metadata (title, author, etc.)
        
        Note: Many PDFs have incomplete metadata.
        We'll also try to extract from first page text.
        """
        
        try:
            reader = PdfReader(str(pdf_path))
            pdf_metadata = reader.metadata or {}
            
            return {
                'title': pdf_metadata.get('/Title', 'Unknown'),
                'author': pdf_metadata.get('/Author', 'Unknown'),
                'subject': pdf_metadata.get('/Subject', ''),
                'creator': pdf_metadata.get('/Creator', ''),
                'creation_date': pdf_metadata.get('/CreationDate', '')
            }
            
        except Exception as e:
            print(f"   Warning: Could not extract metadata: {e}")
            return {}
    
    def _extract_images(self, pdf_path: Path, 
                       max_images: int = 50,
                       min_size: int = 100) -> List[Dict]:
        """
        Extract images from PDF.
        
        This is COMPLEX because:
        - Some images are embedded in PDF
        - Some are rendered from vector graphics
        - We need to convert PDF pages to images to capture charts
        
        Strategy: Convert each page to image, detect if it contains figures
        
        Args:
            pdf_path: Path to PDF
            max_images: Maximum images to extract (to control costs)
            min_size: Minimum image size in pixels
        
        Returns:
            List of image dicts with base64 data
        """
        
        images = []
        
        try:
            # Convert PDF pages to images
            # This captures everything, including vector graphics
            pages = pdf2image.convert_from_path(
                pdf_path,
                dpi=150,  # Balance quality vs size
                fmt='png'
            )
            
            for page_num, page_image in enumerate(pages, 1):
                # Check if this page likely contains a figure
                # (This is a heuristic - we look for pages with less text)
                
                # For now, let's extract images from pages that might have charts
                # We'll look for pages with "Figure" or "Table" in their text
                
                # For simplicity in MVP, let's extract first N pages
                # that might contain important charts
                
                if len(images) >= max_images:
                    print(f"   Reached max images ({max_images}), stopping extraction")
                    break
                
                # Skip very small images
                if page_image.width < min_size or page_image.height < min_size:
                    continue
                
                # Convert to base64
                buffered = io.BytesIO()
                page_image.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode()
                
                images.append({
                    'page': page_num,
                    'image_data': img_base64,
                    'width': page_image.width,
                    'height': page_image.height,
                    'caption': f"Page {page_num}"  # Will try to extract captions later
                })
                
                if page_num % 10 == 0:
                    print(f"   Extracted {len(images)} images from {page_num} pages...")
            
            return images
            
        except Exception as e:
            print(f"   Warning: Could not extract images: {e}")
            print(f"   Make sure pdf2image and poppler are installed")
            print(f"   macOS: brew install poppler")
            print(f"   Ubuntu: sudo apt install poppler-utils")
            return []
    
    def detect_figure_captions(self, page_texts: List[str]) -> Dict[int, List[str]]:
        """
        Detect figure captions in the text.
        
        Looks for patterns like:
        - "Figure 3.2: Ocean pH trends..."
        - "Table 1: Summary statistics..."
        
        Args:
            page_texts: List of text from each page
        
        Returns:
            Dict mapping page number to list of captions found
        """
        
        captions = {}
        
        # Regex pattern for figure/table captions
        # Matches: "Figure 3.2: Some caption text"
        pattern = r'(Figure|Table|Fig\.|Tab\.)\s+\d+\.?\d*:?\s+([^\n]{10,100})'
        
        for page_num, text in enumerate(page_texts, 1):
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            if matches:
                page_captions = [f"{match[0]} {match[1]}" for match in matches]
                captions[page_num] = page_captions
        
        return captions
    
    def chunk_text(self, text: str, chunk_size: int = 3000) -> List[str]:
        """
        Split text into chunks for API processing.
        
        Long papers need to be split into manageable chunks
        for Claude API (context window limits).
        
        Args:
            text: Full paper text
            chunk_size: Target chunk size in characters
        
        Returns:
            List of text chunks
        """
        
        # Simple chunking by character count
        # Better approach: chunk by sections, but this works for MVP
        
        chunks = []
        words = text.split()
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word) + 1  # +1 for space
            
            if current_size + word_size > chunk_size and current_chunk:
                # Save current chunk and start new one
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size
        
        # Add last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks


# Example usage / testing
if __name__ == "__main__":
    """
    Test PDF processor with a sample file.
    
    Usage:
        python pdf_processor.py sample_paper.pdf
    """
    
    import sys
    import json
    
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python pdf_processor.py <pdf_file>")
        print("\nExample: python pdf_processor.py research_paper.pdf")
        sys.exit(1)

    pdf_file = sys.argv[1]

    try:
        print(f"\n📍 Step: Checking file: {pdf_file}")
        print(f"   Current directory: {Path.cwd()}")
        print(f"   File exists: {Path(pdf_file).exists()}")

        if not Path(pdf_file).exists():
            print(f"\n❌ Error: File not found!")
            print(f"   Path attempted: {pdf_file}")
            print(f"   Absolute path: {Path(pdf_file).absolute()}")
            sys.exit(1)

        # Process PDF
        print("\n📍 Step: Initializing PDF processor...")
        processor = PDFProcessor()

        # Extract without images first (faster)
        print("\n" + "="*60)
        print("PROCESSING PDF (TEXT ONLY)")
        print("="*60)

        print("\n📍 Step: Extracting text...")
        content = processor.extract(pdf_file, extract_images=False)

        # Show results
        print("\n" + "="*60)
        print("EXTRACTION RESULTS")
        print("="*60)

        print(f"\n📊 Metadata:")
        print(json.dumps(content['metadata'], indent=2))

        print(f"\n📖 Text Preview (first 500 chars):")
        print(content['text'][:500])
        print("...")

        print(f"\n📏 Statistics:")
        print(f"   Total pages: {content['pages']}")
        print(f"   Total characters: {len(content['text']):,}")
        print(f"   Total words (approx): {len(content['text'].split()):,}")

        # Test chunking
        chunks = processor.chunk_text(content['text'], chunk_size=2000)
        print(f"\n✂️  Text chunks (for API): {len(chunks)}")
        print(f"   Chunk 1 length: {len(chunks[0])} chars")

        # Detect captions
        captions = processor.detect_figure_captions(content['page_texts'])
        print(f"\n🖼️  Figure captions found: {sum(len(caps) for caps in captions.values())}")
        if captions:
            print(f"   Example: {list(captions.values())[0][0]}")

        # Optionally extract images (slow!)
        print("\n" + "="*60)
        extract_imgs = input("Extract images? (slow, costs API credits) [y/N]: ")

        if extract_imgs.lower() == 'y':
            print("\n📍 Step: Extracting images...")
            content_with_images = processor.extract(pdf_file, extract_images=True)
            print(f"   Extracted {len(content_with_images['images'])} images")
            if content_with_images['images']:
                print(f"   First image size: {len(content_with_images['images'][0]['image_data'])} bytes (base64)")

        print("\n✅ PDF processing test complete!")

    except FileNotFoundError as e:
        print(f"\n❌ FileNotFoundError: {e}")
        print(f"\n📍 Location: File lookup failed")
        print(f"   File attempted: {pdf_file}")
        print(f"   Current directory: {Path.cwd()}")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()

    except ImportError as e:
        print(f"\n❌ ImportError: {e}")
        print(f"\n📍 Location: Missing required module")
        print("\nRequired dependencies:")
        print("  - PyPDF2: pip install PyPDF2")
        print("  - pdf2image: pip install pdf2image")
        print("  - Pillow: pip install Pillow")
        print("\nSystem requirements:")
        print("  - poppler (for pdf2image)")
        print("    macOS: brew install poppler")
        print("    Ubuntu: sudo apt install poppler-utils")
        print("    Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()

    except Exception as e:
        print(f"\n❌ Unexpected error ({type(e).__name__}): {e}")
        print(f"\n📍 Location: Error details below")
        print("\nPossible causes:")
        print("  - Corrupted PDF file")
        print("  - Invalid PDF format")
        print("  - Missing poppler installation")
        print("  - Insufficient memory for large PDFs")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()