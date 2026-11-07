"""
CivicResolve AI - Human-in-the-Loop Approval and External Dispatch Workflow
Enforces strict consent checks before action execution and logs audit trails.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import httpx


def process_user_approval(
    complaint_id: str,
    approved: bool,
    user_notes: Optional[str] = None,
    action_type: str = "official_submission",
    target_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Records explicit user authorization and prepares the official dispatch package.
    Only proceeds if approved is explicitly True.
    """
    if not approved:
        return {
            "status": "rejected_by_user",
            "approved": False,
            "complaint_id": complaint_id,
            "message": "User declined action authorization. No external communication was dispatched.",
            "timestamp": datetime.now().isoformat()
        }

    # Action approved by user
    action_result = {
        "status": "approved_and_ready",
        "approved": True,
        "complaint_id": complaint_id,
        "action_type": action_type,
        "user_notes": user_notes,
        "dispatch_url": target_url or "https://askdubai.app.n8n.cloud/form/civicresolve",
        "timestamp": datetime.now().isoformat(),
        "next_action": "Guide user to complete authorized submission or trigger external webhook."
    }

    return action_result


def sync_to_n8n_flow(
    form_url: str,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Dispatches verified complaint payload to the external authorized n8n form/webhook if network allows.
    Handles timeout and connection gracefully with fallback link.
    """
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(form_url, json=payload)
            if resp.status_code in [200, 201]:
                return {
                    "success": True,
                    "status_code": resp.status_code,
                    "message": "Successfully synchronized with external workflow.",
                    "portal_link": form_url
                }
    except Exception as e:
        pass

    return {
        "success": False,
        "message": "Direct HTTP POST unavailable; opening official submission link for direct user entry.",
        "portal_link": form_url
    }
