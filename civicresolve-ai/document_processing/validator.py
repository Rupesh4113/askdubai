"""
CivicResolve AI - Document Intelligence Validator
Performs duplicate detection, integrity verification, field validation,
and missing document requirement analysis.
"""
import hashlib
from typing import Dict, Any, List, Optional


def compute_file_hash(file_bytes: bytes) -> str:
    """Computes SHA-256 hash of document binary for tamper and duplicate detection."""
    return hashlib.sha256(file_bytes).hexdigest()


def validate_document_fields(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates extracted fields, checks constraints, and assigns validation status.
    Returns audit status: 'verified', 'incomplete', or 'flagged'.
    """
    status = "verified"
    notes = []

    # Check merchant
    merchant = extracted_data.get("merchant")
    if not merchant:
        status = "incomplete"
        notes.append("Merchant name could not be definitively detected.")

    # Check invoice number
    inv_num = extracted_data.get("invoice_number")
    if not inv_num:
        status = "incomplete"
        notes.append("Invoice or receipt number is missing.")

    # Check amount
    amount = extracted_data.get("amount")
    if amount is None or amount <= 0:
        status = "incomplete"
        notes.append("Transaction amount is missing or invalid.")

    # Check date
    date = extracted_data.get("purchase_date")
    if not date:
        status = "incomplete"
        notes.append("Purchase date is missing.")

    # Integrity alert: Never claim authenticity without official tax registration
    trn = extracted_data.get("trn")
    if not trn:
        notes.append("Standard UAE 15-digit TRN not detected; manual merchant verification recommended.")

    confidence = extracted_data.get("confidence_score", 0.0)
    if confidence < 0.4:
        status = "flagged"

    return {
        "status": status,
        "is_valid": status in ["verified", "incomplete"],
        "confidence": confidence,
        "validation_notes": notes
    }


def assess_missing_documents_for_category(category: str, uploaded_doc_types: List[str]) -> List[str]:
    """
    Determines missing evidence items based on complaint category.
    Assists the Resolution Planning Agent and user guidance.
    """
    required = {
        "defective_product": [
            "Official Tax Invoice or Purchase Receipt",
            "Manufacturer Warranty Card or Service Contract",
            "Photographs or Video showing the Defect or Serial Number",
            "Proof of Merchant Communication (Email, SMS, or Ticket)"
        ],
        "warranty_dispute": [
            "Official Tax Invoice or Purchase Receipt",
            "Warranty Card indicating Terms and Coverage Period",
            "Service Center Job Card or Repair Rejection Report",
            "Proof of Communication with Authorized Agent"
        ],
        "refund_dispute": [
            "Original Purchase Invoice",
            "Payment Proof (Credit Card Slip or Bank Statement)",
            "Store Return Request or Cancellation Receipt",
            "Merchant Written Refusal or Correspondence"
        ],
        "delayed_delivery": [
            "Sales Order Confirmation stating Promised Delivery Date",
            "Payment Receipt",
            "Follow-up Emails or Delivery Tracking Logs"
        ],
        "incorrect_billing": [
            "Detailed Itemized Bill or Invoice",
            "Agreed Quotation, Contract, or Price Tag Photograph",
            "Bank or Card Statement showing Excess Deducted Amount"
        ],
        "misleading_advertising": [
            "Dated Screenshot or Photograph of Advertisement / Price Tag",
            "Final Bill or Checkout Screen showing Discrepancy",
            "Merchant Communication"
        ]
    }

    mandatory = required.get(category, [
        "Official Proof of Purchase (Invoice / Receipt)",
        "Documentation of Dispute or Merchant Refusal"
    ])

    # Return items that haven't been identified in uploaded documents
    missing = []
    types_lower = [t.lower() for t in uploaded_doc_types]
    for item in mandatory:
        # Heuristic match
        matched = False
        for t in types_lower:
            if ("invoice" in item.lower() and "invoice" in t) or \
               ("warranty" in item.lower() and "warranty" in t) or \
               ("photo" in item.lower() and ("photo" in t or "image" in t)) or \
               ("communication" in item.lower() and ("email" in t or "communication" in t or "chat" in t)):
                matched = True
                break
        if not matched:
            missing.append(item)

    return missing
