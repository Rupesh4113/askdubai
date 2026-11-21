"""
CivicResolve AI - High-Fidelity PDF Processing Engine
Handles single-page and multi-page PDFs, native vector text extraction,
table detection with pdfplumber, page preview rendering, and scanned-page routing.
"""
import io
import fitz  # PyMuPDF
from typing import List, Dict, Any, Tuple, Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


class PDFProcessingError(Exception):
    """Specific error for corrupted or password-protected PDF files."""
    def __init__(self, message: str, code: str = "PDF_ERROR"):
        super().__init__(message)
        self.code = code


def inspect_and_process_pdf(file_bytes: bytes) -> Dict[str, Any]:
    """
    Validates, extracts, and renders all pages of a PDF document.
    Returns structured page data, text streams, extracted tables, and page preview images.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise PDFProcessingError(f"Corrupted or invalid PDF document: {str(e)}", code="CORRUPTED_PDF")

    if doc.is_encrypted:
        doc.close()
        raise PDFProcessingError(
            "This PDF document is password-protected. Please unlock or supply an unencrypted copy.",
            code="PASSWORD_PROTECTED_PDF"
        )

    page_count = len(doc)
    if page_count == 0:
        doc.close()
        raise PDFProcessingError("The uploaded PDF file contains zero pages.", code="EMPTY_PDF")

    pages_output = []
    total_native_words = 0

    # Also open with pdfplumber for table extraction if available
    plumber_pdf = None
    if pdfplumber is not None:
        try:
            plumber_pdf = pdfplumber.open(io.BytesIO(file_bytes))
        except Exception:
            plumber_pdf = None

    try:
        for page_idx in range(page_count):
            page = doc[page_idx]
            rect = page.rect
            page_w, page_h = rect.width, rect.height

            # 1. Native text extraction with word coordinates
            words = page.get_text("words")  # (x0, y0, x1, y1, word, block_no, line_no, word_no)
            page_text = page.get_text("text").strip()
            total_native_words += len(words)

            word_tokens = []
            for w in words:
                word_tokens.append({
                    "text": w[4],
                    "bbox": [round(w[0], 2), round(w[1], 2), round(w[2], 2), round(w[3], 2)],
                    "block_id": w[5],
                    "line_id": w[6],
                    "word_id": w[7],
                    "confidence": 1.0  # Native PDF text has perfect character fidelity
                })

            # 2. Extract structured tables for this page
            tables = []
            if plumber_pdf and page_idx < len(plumber_pdf.pages):
                try:
                    p_page = plumber_pdf.pages[page_idx]
                    raw_tables = p_page.extract_tables()
                    for t in raw_tables:
                        if t and len(t) > 1:
                            clean_table = [[cell.strip() if cell else "" for cell in row] for row in t]
                            tables.append(clean_table)
                except Exception:
                    pass
            if not tables and hasattr(page, "find_tables"):
                try:
                    tabs = page.find_tables()
                    for t in tabs:
                        extracted = t.extract()
                        if extracted and len(extracted) > 1:
                            clean_table = [[cell.strip() if cell else "" for cell in row] for row in extracted]
                            tables.append(clean_table)
                except Exception:
                    pass

            # 3. Render high-resolution preview image (DPI 150)
            zoom = 150 / 72.0  # ~2.08x
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            preview_png_bytes = pix.tobytes("png")

            # Determine whether this page is scanned/image-only
            is_scanned = len(words) < 15 or len(page_text) < 30

            pages_output.append({
                "page_number": page_idx + 1,
                "width": round(page_w, 2),
                "height": round(page_h, 2),
                "native_text": page_text,
                "words": word_tokens,
                "tables": tables,
                "is_scanned": is_scanned,
                "preview_png_bytes": preview_png_bytes,
                "native_word_count": len(words)
            })

    finally:
        doc.close()
        if plumber_pdf:
            plumber_pdf.close()

    is_document_scanned = all(p["is_scanned"] for p in pages_output)

    return {
        "page_count": page_count,
        "is_scanned": is_document_scanned,
        "total_native_words": total_native_words,
        "pages": pages_output
    }
