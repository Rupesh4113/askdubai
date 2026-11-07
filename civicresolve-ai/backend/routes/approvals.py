"""
CivicResolve AI - Approvals REST API Endpoints
Enforces explicit human approval before any external action or complaint dispatch.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import User
from backend.routes.auth import get_current_user
from backend.services.complaint_service import record_approval_action

router = APIRouter(prefix="/api/v1/approvals", tags=["Approvals"])


class ApprovalRequestSchema(BaseModel):
    complaint_id: str
    approved: bool
    user_notes: Optional[str] = None
    action_type: Optional[str] = "official_submission"


@router.post("")
def submit_approval(
    req: ApprovalRequestSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        res = record_approval_action(
            db=db,
            complaint_id=req.complaint_id,
            approved=req.approved,
            user_notes=req.user_notes,
            action_type=req.action_type or "official_submission"
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
