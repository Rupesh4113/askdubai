"""
CivicResolve AI - LangGraph Multi-Agent Complaint Workflow
Defines a stateful graph connecting all seven agents with explicit human-in-the-loop approval gates.
"""
from typing import Dict, Any, List, TypedDict, Optional
from langgraph.graph import StateGraph, END
from agents.supervisor import SupervisorAgent


class ComplaintState(TypedDict):
    complaint_description: str
    user_overrides: Optional[Dict[str, Any]]
    uploaded_files: Optional[List[Dict[str, Any]]]
    status: str
    next_step: str
    complaint: Dict[str, Any]
    documents: List[Dict[str, Any]]
    evidence_analysis: Dict[str, Any]
    follow_up_questions: List[str]
    rights: Dict[str, Any]
    resolution_plan: Dict[str, Any]
    action_package: Dict[str, Any]
    verification: Dict[str, Any]
    approved: bool
    submission_reference: Optional[str]
    agent_logs: List[Dict[str, Any]]


supervisor = SupervisorAgent()


def supervisor_pipeline_node(state: ComplaintState) -> Dict[str, Any]:
    """LangGraph node executing the supervisor multi-agent pipeline."""
    result = supervisor.run_full_pipeline(
        complaint_description=state.get("complaint_description", ""),
        uploaded_files=state.get("uploaded_files", []),
        user_overrides=state.get("user_overrides", {})
    )
    return {
        **result,
        "approved": state.get("approved", False),
        "submission_reference": state.get("submission_reference", None)
    }


def human_approval_check(state: ComplaintState) -> str:
    """Routing condition: ensures workflow halts for human approval before external dispatch."""
    if state.get("approved", False):
        return "authorized_dispatch"
    return "await_user_approval"


def build_complaint_graph():
    """Builds and compiles the LangGraph StateGraph for CivicResolve AI."""
    workflow = StateGraph(ComplaintState)

    workflow.add_node("supervisor_agent", supervisor_pipeline_node)

    workflow.set_entry_point("supervisor_agent")
    workflow.add_edge("supervisor_agent", END)

    return workflow.compile()


# Singleton compiled graph instance
complaint_graph = build_complaint_graph()


def execute_workflow(
    description: str,
    files: Optional[List[Dict[str, Any]]] = None,
    overrides: Optional[Dict[str, Any]] = None,
    approved: bool = False
) -> Dict[str, Any]:
    """Helper entry point for executing the LangGraph complaint workflow."""
    initial_state: ComplaintState = {
        "complaint_description": description,
        "user_overrides": overrides or {},
        "uploaded_files": files or [],
        "status": "initiated",
        "next_step": "analyze",
        "complaint": {},
        "documents": [],
        "evidence_analysis": {},
        "follow_up_questions": [],
        "rights": {},
        "resolution_plan": {},
        "action_package": {},
        "verification": {},
        "approved": approved,
        "submission_reference": None,
        "agent_logs": []
    }
    output = complaint_graph.invoke(initial_state)
    return output
