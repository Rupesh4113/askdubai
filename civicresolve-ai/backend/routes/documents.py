"""
CivicResolve AI - Document Intelligence API Endpoints
Handles document uploads, multi-page previews, field extraction, manual field editing,
and exports in JSON, CSV, Excel (.xlsx), and PDF formats.

Architecture:
- High-Performance Hybrid: Offloads heavyweight OCR (PaddleOCR, PyMuPDF, OpenCV)
  to dedicated microservice when DOCUMENT_SERVICE_URL is configured.
- Resilient Serverless Fallback: Runs pure-Python extraction and mathematical validation
  natively in lightweight environments (Vercel Lambda) without oversized C++ packages.
"""
import os
import json
import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Document, Complaint, CaseEvent, User
from backend.routes.auth import get_current_user
from document_processing.financial_validator import validate_financial_calculations
from document_processing.vat_validator import assess_uae_vat_compliance

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

DOCUMENT_SERVICE_URL = os.getenv("DOCUMENT_SERVICE_URL", "").rstrip("/")

if os.getenv("VERCEL") == "1" or (os.name != "nt" and os.path.exists("/tmp")):
    UPLOAD_DIR = "/tmp/uploads"
else:
    UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads")

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt"}
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB

# In-memory document and preview cache
_LOCAL_DOC_CACHE: Dict[str, Dict[str, Any]] = {}
_LOCAL_PREVIEW_CACHE: Dict[str, Dict[int, bytes]] = {}


@router.post("/upload")
async def upload_document(
    complaint_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Uploads and processes tax invoices, warranty cards, receipts, or other evidence documents.
    Extracts all fields across Sections A through H, validates mathematics and UAE VAT compliance.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported formats: PDF, PNG, JPG, JPEG, WebP, TXT."
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File exceeds maximum allowed size of 15 MB."
        )

    complaint = None
    complaint_data = None
    if complaint_id:
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if complaint:
            complaint_data = {
                "merchant": complaint.merchant,
                "amount": complaint.amount
            }
    if not complaint:
        complaint = db.query(Complaint).filter(Complaint.id == "standalone_documents").first()
        if not complaint:
            complaint = Complaint(
                id="standalone_documents",
                user_id=current_user.id,
                title="Standalone Document Intelligence Analysis",
                description="Document Intelligence standalone evidence upload session.",
                category="general_consumer_complaint",
                merchant="Commercial Establishment",
                amount=0.0,
                status="draft"
            )
            db.add(complaint)
            db.commit()
            db.refresh(complaint)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    storage_filename = f"{complaint_id or 'standalone'}_{uuid_short()}_{file.filename}"
    storage_path = os.path.join(UPLOAD_DIR, storage_filename)
    try:
        with open(storage_path, "wb") as f:
            f.write(file_bytes)
    except OSError:
        # Fallback for read-only filesystem environments
        storage_path = f"/tmp/{storage_filename}"

    # Execution Stage: Remote Processing Service -> Local Heavy -> Lightweight Fallback
    doc_res = None

    # Option 1: Offload to Dedicated Docker Document Intelligence Service
    if DOCUMENT_SERVICE_URL:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                files_payload = {"file": (file.filename, file_bytes, file.content_type or "application/octet-stream")}
                data_payload = {}
                if complaint_data:
                    data_payload["complaint_data"] = json.dumps(complaint_data)
                resp = await client.post(
                    f"{DOCUMENT_SERVICE_URL}/api/v1/documents/process",
                    files=files_payload,
                    data=data_payload
                )
                if resp.status_code == 200:
                    doc_res = resp.json()
        except Exception as e:
            print(f"[Document Proxy] Microservice connection notice: {e}. Falling back to internal engine.")

    # Option 2: Local Full Pipeline (PyMuPDF / OpenCV / RapidOCR if installed)
    if doc_res is None:
        try:
            from document_processing.document_upload import process_uploaded_document
            doc_res = process_uploaded_document(
                file_bytes=file_bytes,
                filename=file.filename,
                complaint_data=complaint_data
            )
        except Exception:
            # Option 3: Resilient Pure-Python Lightweight Extractor (Vercel Lambda Safe)
            from document_processing.lightweight_extractor import extract_lightweight_intelligence
            doc_res = extract_lightweight_intelligence(
                file_bytes=file_bytes,
                filename=file.filename,
                complaint_data=complaint_data
            )

    # Cache locally
    _LOCAL_DOC_CACHE[doc_res["document_id"]] = doc_res

    doc_record = Document(
        id=doc_res["document_id"],
        complaint_id=complaint.id if complaint else None,
        filename=file.filename,
        file_type=ext.replace(".", ""),
        storage_reference=storage_path,
        document_type=doc_res.get("document_type", "supporting_document"),
        extracted_data=json.dumps(doc_res, ensure_ascii=False),
        validation_status=doc_res.get("validation_status", "pending"),
        confidence_score=doc_res.get("confidence_score", 0.0)
    )
    db.add(doc_record)

    if complaint:
        event = CaseEvent(
            complaint_id=complaint.id,
            event_type="document_uploaded",
            description=f"Uploaded and extracted '{file.filename}' ({doc_res.get('type_display')})."
        )
        db.add(event)

    db.commit()
    db.refresh(doc_record)

    # Build page preview URLs
    page_count = doc_res.get("page_count", 1)
    preview_urls = [
        f"/api/v1/documents/{doc_record.id}/page/{p}/image"
        for p in range(1, page_count + 1)
    ]

    return {
        "document_id": doc_record.id,
        "filename": doc_record.filename,
        "document_type": doc_record.document_type,
        "type_display": doc_res.get("type_display"),
        "compliance_classification": doc_res.get("compliance_classification"),
        "validation_status": doc_record.validation_status,
        "confidence_score": doc_record.confidence_score,
        "page_count": page_count,
        "preview_urls": preview_urls,
        "extracted_fields": doc_res.get("extracted_fields"),
        "extracted_intelligence": doc_res.get("extracted_intelligence"),
        "consistency_audit": doc_res.get("consistency_audit"),
        "duplicate_audit": doc_res.get("duplicate_audit")
    }


