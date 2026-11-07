"""
CivicResolve AI - Complaint Service Layer
Bridges REST API endpoints and Database models with the Multi-Agent LangGraph Workflow.
"""
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from database.models import Complaint, Document, EvidenceSource, Approval, CaseEvent, User
from agents.supervisor import SupervisorAgent
from workflows.approval_workflow import process_user_approval

supervisor = SupervisorAgent()


def create_complaint_record(
    db: Session,
    user_id: str,
    category: str,
    description: str,
    merchant: Optional[str] = None,
    amount: Optional[float] = None,
    purchase_date: Optional[str] = None,
    requested_resolution: Optional[str] = None
) -> Complaint:
    """Initializes a new complaint entry and logs creation event."""
    complaint = Complaint(
        user_id=user_id,
        category=category,
        description=description,
        merchant=merchant,
        amount=amount,
        purchase_date=purchase_date,
        requested_resolution=requested_resolution,
        status="draft"
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    # Log event
    event = CaseEvent(
        complaint_id=complaint.id,
        event_type="complaint_created",
        description=f"Complaint initialized in category '{category}'."
    )
    db.add(event)
    db.commit()

    return complaint


def run_complaint_analysis(
    db: Session,
    complaint_id: str,
    user_overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executes the 7-agent supervisor pipeline for a complaint in the database.
    Stores extracted evidence sources, resolution plan, and drafts in database.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise ValueError(f"Complaint {complaint_id} not found.")

    # Collect existing documents
    db_docs = db.query(Document).filter(Document.complaint_id == complaint_id).all()
    uploaded_files = []
    for d in db_docs:
        if os.path.exists(d.storage_reference):
            with open(d.storage_reference, "rb") as f:
                uploaded_files.append({
                    "filename": d.filename,
                    "bytes": f.read()
                })

    # Run multi-agent pipeline
    overrides = {
        "merchant": complaint.merchant,
        "amount": complaint.amount,
        "purchase_date": complaint.purchase_date,
        "requested_resolution": complaint.requested_resolution,
        **(user_overrides or {})
    }

    result = supervisor.run_full_pipeline(
        complaint_description=complaint.description,
        uploaded_files=uploaded_files,
        user_overrides=overrides
    )

    # Update database record
    complaint.category = result["complaint"].get("category", complaint.category)
    complaint.merchant = result["complaint"].get("merchant") or complaint.merchant
    complaint.amount = result["complaint"].get("amount") or complaint.amount
    complaint.purchase_date = result["complaint"].get("purchase_date") or complaint.purchase_date
    complaint.jurisdiction = result["rights"].get("jurisdiction")
    complaint.status = result.get("status", "ready_for_review")
    complaint.draft_complaint_en = result["action_package"].get("official_complaint_draft")
    complaint.resolution_plan = json.dumps(result["resolution_plan"], ensure_ascii=False)

    # Persist evidence sources
    for cit in result["rights"].get("citations", []):
        src = EvidenceSource(
            complaint_id=complaint.id,
            source_title=cit.get("title", "Official Source"),
            source_url=cit.get("source_url", ""),
            source_date=cit.get("source_date"),
            snippet=cit.get("snippet"),
            relevance_score=cit.get("confidence_score", 1.0)
        )
        db.add(src)

    # Log event
    event = CaseEvent(
        complaint_id=complaint.id,
        event_type="multi_agent_analysis_completed",
        description=f"7 agents completed analysis. Verification status: {result['verification'].get('overall_status')}."
    )
    db.add(event)
    db.commit()
    db.refresh(complaint)

    return result


def record_approval_action(
    db: Session,
    complaint_id: str,
    approved: bool,
    user_notes: Optional[str] = None,
    action_type: str = "official_submission"
) -> Dict[str, Any]:
    """Records formal user authorization in database and updates case status."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise ValueError(f"Complaint {complaint_id} not found.")

    res = process_user_approval(
        complaint_id=complaint_id,
        approved=approved,
        user_notes=user_notes,
        action_type=action_type
    )

    approval_rec = Approval(
        complaint_id=complaint_id,
        action_type=action_type,
        approved=approved,
        user_notes=user_notes,
        action_result=json.dumps(res, ensure_ascii=False)
    )
    db.add(approval_rec)

    if approved:
        complaint.status = "approved"
        desc = "User explicitly approved official complaint submission."
    else:
        complaint.status = "draft"
        desc = "User rejected current complaint draft."

    event = CaseEvent(
        complaint_id=complaint.id,
        event_type="user_approval_decision",
        description=desc
    )
    db.add(event)
    db.commit()

    return res
