"""
CivicResolve AI - Document Intelligence OCR Engine
Extracts textual content from PDF files and images (PNG, JPG, JPEG) using PyMuPDF and OCR.
Provides clean fallback if Tesseract is not installed on the host system.
"""
import os
import io
import fitz  # PyMuPDF
from PIL import Image
from typing import Tuple, Dict, Any

# Optional pytesseract
try:
    import pytesseract
except ImportError:
    pytesseract = None


def extract_text_from_file(file_bytes: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extracts text and structural metadata from PDF or image byte streams.
    Returns (extracted_text, metadata_dict).
    """
    ext = os.path.splitext(filename)[1].lower()
    metadata = {
        "filename": filename,
        "extension": ext,
        "size_bytes": len(file_bytes),
        "extraction_method": "text_stream",
        "ocr_performed": False,
        "page_count": 1
    }

    if ext == ".pdf":
        return _extract_pdf(file_bytes, metadata)
    elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
        return _extract_image(file_bytes, metadata)
    elif ext in [".txt", ".text"]:
        return file_bytes.decode("utf-8", errors="ignore"), metadata
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Supported: PDF, PNG, JPG, JPEG, TXT.")


def _extract_pdf(file_bytes: bytes, metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Extracts text from PDF pages using PyMuPDF; falls back to OCR if pages are images."""
    extracted_pages = []
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    metadata["page_count"] = len(doc)

    ocr_used = False
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if text:
            extracted_pages.append(f"--- Page {page_num + 1} ---\n{text}")
        else:
            # Scanned or image-only PDF page: attempt OCR
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            ocr_text = _run_ocr_on_pil_image(img)
            if ocr_text:
                extracted_pages.append(f"--- Page {page_num + 1} (OCR) ---\n{ocr_text}")
                ocr_used = True

    doc.close()
    metadata["ocr_performed"] = ocr_used
    metadata["extraction_method"] = "pymupdf_hybrid" if ocr_used else "pymupdf_text"
    full_text = "\n\n".join(extracted_pages)
    return full_text, metadata


def _extract_image(file_bytes: bytes, metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Extracts text from image using OCR or Pillow image inspection."""
    img = Image.open(io.BytesIO(file_bytes))
    metadata["dimensions"] = f"{img.width}x{img.height}"
    metadata["format"] = img.format
    metadata["ocr_performed"] = True

    text = _run_ocr_on_pil_image(img)
    metadata["extraction_method"] = "ocr_tesseract" if text else "image_metadata_only"
    return text, metadata


def _run_ocr_on_pil_image(img: Image.Image) -> str:
    """Invokes pytesseract if configured; returns empty string if unavailable."""
    if pytesseract is not None:
        try:
            custom_cmd = os.getenv("TESSERACT_CMD")
            if custom_cmd and os.path.exists(custom_cmd):
                pytesseract.pytesseract.tesseract_cmd = custom_cmd
            return pytesseract.image_to_string(img)
        except Exception as e:
            # Tesseract binary not on PATH or execution error
            pass
    return ""
