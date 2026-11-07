"""
CivicResolve AI - Interactive AI Assistant Chat Endpoint
Supports direct conversational complaint processing, multi-agent status reporting, and citations.
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import User
from backend.routes.auth import get_current_user
from agents.supervisor import SupervisorAgent
from languages.i18n import t

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])
supervisor = SupervisorAgent()


class ChatMessageRequest(BaseModel):
    message: str
    language: Optional[str] = "en"
    complaint_id: Optional[str] = None
    voice_input: Optional[bool] = False


class ChatMessageResponse(BaseModel):
    reply_text: str
    complaint_category: str
    confidence: float
    jurisdiction: str
    next_step: str
    follow_up_questions: List[str]
    citations: List[Dict[str, Any]]
    agent_logs: List[Dict[str, Any]]
    action_package: Optional[Dict[str, Any]] = None


@router.post("", response_model=ChatMessageResponse)
def handle_chat_message(
    req: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    text = req.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Run multi-agent orchestration
    pipeline_result = supervisor.run_full_pipeline(
        complaint_description=text,
        uploaded_files=None,
        user_overrides=None
    )

    complaint = pipeline_result["complaint"]
    rights = pipeline_result["rights"]
    verification = pipeline_result["verification"]
    plan = pipeline_result["resolution_plan"]
    action_pkg = pipeline_result["action_package"]

    # Construct synthesized conversational reply
    reply = (
        f"I have reviewed your problem regarding {complaint.get('category_label', 'your consumer issue')}. "
        f"Under UAE Federal Law No. 15 of 2020 and Dubai Consumer Protection directives, "
        f"this matter falls under the jurisdiction of the {rights.get('primary_authority')}.\n\n"
        f"Summary of Assessment:\n"
        f"• Merchant: {complaint.get('merchant') or 'Identified in complaint'}\n"
        f"• Transaction Amount: AED {complaint.get('amount') or 0:,.2f}\n"
        f"• Recommended Next Action: {rights.get('applicable_procedure')}\n\n"
        f"Our 7 agents have drafted a formal merchant demand letter and official filing dossier for you to review."
    )

    return {
        "reply_text": reply,
        "complaint_category": complaint.get("category", "other"),
        "confidence": complaint.get("confidence", 0.0),
        "jurisdiction": rights.get("jurisdiction", "Dubai Emirate"),
        "next_step": pipeline_result.get("next_step", "review"),
        "follow_up_questions": pipeline_result.get("follow_up_questions", []),
        "citations": rights.get("citations", []),
        "agent_logs": pipeline_result.get("agent_logs", []),
        "action_package": action_pkg
    }
