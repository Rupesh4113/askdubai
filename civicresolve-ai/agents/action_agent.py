"""
CivicResolve AI - Action Agent (Agent 6)
Generates formal merchant demand notices, official consumer complaint dossiers,
evidence summaries, and guides users through authorized submission channels.
Strictly prohibits autonomous submission without explicit human approval.
"""
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

N8N_NEW_COMPLAINT_URL = os.getenv("N8N_NEW_COMPLAINT_URL", "https://askdubai.app.n8n.cloud/form/civicresolve")
N8N_UPDATE_CASE_URL = os.getenv("N8N_UPDATE_CASE_URL", "https://askdubai.app.n8n.cloud/form/civicresolve-update")


def prepare_action_package(
    complaint_data: Dict[str, Any],
    evidence_analysis: Dict[str, Any],
    rights_info: Dict[str, Any],
    resolution_plan: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Synthesizes actionable drafts and submission kits.
    Requires user review and explicit approval before any external action can proceed.
    """
    merchant = complaint_data.get("merchant") or evidence_analysis.get("consolidated_merchant") or "[Merchant Name]"
    amount = complaint_data.get("amount") or evidence_analysis.get("consolidated_amount") or 0.0
    amount_str = f"AED {amount:,.2f}"
    inv_no = complaint_data.get("invoice_number") or evidence_analysis.get("consolidated_invoice_no") or "[Invoice #]"
    p_date = complaint_data.get("purchase_date") or evidence_analysis.get("consolidated_date") or "[Purchase Date]"
    desc = complaint_data.get("description", "")
    requested_res = complaint_data.get("requested_resolution") or "Immediate replacement or full refund"
    authority = rights_info.get("primary_authority", "Dubai Department of Economy and Tourism (DET)")
    portal_url = rights_info.get("official_portal_url", "https://consumerrights.gov.ae/")

    # 1. Formal Merchant Communication
    merchant_notice = _generate_merchant_notice(
        merchant=merchant,
        invoice_no=inv_no,
        purchase_date=p_date,
        amount_str=amount_str,
        description=desc,
        requested_resolution=requested_res
    )

    # 2. Official Authority Complaint Dossier
    official_dossier = _generate_official_dossier(
        authority=authority,
        merchant=merchant,
        invoice_no=inv_no,
        purchase_date=p_date,
        amount_str=amount_str,
        description=desc,
        requested_resolution=requested_res,
        legal_basis=rights_info.get("legal_basis", "UAE Federal Law No. 15 of 2020 on Consumer Protection")
    )

    # 3. Evidence Summary
    evidence_summary = _generate_evidence_summary(evidence_analysis)

    # 4. Official Submission Guidance
    submission_instructions = {
        "channel": authority,
        "direct_portal_url": portal_url,
        "helpline": "600 545555" if "Dubai" in authority else "800 1222",
        "mobile_app": "Dubai Consumer App (available on iOS and Android)",
        "authorized_n8n_flow": N8N_NEW_COMPLAINT_URL,
        "steps": [
            f"1. Navigate to the authorized portal: {portal_url} or use the authorized civic assistant link below.",
            "2. Fill in your personal Emirates ID / Resident Passport details.",
            f"3. Paste the generated CivicResolve complaint text into the description field.",
            "4. Upload the attached invoice and photos as itemized in the Evidence Summary.",
            "5. Submit and record your official government complaint reference number."
        ]
    }

    # 5. Follow-up Reminder Template
    follow_up_message = (
        f"Subject: Follow-up on Consumer Protection Formal Notice - Invoice {inv_no}\n\n"
        f"Dear Customer Service Team at {merchant},\n\n"
        f"I am writing to follow up on my formal notice submitted regarding the defective product purchased on {p_date} "
        f"(Invoice Ref: {inv_no}). As 72 hours have elapsed without a satisfactory resolution, please be advised that "
        f"this matter is being registered with the {authority} for formal regulatory mediation.\n\n"
        f"Sincerely,\n[Consumer Name]"
    )

    return {
        "merchant_notice": merchant_notice,
        "official_complaint_draft": official_dossier,
        "evidence_summary": evidence_summary,
        "submission_instructions": submission_instructions,
        "follow_up_template": follow_up_message,
        "external_submission_routes": {
            "n8n_new_complaint": N8N_NEW_COMPLAINT_URL,
            "n8n_update_case": N8N_UPDATE_CASE_URL,
            "government_portal": portal_url
        },
        "requires_human_approval": True,
        "approval_granted": False,
        "created_at": datetime.now().isoformat()
    }


def _generate_merchant_notice(merchant: str, invoice_no: str, purchase_date: str, amount_str: str, description: str, requested_resolution: str) -> str:
    return (
        f"FORMAL NOTICE OF CONSUMER DISPUTE\n"
        f"Date: {datetime.now().strftime('%d %B %Y')}\n\n"
        f"To: Management / Customer Relations, {merchant}\n"
        f"Reference: Invoice #{invoice_no} | Transaction Date: {purchase_date}\n"
        f"Subject: Statutory Notice of Defective Goods & Request for Remedy ({amount_str})\n\n"
        f"Dear Customer Service Team,\n\n"
        f"I am writing to formally place on record a serious consumer defect regarding my purchase of {amount_str} made on {purchase_date}.\n\n"
        f"Statement of Facts:\n"
        f"{description}\n\n"
        f"Legal Grounds:\n"
        f"Under UAE Federal Law No. 15 of 2020 on Consumer Protection (Articles 10 & 12) and the Executive Regulations enacted by Cabinet Decision No. 66 of 2023, suppliers in the United Arab Emirates are legally obligated to guarantee consumer goods against manufacturing defects, provide prompt repair within 14-21 calendar days, or immediately provide a replacement or full refund if the defect occurs within the statutory period.\n\n"
        f"Required Resolution:\n"
        f"In accordance with my statutory rights, I hereby formally request: {requested_resolution}.\n\n"
        f"Please confirm your arrangement for inspection, replacement, or refund within three (3) business days. In the absence of a satisfactory response, this dossier and all documentary evidence will be escalated directly to the Dubai Department of Economy and Tourism (Commercial Compliance & Consumer Protection CCCP) for formal enforcement.\n\n"
        f"Yours sincerely,\n"
        f"[Consumer Name]\n"
        f"[Contact Phone Number]\n"
        f"[Email Address]"
    )


def _generate_official_dossier(authority: str, merchant: str, invoice_no: str, purchase_date: str, amount_str: str, description: str, requested_resolution: str, legal_basis: str) -> str:
    return (
        f"OFFICIAL CONSUMER COMPLAINT FILING DOSSIER\n"
        f"Addressed To: {authority}\n"
        f"Filing Type: First-Party Consumer Rights Mediation Request\n"
        f"Date of Generation: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"1. COMPLAINANT / RESPONDENT INFORMATION\n"
        f"   - Respondent Merchant: {merchant}\n"
        f"   - Commercial Registration: Dubai Mainland / Licensed Commercial Entity\n"
        f"   - Transaction Reference / Tax Invoice: {invoice_no}\n"
        f"   - Date of Purchase: {purchase_date}\n"
        f"   - Disputed Amount: {amount_str}\n\n"
        f"2. SUMMARY OF COMPLAINT\n"
        f"   {description}\n\n"
        f"3. MERCHANT COMMUNICATION EFFORTS\n"
        f"   - Direct notice was submitted to {merchant} without adequate or lawful resolution.\n"
        f"   - The merchant has failed to fulfill mandatory after-sales warranty obligations.\n\n"
        f"4. STATUTORY BASIS\n"
        f"   - {legal_basis}\n"
        f"   - Dubai DET Commercial Compliance & Consumer Protection Standards\n\n"
        f"5. REQUESTED RELIEF\n"
        f"   - {requested_resolution} without penalty or unauthorized deduction.\n"
        f"   - Direction to the merchant to comply with statutory consumer protection directives.\n\n"
        f"Attestation: The complainant certifies that all statements and attached receipts are genuine and accurate."
    )


def _generate_evidence_summary(evidence_analysis: Dict[str, Any]) -> List[str]:
    summary = []
    summary.append(f"Total Attached Documents: {evidence_analysis.get('total_documents', 0)}")
    for t in evidence_analysis.get("uploaded_types", []):
        summary.append(f"• Document Category: {t.replace('_', ' ').title()}")
    if evidence_analysis.get("consolidated_invoice_no"):
        summary.append(f"• Verified Invoice / Receipt Reference: {evidence_analysis['consolidated_invoice_no']}")
    if evidence_analysis.get("consolidated_amount"):
        summary.append(f"• Verified Total Amount: AED {evidence_analysis['consolidated_amount']:,.2f}")
    return summary
