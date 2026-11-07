"""
CivicResolve AI - Document Upload & Intelligence API Endpoints
Validates mime types and file sizes, persists files securely, and runs OCR extraction.
"""
import os
import json
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Document, Complaint, CaseEvent, User
from backend.routes.auth import get_current_user
from agents.document_agent import process_document

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

if os.getenv("VERCEL") == "1" or (os.name != "nt" and os.path.exists("/tmp")):
    UPLOAD_DIR = "/tmp/uploads"
else:
    UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads")

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB


@router.post("/upload")
async def upload_document(
    complaint_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Associated complaint not found.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension '{ext}'. Only PDF, PNG, JPG, and JPEG files are supported."
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of 15 MB."
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    storage_path = os.path.join(UPLOAD_DIR, f"{complaint_id}_{file.filename}")
    with open(storage_path, "wb") as f:
        f.write(file_bytes)

    # Run Document Intelligence processing
    doc_res = process_document(
        file_bytes=file_bytes,
        filename=file.filename,
        complaint_data={
            "merchant": complaint.merchant,
            "amount": complaint.amount
        }
    )

    doc_record = Document(
        complaint_id=complaint_id,
        filename=file.filename,
        file_type=ext.replace(".", ""),
        storage_reference=storage_path,
        document_type=doc_res.get("document_type", "supporting_document"),
        extracted_data=json.dumps(doc_res.get("extracted_fields", {}), ensure_ascii=False),
        validation_status=doc_res.get("validation_status", "pending"),
        confidence_score=doc_res.get("confidence_score", 0.0)
    )
    db.add(doc_record)

    event = CaseEvent(
        complaint_id=complaint_id,
        event_type="document_uploaded",
        description=f"Uploaded and processed '{file.filename}' (Type: {doc_res.get('document_type')})."
    )
    db.add(event)
    db.commit()
    db.refresh(doc_record)

    return {
        "document_id": doc_record.id,
        "filename": doc_record.filename,
        "document_type": doc_record.document_type,
        "validation_status": doc_record.validation_status,
        "confidence_score": doc_record.confidence_score,
        "extracted_fields": doc_res.get("extracted_fields"),
        "consistency_audit": doc_res.get("consistency_audit")
    }


@router.post("/{document_id}/extract")
def re_extract_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    if not os.path.exists(doc.storage_reference):
        raise HTTPException(status_code=404, detail="File binary not found in storage.")

    with open(doc.storage_reference, "rb") as f:
        file_bytes = f.read()

    doc_res = process_document(file_bytes=file_bytes, filename=doc.filename)
    doc.extracted_data = json.dumps(doc_res.get("extracted_fields", {}), ensure_ascii=False)
    doc.validation_status = doc_res.get("validation_status", "pending")
    doc.confidence_score = doc_res.get("confidence_score", 0.0)
    db.commit()

    return {
        "document_id": doc.id,
        "extracted_fields": doc_res.get("extracted_fields"),
        "confidence_score": doc.confidence_score
    }
