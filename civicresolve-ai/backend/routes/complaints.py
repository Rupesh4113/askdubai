"""
CivicResolve AI - Complaints REST API Endpoints
Manages complaint lifecycle, multi-agent analysis invocations, and case history.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Complaint, CaseEvent, User
from backend.routes.auth import get_current_user
from backend.services.complaint_service import create_complaint_record, run_complaint_analysis

router = APIRouter(prefix="/api/v1/complaints", tags=["Complaints"])


class ComplaintCreateSchema(BaseModel):
    category: Optional[str] = "defective_product"
    description: str
    merchant: Optional[str] = None
    amount: Optional[float] = None
    purchase_date: Optional[str] = None
    requested_resolution: Optional[str] = None


class ComplaintEventCreateSchema(BaseModel):
    event_type: str
    description: str


@router.post("")
def create_complaint(
    req: ComplaintCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    complaint = create_complaint_record(
        db=db,
        user_id=current_user.id,
        category=req.category,
        description=req.description,
        merchant=req.merchant,
        amount=req.amount,
        purchase_date=req.purchase_date,
        requested_resolution=req.requested_resolution
    )
    return {
        "id": complaint.id,
        "status": complaint.status,
        "category": complaint.category,
        "merchant": complaint.merchant,
        "amount": complaint.amount,
        "created_at": complaint.created_at.isoformat()
    }


@router.get("")
def list_complaints(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    complaints = db.query(Complaint).filter(Complaint.user_id == current_user.id).order_by(Complaint.created_at.desc()).all()
    return [
        {
            "id": c.id,
            "category": c.category,
            "merchant": c.merchant,
            "amount": c.amount,
            "status": c.status,
            "submission_reference": c.submission_reference,
            "created_at": c.created_at.isoformat()
        }
        for c in complaints
    ]


@router.get("/{complaint_id}")
def get_complaint(
    complaint_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    events = [
        {"event_type": e.event_type, "description": e.description, "created_at": e.created_at.isoformat()}
        for e in c.case_events
    ]
    docs = [
        {"id": d.id, "filename": d.filename, "document_type": d.document_type, "validation_status": d.validation_status}
        for d in c.documents
    ]
    sources = [
        {"title": s.source_title, "url": s.source_url, "snippet": s.snippet}
        for s in c.evidence_sources
    ]

    return {
        "id": c.id,
        "category": c.category,
        "description": c.description,
        "merchant": c.merchant,
        "amount": c.amount,
        "currency": c.currency,
        "purchase_date": c.purchase_date,
        "requested_resolution": c.requested_resolution,
        "jurisdiction": c.jurisdiction,
        "status": c.status,
        "submission_reference": c.submission_reference,
        "draft_complaint_en": c.draft_complaint_en,
        "documents": docs,
        "evidence_sources": sources,
        "events": events,
        "created_at": c.created_at.isoformat()
    }


@router.post("/{complaint_id}/analyze")
def trigger_analysis(
    complaint_id: str,
    user_overrides: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = run_complaint_analysis(db, complaint_id, user_overrides)
        return {
            "complaint_id": complaint_id,
            "status": result["status"],
            "verification": result["verification"],
            "resolution_plan": result["resolution_plan"],
            "action_package": result["action_package"],
            "agent_logs": result["agent_logs"]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{complaint_id}/events")
def add_case_event(
    complaint_id: str,
    req: ComplaintEventCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    event = CaseEvent(
        complaint_id=c.id,
        event_type=req.event_type,
        description=req.description
    )
    db.add(event)
    db.commit()
    return {"status": "event_recorded", "event_type": req.event_type}
