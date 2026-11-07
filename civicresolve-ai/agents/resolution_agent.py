"""
CivicResolve AI - Resolution Planning Agent (Agent 5)
Synthesizes facts, documentary evidence, and statutory rights into an actionable,
structured step-by-step consumer resolution roadmap.
"""
from typing import Dict, Any, List


def generate_resolution_plan(
    complaint_data: Dict[str, Any],
    evidence_analysis: Dict[str, Any],
    rights_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Constructs an authoritative, transparent resolution roadmap.
    Explicitly articulates facts, evidence gaps, jurisdiction, next steps, and alternative remedies.
    """
    category = complaint_data.get("category", "defective_product")
    merchant = complaint_data.get("merchant") or evidence_analysis.get("consolidated_merchant") or "the merchant"
    amount = complaint_data.get("amount") or evidence_analysis.get("consolidated_amount")
    amount_str = f"AED {amount:,.2f}" if amount else "the invoiced amount"
    desc = complaint_data.get("description", "")
    requested_res = complaint_data.get("requested_resolution") or "Repair, Replacement or Full Refund"

    # 1. What happened
    what_happened = (
        f"The consumer encountered a dispute regarding {complaint_data.get('category_label', category)} "
        f"with merchant '{merchant}' for a purchase valued at {amount_str}. "
        f"Core issue reported: {desc[:250]}."
    )

    # 2. What information is available
    available_info = [
        f"Problem Category: {complaint_data.get('category_label', category)}",
        f"Merchant / Retailer: {merchant}",
        f"Stated Transaction Amount: {amount_str}",
        f"Stated Purchase Date: {complaint_data.get('purchase_date', 'Not specified')}",
        f"Requested Redress: {requested_res}",
        f"Attached Supporting Documents: {evidence_analysis.get('total_documents', 0)} file(s)"
    ]

    # 3. What evidence is missing
    missing_evidence = evidence_analysis.get("missing_evidence", [])
    if not missing_evidence:
        missing_evidence = ["All primary statutory evidence items appear to be provided."]

    # 4. Responsible Authority
    responsible_authority = {
        "name": rights_info.get("primary_authority", "Dubai Department of Economy and Tourism (DET)"),
        "jurisdiction": rights_info.get("jurisdiction", "Dubai Emirate"),
        "portal_url": rights_info.get("official_portal_url", "https://consumerrights.gov.ae/"),
        "legal_basis": rights_info.get("legal_basis", "UAE Federal Law No. 15 of 2020 on Consumer Protection")
    }

    # 5. What the consumer should do next (Sequenced Action Plan)
    action_steps = [
        {
            "step": 1,
            "title": "Issue Formal Written Cure Notice to Merchant",
            "timeline": "Immediate (allow 48 to 72 hours for merchant response)",
            "description": f"Send the CivicResolve-generated formal notification to {merchant} demanding {requested_res} under UAE Federal Law No. 15 of 2020.",
            "deliverable": "Merchant Demand Letter / Email Draft"
        },
        {
            "step": 2,
            "title": "Review & Approve CivicResolve Official Complaint Pack",
            "timeline": "Within 24 hours",
            "description": "Verify extracted facts, ensure all invoices and photos are attached, and give explicit user authorization.",
            "deliverable": "Verified Consumer Dossier"
        },
        {
            "step": 3,
            "title": "Lodge Complaint with Dubai DED (Consumer Rights)",
            "timeline": "Upon merchant non-response or expiration of notice",
            "description": f"Submit dossier via {responsible_authority['portal_url']} or through the Dubai Consumer App (Call center: 600 545555).",
            "deliverable": "Official Government Reference Number"
        },
        {
            "step": 4,
            "title": "Track Mediation and Record Outcome",
            "timeline": "4 to 14 business days",
            "description": "Log the official reference number in CivicResolve AI to activate automated milestone alerts and mediation tracking.",
            "deliverable": "Case Closure / Mediation Accord"
        }
    ]

    # 6. Alternative remedies
    alternatives = [
        {
            "option": "Credit Card Chargeback (Bank Dispute)",
            "condition": "Applicable if payment was completed via credit card and goods were defective or undelivered and merchant refuses refund.",
            "action": "Contact issuing UAE bank within 60 to 120 days from transaction date citing 'Goods Defective / Not as Described'."
        },
        {
            "option": "Free Zone Mediation (if merchant registered in Free Zone)",
            "condition": "Applicable if merchant holds trade license in DIFC, DMCC, or DAFZA.",
            "action": "Lodge parallel complaint with the respective Free Zone Consumer Protection Bureau."
        },
        {
            "option": "Manufacturer Regional Escalation",
            "condition": "Applicable for major international brands (Samsung, LG, Daikin, Apple).",
            "action": "Escalate directly to UAE Regional Headquarters Customer Experience office."
        }
    ]

    # 7. Important limitations
    limitations = [
        "CivicResolve AI provides regulatory intelligence, document auditing, and complaint drafting assistance.",
        "CivicResolve AI is not a law firm and does not provide formal judicial representation.",
        "Formal binding rulings, merchant sanctions, and enforceable decrees are the exclusive jurisdiction of official UAE government authorities.",
        "All complaints must be submitted through authorized official government channels or verified agency integrations."
    ]

    return {
        "what_happened": what_happened,
        "available_information": available_info,
        "missing_evidence": missing_evidence,
        "responsible_authority": responsible_authority,
        "action_steps": action_steps,
        "alternatives": alternatives,
        "limitations": limitations,
        "status": "plan_ready"
    }
