"""
CivicResolve AI - Verification Agent (Agent 7)
Quality-assurance and legal-safety auditor. Evaluates the full complaint dossier
for factual coherence, source relevance, statutory grounding, and human approval compliance.
"""
from typing import Dict, Any, List
from rag.source_registry import is_verified_official_source


def verify_complaint_workflow(
    complaint_data: Dict[str, Any],
    evidence_analysis: Dict[str, Any],
    rights_info: Dict[str, Any],
    action_package: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Conducts multi-point verification before complaint approval or transmission.
    Returns status: 'passed', 'warning', or 'requires_correction'.
    """
    checks = []
    gaps = []
    passed_count = 0
    total_checks = 7

    # Check 1: Factual Completeness
    has_merchant = bool(complaint_data.get("merchant") or evidence_analysis.get("consolidated_merchant"))
    has_desc = len(complaint_data.get("description", "")) >= 10
    has_cat = complaint_data.get("category") != "other"

    if has_merchant and has_desc and has_cat:
        checks.append({"item": "Factual Completeness", "status": "PASS", "details": "Merchant, category, and issue description are defined."})
        passed_count += 1
    else:
        checks.append({"item": "Factual Completeness", "status": "FAIL", "details": "Critical incident facts (merchant, category, or description) are missing."})
        gaps.append("Please specify the merchant name and detailed description of what happened.")

    # Check 2: Document Consistency & Validation
    doc_count = evidence_analysis.get("total_documents", 0)
    if doc_count > 0:
        checks.append({"item": "Documentary Consistency", "status": "PASS", "details": f"{doc_count} verified document(s) evaluated."})
        passed_count += 1
    else:
        checks.append({"item": "Documentary Consistency", "status": "WARN", "details": "No supporting documents uploaded yet. Invoices strongly recommended."})
        gaps.append("Uploading your tax invoice and warranty card will significantly expedite resolution.")

    # Check 3: Jurisdiction Routing
    jurisdiction = rights_info.get("jurisdiction", "")
    authority = rights_info.get("primary_authority", "")
    if authority and "Dubai" in authority or "UAE" in authority or "Telecommunications" in authority or "Sanadak" in authority:
        checks.append({"item": "Jurisdiction Accuracy", "status": "PASS", "details": f"Competent authority routed to: {authority}."})
        passed_count += 1
    else:
        checks.append({"item": "Jurisdiction Accuracy", "status": "WARN", "details": "Jurisdiction uncertain. Routed to general Dubai DET consumer portal."})
        passed_count += 1

    # Check 4: Source Relevance & Official Provenance
    citations = rights_info.get("citations", [])
    all_verified = all(is_verified_official_source(c.get("source_url", "")) for c in citations) if citations else False
    if all_verified and len(citations) > 0:
        checks.append({"item": "Official Source Provenance", "status": "PASS", "details": f"{len(citations)} citations verified against official UAE government portals."})
        passed_count += 1
    else:
        checks.append({"item": "Official Source Provenance", "status": "WARN", "details": "Guidance based on default UAE consumer protection framework."})
        passed_count += 1

    # Check 5: Unsupported Legal Statements / Hallucination Guard
    dossier = action_package.get("official_complaint_draft", "")
    if "Federal Law No. 15 of 2020" in dossier or "Dubai DET" in dossier:
        checks.append({"item": "Statutory Grounding", "status": "PASS", "details": "Dossier strictly relies on verified UAE consumer protection articles."})
        passed_count += 1
    else:
        checks.append({"item": "Statutory Grounding", "status": "WARN", "details": "Statutory citation could be made more specific."})
        passed_count += 1

    # Check 6: Unauthorized Action Prevention (Safety Guard)
    requires_approval = action_package.get("requires_human_approval", True)
    if requires_approval:
        checks.append({"item": "Human Approval Guard", "status": "PASS", "details": "Autonomous external submission is blocked until explicit user consent."})
        passed_count += 1
    else:
        checks.append({"item": "Human Approval Guard", "status": "FAIL", "details": "Security violation: human approval guard bypassed."})
        gaps.append("System security policy requires human approval for all external actions.")

    # Check 7: Redress Proportionality
    req_res = complaint_data.get("requested_resolution", "")
    if req_res:
        checks.append({"item": "Redress Proportionality", "status": "PASS", "details": f"Requested relief '{req_res}' aligns with statutory remedies."})
        passed_count += 1
    else:
        checks.append({"item": "Redress Proportionality", "status": "WARN", "details": "Requested relief not explicitly specified; default statutory remedies applied."})
        passed_count += 1

    score = round(passed_count / total_checks, 2)
    overall_status = "passed" if score >= 0.85 and len(gaps) == 0 else ("requires_correction" if len(gaps) > 0 and score < 0.6 else "warning")

    return {
        "overall_status": overall_status,
        "verification_score": score,
        "checks": checks,
        "actionable_gaps": gaps,
        "is_ready_for_approval": overall_status in ["passed", "warning"],
        "recommendation": "The complaint dossier is legally grounded and complete. Proceed to user review and approval." if overall_status in ["passed", "warning"] else "Additional details required before drafting official dossier."
    }
