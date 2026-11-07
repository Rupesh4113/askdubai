"""
CivicResolve AI - Supervisor Agent (Agent 1)
Central orchestrator of the multi-agent system.
Coordinates the specialist agents, tracks workflow state, enforces validation gates,
and mandates explicit human authorization before external submission.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from agents.complaint_agent import classify_complaint
from agents.document_agent import process_document, analyze_evidence_package
from agents.rights_agent import research_official_rights
from agents.resolution_agent import generate_resolution_plan
from agents.action_agent import prepare_action_package
from agents.verification_agent import verify_complaint_workflow


class SupervisorAgent:
    """
    Supervisor Agent coordinating the 6 specialist agents:
    - Agent 2: Complaint Classification Agent
    - Agent 3: Document Intelligence Agent
    - Agent 4: Official Rights Research Agent
    - Agent 5: Resolution Planning Agent
    - Agent 6: Action Agent
    - Agent 7: Verification Agent
    """

    def __init__(self):
        self.agent_name = "Supervisor Agent"

    def run_full_pipeline(
        self,
        complaint_description: str,
        uploaded_files: Optional[List[Dict[str, Any]]] = None,
        user_overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes the multi-agent orchestration pipeline across all specialist agents.
        Returns a comprehensive state object ready for frontend rendering and database storage.
        """
        logs = []
        def log_step(agent: str, action: str):
            logs.append({
                "timestamp": datetime.now().isoformat(),
                "agent": agent,
                "action": action
            })

        log_step(self.agent_name, "Initiating multi-agent complaint resolution pipeline.")

        # STEP 1: Understand problem & classify (Agent 2)
        log_step("Complaint Classification Agent", "Analyzing problem text and extracting transaction entities.")
        classification = classify_complaint(complaint_description)
        if user_overrides:
            for k, v in user_overrides.items():
                if v is not None and v != "":
                    classification[k] = v

        log_step("Complaint Classification Agent", f"Classified category as '{classification.get('category')}' with confidence {classification.get('confidence')}.")

        # STEP 2: Document Intelligence (Agent 3)
        processed_docs = []
        if uploaded_files:
            log_step("Document Intelligence Agent", f"Processing {len(uploaded_files)} supporting document(s).")
            for item in uploaded_files:
                p_doc = process_document(
                    file_bytes=item["bytes"],
                    filename=item["filename"],
                    complaint_data=classification
                )
                processed_docs.append(p_doc)
        else:
            log_step("Document Intelligence Agent", "No documents uploaded; proceeding with statement-level analysis.")

        evidence_analysis = analyze_evidence_package(
            category=classification.get("category", "other"),
            processed_documents=processed_docs
        )

        # Merge extracted document entities if missing in complaint text
        if not classification.get("merchant") and evidence_analysis.get("consolidated_merchant"):
            classification["merchant"] = evidence_analysis["consolidated_merchant"]
        if not classification.get("amount") and evidence_analysis.get("consolidated_amount"):
            classification["amount"] = evidence_analysis["consolidated_amount"]
        if not classification.get("purchase_date") and evidence_analysis.get("consolidated_date"):
            classification["purchase_date"] = evidence_analysis["consolidated_date"]

        # Follow-up questions generation if key information is missing
        follow_up_questions = self._determine_follow_up_questions(classification, evidence_analysis)

        # STEP 3: Official Rights Research (Agent 4)
        log_step("Official Rights Research Agent", "Querying official UAE & Dubai legal knowledge base (FAISS RAG).")
        rights_info = research_official_rights(classification)
        log_step("Official Rights Research Agent", f"Identified competent jurisdiction: {rights_info.get('jurisdiction')} ({rights_info.get('primary_authority')}).")

        # STEP 4: Resolution Planning (Agent 5)
        log_step("Resolution Planning Agent", "Formulating structured 4-step consumer resolution roadmap.")
        resolution_plan = generate_resolution_plan(
            complaint_data=classification,
            evidence_analysis=evidence_analysis,
            rights_info=rights_info
        )

        # STEP 5: Action Preparation (Agent 6)
        log_step("Action Agent", "Generating official complaint dossier and formal merchant demand letter.")
        action_package = prepare_action_package(
            complaint_data=classification,
            evidence_analysis=evidence_analysis,
            rights_info=rights_info,
            resolution_plan=resolution_plan
        )

        # STEP 6: Verification & Safety Audit (Agent 7)
        log_step("Verification Agent", "Auditing dossier completeness, legal grounding, and human approval gates.")
        verification_result = verify_complaint_workflow(
            complaint_data=classification,
            evidence_analysis=evidence_analysis,
            rights_info=rights_info,
            action_package=action_package
        )
        log_step("Verification Agent", f"Audit completed. Status: {verification_result.get('overall_status')} (Score: {verification_result.get('verification_score')}).")

        # Determine next appropriate step
        if verification_result.get("overall_status") == "requires_correction":
            next_step = "request_additional_information"
            status = "incomplete"
        else:
            next_step = "awaiting_user_approval"
            status = "ready_for_review"

        log_step(self.agent_name, f"Pipeline workflow synchronized. Next step: {next_step}.")

        return {
            "status": status,
            "next_step": next_step,
            "complaint": classification,
            "documents": processed_docs,
            "evidence_analysis": evidence_analysis,
            "follow_up_questions": follow_up_questions,
            "rights": rights_info,
            "resolution_plan": resolution_plan,
            "action_package": action_package,
            "verification": verification_result,
            "agent_logs": logs
        }

    def _determine_follow_up_questions(self, complaint: Dict[str, Any], evidence: Dict[str, Any]) -> List[str]:
        questions = []
        if not complaint.get("merchant"):
            questions.append("What is the registered name of the store, company, or online platform where you made the purchase?")
        if not complaint.get("amount"):
            questions.append("What was the exact purchase or transaction amount in UAE Dirhams (AED)?")
        if not complaint.get("purchase_date"):
            questions.append("On what date did you purchase the item or receive the service?")
        if not complaint.get("requested_resolution"):
            questions.append("What is your preferred resolution (e.g., immediate product replacement, full refund, or free authorized repair)?")
        if evidence.get("total_documents", 0) == 0:
            questions.append("Do you have a copy of the tax invoice, receipt, or warranty certificate to upload?")
        return questions