@router.get("/{document_id}")
def get_document_details(
    document_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves full extraction records and analysis for a given document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        if document_id in _LOCAL_DOC_CACHE:
            return _LOCAL_DOC_CACHE[document_id]
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        data = json.loads(doc.extracted_data or "{}")
        return data
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse document extraction payload.")


@router.get("/{document_id}/page/{page_number}/image")
async def get_page_preview_image(
    document_id: str,
    page_number: int = 1
):
    """Serves rendered PNG image of a document page for visual inspection."""
    # Check remote microservice
    if DOCUMENT_SERVICE_URL:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{DOCUMENT_SERVICE_URL}/api/v1/documents/{document_id}/page/{page_number}/image")
                if resp.status_code == 200:
                    return Response(content=resp.content, media_type="image/png")
        except Exception:
            pass

    # Check local heavy processor cache
    try:
        from document_processing.document_upload import get_cached_page_preview
        png_bytes = get_cached_page_preview(document_id, page_number)
        if png_bytes:
            return Response(content=png_bytes, media_type="image/png")
    except Exception:
        pass

    # Transparent 1x1 PNG fallback for serverless preview placeholder
    transparent_png = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4'
        b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return Response(content=transparent_png, media_type="image/png")


@router.get("/{document_id}/text")
def get_document_raw_text(
    document_id: str,
    db: Session = Depends(get_db)
):
    """Returns raw extracted text stream from document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        if document_id in _LOCAL_DOC_CACHE:
            raw_text = _LOCAL_DOC_CACHE[document_id].get("extracted_intelligence", {}).get("raw_text_stream", "")
            return {"document_id": document_id, "filename": _LOCAL_DOC_CACHE[document_id].get("filename", ""), "text": raw_text}
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        data = json.loads(doc.extracted_data or "{}")
        raw_text = data.get("extracted_intelligence", {}).get("raw_text_stream", "")
        return {"document_id": document_id, "filename": doc.filename, "text": raw_text}
    except Exception:
        return {"document_id": document_id, "filename": doc.filename, "text": ""}


@router.put("/{document_id}/fields")
def update_extracted_fields(
    document_id: str,
    updated_fields: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Allows user to edit extracted values (e.g. correct a typo in merchant, invoice number, or amounts),
    re-runs mathematical and VAT verification, and updates records.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        full_payload = json.loads(doc.extracted_data or "{}")
    except Exception:
        full_payload = {}

    intel = full_payload.get("extracted_intelligence", {})
    if "merchant_name" in updated_fields:
        intel.setdefault("merchant_information", {})["business_name"] = {
            "value": updated_fields["merchant_name"],
            "status": "VERIFIED (USER EDITED)",
            "confidence": 1.0
        }
    if "invoice_number" in updated_fields:
        intel.setdefault("invoice_information", {})["invoice_number"] = {
            "value": updated_fields["invoice_number"],
            "status": "VERIFIED (USER EDITED)",
            "confidence": 1.0
        }
    if "total_payable" in updated_fields:
        try:
            amt = float(updated_fields["total_payable"])
            intel.setdefault("financial_summary", {})["total_payable"] = {
                "value": amt,
                "status": "VERIFIED (USER EDITED)",
                "confidence": 1.0
            }
        except (ValueError, TypeError):
            pass

    # Re-run financial and VAT validation
    subtotal = intel.get("financial_summary", {}).get("subtotal", {}).get("value")
    vat_amt = intel.get("financial_summary", {}).get("vat_amount", {}).get("value")
    printed_tot = intel.get("financial_summary", {}).get("total_payable", {}).get("value")
    items = intel.get("product_service_details", [])

    new_fin_audit = validate_financial_calculations(
        subtotal=subtotal,
        vat_amount=vat_amt,
        vat_rate=5.0,
        discounts=0.0,
        additional_charges=0.0,
        printed_total=printed_tot,
        line_items=items
    )
    intel["financial_audit"] = new_fin_audit

    full_payload["extracted_intelligence"] = intel
    full_payload["validation_status"] = new_fin_audit["math_validation_status"]

    doc.extracted_data = json.dumps(full_payload, ensure_ascii=False)
    doc.validation_status = full_payload["validation_status"]
    db.commit()

    return {
        "document_id": doc.id,
        "message": "Fields successfully updated and mathematically audited.",
        "financial_audit": new_fin_audit
    }


@router.get("/{document_id}/export/json")
def download_export_json(document_id: str, db: Session = Depends(get_db)):
    """Downloads full document intelligence payload as JSON."""
    doc_payload = _get_doc_payload(document_id, db)
    json_str = json.dumps(doc_payload, indent=2, ensure_ascii=False)
    filename = f"{doc_payload.get('filename', 'invoice')}_intelligence.json"
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{document_id}/export/csv")
def download_export_csv(document_id: str, db: Session = Depends(get_db)):
    """Downloads extracted fields and line items as CSV."""
    doc_payload = _get_doc_payload(document_id, db)
    try:
        from document_processing.report_generator import export_document_csv
        csv_str = export_document_csv(doc_payload)
    except Exception:
        import csv
        import io
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["Field", "Value"])
        for k, v in doc_payload.get("extracted_fields", {}).items():
            w.writerow([k, v])
        csv_str = out.getvalue()

    filename = f"{doc_payload.get('filename', 'invoice')}_line_items.csv"
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{document_id}/export/excel")
async def download_export_excel(document_id: str, db: Session = Depends(get_db)):
    """Downloads structured multi-sheet Excel (.xlsx) workbook."""
    doc_payload = _get_doc_payload(document_id, db)

    # Proxy to microservice if configured
    if DOCUMENT_SERVICE_URL:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{DOCUMENT_SERVICE_URL}/api/v1/documents/export/excel",
                    json=doc_payload
                )
                if resp.status_code == 200:
                    filename = f"{doc_payload.get('filename', 'invoice')}_audit_report.xlsx"
                    return Response(
                        content=resp.content,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
                    )
        except Exception:
            pass

    try:
        from document_processing.report_generator import export_document_excel
        xlsx_bytes = export_document_excel(doc_payload)
        filename = f"{doc_payload.get('filename', 'invoice')}_audit_report.xlsx"
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception:
        # Fallback to CSV format with Excel MIME type
        from document_processing.report_generator import export_document_csv
        csv_str = export_document_csv(doc_payload)
        filename = f"{doc_payload.get('filename', 'invoice')}_audit_report.csv"
        return Response(
            content=csv_str.encode("utf-8"),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )


@router.get("/{document_id}/export/pdf")
async def download_export_pdf(document_id: str, db: Session = Depends(get_db)):
    """Downloads formal Executive Evidence Intelligence Audit PDF Report."""
    doc_payload = _get_doc_payload(document_id, db)

    # Proxy to microservice if configured
    if DOCUMENT_SERVICE_URL:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{DOCUMENT_SERVICE_URL}/api/v1/documents/export/pdf",
                    json=doc_payload
                )
                if resp.status_code == 200:
                    filename = f"{doc_payload.get('filename', 'invoice')}_evidence_report.pdf"
                    return Response(
                        content=resp.content,
                        media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
                    )
        except Exception:
            pass

    try:
        from document_processing.report_generator import export_document_pdf
        pdf_bytes = export_document_pdf(doc_payload)
        filename = f"{doc_payload.get('filename', 'invoice')}_evidence_report.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception:
        # Fallback: HTML Evidence Audit Document
        html_content = f"""<!DOCTYPE html>
<html>
<head><title>CivicResolve AI - Evidence Report</title>
<style>body{{font-family:Arial,sans-serif;padding:2rem;line-height:1.6;color:#1E293B}}h1{{color:#0F766E}}table{{width:100%;border-collapse:collapse;margin:1rem 0}}th,td{{border:1px solid #CBD5E1;padding:8px;text-align:left}}th{{background:#F1F5F9}}</style>
</head>
<body>
<h1>CivicResolve AI | Evidence Intelligence Report</h1>
<p><strong>Document ID:</strong> {doc_payload.get('document_id')}</p>
<p><strong>Filename:</strong> {doc_payload.get('filename')}</p>
<p><strong>Classification:</strong> {doc_payload.get('type_display')}</p>
<p><strong>Confidence:</strong> {int(doc_payload.get('confidence_score', 0)*100)}% ({doc_payload.get('validation_status')})</p>
<h3>Extracted Transaction Summary</h3>
<table>
<tr><th>Field</th><th>Value</th></tr>
<tr><td>Merchant</td><td>{doc_payload.get('extracted_fields', {}).get('merchant') or 'N/A'}</td></tr>
<tr><td>Invoice No</td><td>{doc_payload.get('extracted_fields', {}).get('invoice_number') or 'N/A'}</td></tr>
<tr><td>Date</td><td>{doc_payload.get('extracted_fields', {}).get('date') or 'N/A'}</td></tr>
<tr><td>Total (AED)</td><td>AED {doc_payload.get('extracted_fields', {}).get('amount') or '0.00'}</td></tr>
<tr><td>TRN</td><td>{doc_payload.get('extracted_fields', {}).get('trn') or 'N/A'}</td></tr>
</table>
<p><em>Generated under UAE Federal Law No. 15 of 2020 on Consumer Protection.</em></p>
</body></html>"""
        filename = f"{doc_payload.get('filename', 'invoice')}_evidence_report.html"
        return Response(
            content=html_content.encode("utf-8"),
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )


def _get_doc_payload(document_id: str, db: Session) -> Dict[str, Any]:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc and doc.extracted_data:
        try:
            return json.loads(doc.extracted_data)
        except Exception:
            pass
    if document_id in _LOCAL_DOC_CACHE:
        return _LOCAL_DOC_CACHE[document_id]
    raise HTTPException(status_code=404, detail="Document data not found.")


def uuid_short() -> str:
    return uuid.uuid4().hex[:6]
