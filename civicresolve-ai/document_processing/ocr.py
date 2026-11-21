"""
CivicResolve AI - Document Intelligence OCR Engine
Extracts textual content from PDF files and images using RapidOCR (PaddleOCR ONNX)
and PyMuPDF native vector text with preprocessing and fallback handling.
"""
import os
import io
from typing import Tuple, Dict, Any

from document_processing.pdf_processor import inspect_and_process_pdf
from document_processing.image_preprocessor import preprocess_image_bytes
from document_processing.ocr_engine import run_ocr_on_image


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
        try:
            pdf_res = inspect_and_process_pdf(file_bytes)
            metadata["page_count"] = pdf_res["page_count"]
            metadata["is_scanned"] = pdf_res["is_scanned"]

            extracted_pages = []
            ocr_performed = False

            for p in pdf_res["pages"]:
                p_num = p["page_number"]
                if p["is_scanned"] and p.get("preview_png_bytes"):
                    ocr_res = run_ocr_on_image(p["preview_png_bytes"], page_number=p_num)
                    extracted_pages.append(f"--- Page {p_num} (RapidOCR) ---\n{ocr_res['full_text']}")
                    ocr_performed = True
                else:
                    extracted_pages.append(f"--- Page {p_num} ---\n{p['native_text']}")

            metadata["ocr_performed"] = ocr_performed
            metadata["extraction_method"] = "pymupdf_rapidocr_hybrid" if ocr_performed else "pymupdf_vector_text"
            full_text = "\n\n".join(extracted_pages)
            return full_text, metadata
        except Exception as e:
            # Fallback
            metadata["error"] = str(e)
            return "", metadata

    elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
        enhanced_bgr, prep_meta = preprocess_image_bytes(file_bytes)
        ocr_res = run_ocr_on_image(enhanced_bgr, page_number=1)
        metadata["dimensions"] = f"{prep_meta.get('original_width')}x{prep_meta.get('original_height')}"
        metadata["ocr_performed"] = True
        metadata["mean_confidence"] = ocr_res.get("mean_confidence", 0.0)
        metadata["extraction_method"] = "rapidocr_paddle_onnx"
        return ocr_res["full_text"], metadata

    elif ext in [".txt", ".text"]:
        metadata["ocr_performed"] = False
        metadata["extraction_method"] = "plain_text"
        return file_bytes.decode("utf-8", errors="ignore"), metadata

    else:
        raise ValueError(f"Unsupported file format '{ext}'. Supported: PDF, PNG, JPG, JPEG, WebP, TXT.")
