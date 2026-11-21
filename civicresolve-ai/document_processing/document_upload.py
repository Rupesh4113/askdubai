"""
CivicResolve AI - Document Upload & Pipeline Orchestration Service
Validates file types, manages page preview generation, runs end-to-end extraction,
and coordinates document deduplication.
"""
import os
import uuid
import json
from typing import Dict, Any, List, Optional
from PIL import Image
import io

from document_processing.pdf_processor import inspect_and_process_pdf, PDFProcessingError
from document_processing.image_preprocessor import preprocess_image_bytes
from document_processing.ocr_engine import run_ocr_on_image
from document_processing.document_classifier import classify_document
from document_processing.document_extractor import extract_all_document_intelligence
from document_processing.duplicate_detector import check_for_duplicate

ALLOWED_FORMATS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".txt"}
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB

# Global cache for rendered preview images: doc_id -> { page_num: png_bytes }
_PAGE_PREVIEWS_CACHE: Dict[str, Dict[int, bytes]] = {}
_ACTIVE_DOCUMENTS_CACHE: Dict[str, Dict[str, Any]] = {}


def process_uploaded_document(
    file_bytes: bytes,
    filename: str,
    complaint_data: Optional[Dict[str, Any]] = None,
    document_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    End-to-end Document Intelligence processing:
    1. Validation (format, size)
    2. Image/PDF parsing and multi-page preview extraction
    3. RapidOCR / native vector text extraction
    4. Document classification
    5. Deduplication check
    6. Master field extraction (Sections A-H)
    7. Multi-layer verification
    """
    doc_id = document_id or f"DOC-{uuid.uuid4().hex[:12].upper()}"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_FORMATS:
        raise ValueError(f"Unsupported file format '{ext}'. Supported: PDF, JPG, JPEG, PNG, WebP, TXT.")

    file_size = len(file_bytes)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValueError("File exceeds maximum allowed size of 15 MB.")

    pages_data = []
    raw_images = []
    _PAGE_PREVIEWS_CACHE[doc_id] = {}

    # 1. Processing pipeline branch based on format
    if ext == ".pdf":
        pdf_res = inspect_and_process_pdf(file_bytes)
        for p in pdf_res["pages"]:
            p_num = p["page_number"]
            _PAGE_PREVIEWS_CACHE[doc_id][p_num] = p["preview_png_bytes"]

            # If page is scanned or image-sparse, invoke RapidOCR on rendered image
            if p["is_scanned"]:
                ocr_p = run_ocr_on_image(p["preview_png_bytes"], page_number=p_num)
                p["tokens"] = ocr_p["tokens"]
                p["native_text"] = ocr_p["full_text"]
                p["ocr_performed"] = True
            else:
                p["tokens"] = p["words"]
                p["ocr_performed"] = False

            pages_data.append(p)

    elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
        # Image pipeline: preprocess and OCR
        enhanced_bgr, prep_meta = preprocess_image_bytes(file_bytes)
        raw_images.append(enhanced_bgr)

        # Convert enhanced image to PNG bytes for preview
        pil_preview = Image.fromarray(enhanced_bgr[:, :, ::-1])
        buf = io.BytesIO()
        pil_preview.save(buf, format="PNG")
        preview_png_bytes = buf.getvalue()
        _PAGE_PREVIEWS_CACHE[doc_id][1] = preview_png_bytes

        ocr_res = run_ocr_on_image(enhanced_bgr, page_number=1)
        pages_data.append({
            "page_number": 1,
            "width": prep_meta["original_width"],
            "height": prep_meta["original_height"],
            "native_text": ocr_res["full_text"],
            "tokens": ocr_res["tokens"],
            "tables": [],
            "is_scanned": True,
            "preview_png_bytes": preview_png_bytes,
            "preprocessing": prep_meta,
            "ocr_performed": True
        })

    elif ext == ".txt":
        text_content = file_bytes.decode("utf-8", errors="ignore")
        pages_data.append({
            "page_number": 1,
            "width": 800,
            "height": 1000,
            "native_text": text_content,
            "tokens": [],
            "tables": [],
            "is_scanned": False,
            "preview_png_bytes": None,
            "ocr_performed": False
        })

    # 2. Extract full text across pages
    pages_text = [p.get("native_text", "") for p in pages_data]
    full_text = "\n\n".join(pages_text)

    # 3. Document classification & multi-receipt detection
    class_info = classify_document(full_text, filename, pages_text)

    # 4. Master intelligence extraction (Sections A through H)
    extracted_intel = extract_all_document_intelligence(
        pages_data=pages_data,
        document_type_info=class_info,
        raw_images=raw_images
    )

    # 5. Duplicate Detection
    seller_name = extracted_intel["merchant_information"].get("business_name", {}).get("value")
    inv_no = extracted_intel["invoice_information"].get("invoice_number", {}).get("value")
    total_val = extracted_intel["financial_summary"].get("total_payable", {}).get("value")
    inv_date = extracted_intel["invoice_information"].get("invoice_date", {}).get("value")

    dup_audit = check_for_duplicate(
        file_bytes=file_bytes,
        merchant=seller_name,
        invoice_number=inv_no,
        amount=total_val,
        date=inv_date
    )

    # 6. Cross-reference with complaint data if available
    consistency_audit = []
    if complaint_data:
        stated_merchant = complaint_data.get("merchant")
        if stated_merchant and seller_name:
            if stated_merchant.lower() in seller_name.lower() or seller_name.lower() in stated_merchant.lower():
                consistency_audit.append(f"Merchant matched: '{seller_name}'.")
            else:
                consistency_audit.append(f"Discrepancy: User reported '{stated_merchant}', invoice states '{seller_name}'.")

        stated_amount = complaint_data.get("amount")
        if stated_amount and total_val:
            try:
                diff = abs(float(stated_amount) - float(total_val))
                if diff < 1.0:
                    consistency_audit.append(f"Amount confirmed: AED {total_val:.2f}.")
                else:
                    consistency_audit.append(f"Discrepancy: User reported AED {stated_amount}, document states AED {total_val}.")
            except Exception:
                pass

    result_payload = {
        "document_id": doc_id,
        "filename": filename,
        "file_size_bytes": file_size,
        "format": ext.replace(".", "").upper(),
        "page_count": len(pages_data),
        "status": "COMPLETED",
        "duplicate_audit": dup_audit,
        "document_type": class_info["document_type"],
        "type_display": class_info["type_display"],
        "compliance_classification": class_info["compliance_classification"],
        "contains_multiple_documents": class_info["contains_multiple_documents"],
        "validation_status": extracted_intel["accuracy_and_validation_report"]["overall_status"],
        "confidence_score": extracted_intel["accuracy_and_validation_report"]["overall_confidence"],
        "consistency_audit": consistency_audit,
        "extracted_intelligence": extracted_intel,
        # Backward-compatible convenience keys for existing agents/tests
        "extracted_fields": {
            "merchant": seller_name,
            "invoice_number": inv_no,
            "purchase_date": inv_date,
            "product_description": extracted_intel["product_service_details"][0]["product_name"] if extracted_intel["product_service_details"] else None,
            "amount": total_val,
            "currency": extracted_intel["financial_summary"].get("currency", {}).get("value") or "AED",
            "warranty_period": extracted_intel["warranty_after_sales_information"].get("warranty_duration", {}).get("value"),
            "trn": seller_trn_from_intel(extracted_intel),
            "confidence_score": extracted_intel["accuracy_and_validation_report"]["overall_confidence"],
            "missing_fields": [m["field_key"] for m in extracted_intel["missing_information"]]
        },
        "extracted_text_preview": full_text[:400] + ("..." if len(full_text) > 400 else ""),
        "is_authentic_claim": False,
        "ocr_performed": any(p.get("ocr_performed", False) for p in pages_data)
    }

    _ACTIVE_DOCUMENTS_CACHE[doc_id] = result_payload
    return result_payload


def get_cached_document(document_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves processed document result by ID."""
    return _ACTIVE_DOCUMENTS_CACHE.get(document_id)


def get_cached_page_preview(document_id: str, page_number: int = 1) -> Optional[bytes]:
    """Retrieves PNG bytes of a document page preview."""
    doc_pages = _PAGE_PREVIEWS_CACHE.get(document_id, {})
    return doc_pages.get(page_number)


def seller_trn_from_intel(intel: Dict[str, Any]) -> Optional[str]:
    trn_obj = intel.get("merchant_information", {}).get("trn")
    if isinstance(trn_obj, dict):
        return trn_obj.get("value")
    return trn_obj
