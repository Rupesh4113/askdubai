"""
CivicResolve AI - UAE VAT Compliance & TRN Verification Engine
Audits tax invoices against UAE Federal Decree-Law No. (8) of 2017
and Executive Regulations (Articles 59(1) and 59(5)).
"""
import re
from typing import Dict, Any, List, Optional


def validate_uae_trn(trn: Optional[str]) -> Dict[str, Any]:
    """
    Validates UAE Tax Registration Number (TRN):
    Must be exactly 15 numeric digits and start with '100'.
    """
    if not trn:
        return {
            "trn": None,
            "is_valid": False,
            "status": "NOT FOUND",
            "message": "Tax Registration Number (TRN) not detected in document."
        }

    clean_trn = re.sub(r"[^\d]", "", str(trn))
    if len(clean_trn) == 15 and clean_trn.startswith("100"):
        return {
            "trn": clean_trn,
            "is_valid": True,
            "status": "VERIFIED",
            "message": "Valid 15-digit UAE FTA Tax Registration Number format (starts with '100')."
        }
    else:
        return {
            "trn": clean_trn if clean_trn else trn,
            "is_valid": False,
            "status": "REVIEW REQUIRED",
            "message": f"Invalid UAE TRN format ('{trn}'). Must be exactly 15 digits starting with '100'."
        }


def assess_uae_vat_compliance(
    document_title: Optional[str],
    seller_name: Optional[str],
    seller_trn: Optional[str],
    seller_address: Optional[str],
    customer_name: Optional[str],
    customer_trn: Optional[str],
    customer_address: Optional[str],
    invoice_number: Optional[str],
    invoice_date: Optional[str],
    line_items: List[Dict[str, Any]],
    subtotal: Optional[float],
    vat_amount: Optional[float],
    vat_rate: Optional[float],
    total_amount: Optional[float],
    currency: str = "AED"
) -> Dict[str, Any]:
    """
    Evaluates compliance against UAE VAT Executive Regulations:
    - Standard Tax Invoice (Article 59(1)): required if amount > AED 10,000 or customer is VAT registered.
    - Simplified Tax Invoice (Article 59(5)): permissible for retail consumers or consideration <= AED 10,000.
    """
    trn_audit = validate_uae_trn(seller_trn)
    customer_trn_audit = validate_uae_trn(customer_trn) if customer_trn else None

    # Determine applicable invoice standard
    is_high_value = total_amount is not None and total_amount > 10000.0
    requires_standard_invoice = is_high_value or (customer_trn and customer_trn_audit and customer_trn_audit["is_valid"])

    target_standard = "Standard Tax Invoice" if requires_standard_invoice else "Simplified Tax Invoice"

    # Mandatory Legal Checklist
    checklist = [
        {
            "id": "tax_invoice_header",
            "requirement": "Explicit 'Tax Invoice' (فاتورة ضريبية) title",
            "satisfied": bool(document_title and "tax invoice" in document_title.lower()),
            "mandatory_in": ["Standard Tax Invoice", "Simplified Tax Invoice"]
        },
        {
            "id": "seller_name",
            "requirement": "Registered commercial name of supplier",
            "satisfied": bool(seller_name and len(seller_name.strip()) > 2),
            "mandatory_in": ["Standard Tax Invoice", "Simplified Tax Invoice"]
        },
        {
            "id": "seller_trn",
            "requirement": "Supplier 15-digit Tax Registration Number (TRN)",
            "satisfied": trn_audit["is_valid"],
            "mandatory_in": ["Standard Tax Invoice", "Simplified Tax Invoice"]
        },
        {
            "id": "seller_address",
            "requirement": "Supplier physical or registered address in the UAE",
            "satisfied": bool(seller_address and len(seller_address.strip()) > 3),
            "mandatory_in": ["Standard Tax Invoice", "Simplified Tax Invoice"]
        },
        {
            "id": "invoice_number",
            "requirement": "Sequential or unique invoice number",
            "satisfied": bool(invoice_number and len(invoice_number.strip()) > 2),
            "mandatory_in": ["Standard Tax Invoice", "Simplified Tax Invoice"]
        },
        {
            "id": "invoice_date",
            "requirement": "Date of invoice issuance / supply",
            "satisfied": bool(invoice_date and len(invoice_date.strip()) > 5),
            "mandatory_in": ["Standard Tax Invoice", "Simplified Tax Invoice"]
        },
        {
            "id": "line_item_description",
            "requirement": "Detailed description of supplied goods or services",
            "satisfied": bool(line_items and len(line_items) > 0 and line_items[0].get("name")),
            "mandatory_in": ["Standard Tax Invoice", "Simplified Tax Invoice"]
        },
        {
            "id": "vat_amount_specified",
            "requirement": "Explicit total VAT amount payable in AED",
            "satisfied": vat_amount is not None,
            "mandatory_in": ["Standard Tax Invoice", "Simplified Tax Invoice"]
        },
        {
            "id": "total_payable",
            "requirement": "Gross total amount payable",
            "satisfied": total_amount is not None and total_amount > 0,
            "mandatory_in": ["Standard Tax Invoice", "Simplified Tax Invoice"]
        },
        {
            "id": "customer_details",
            "requirement": "Customer name and address (Mandatory for Standard Tax Invoice)",
            "satisfied": bool(customer_name and len(customer_name.strip()) > 2),
            "mandatory_in": ["Standard Tax Invoice"]
        },
        {
            "id": "customer_trn",
            "requirement": "Customer TRN (Mandatory where customer is a registered business)",
            "satisfied": bool(customer_trn_audit and customer_trn_audit["is_valid"]),
            "mandatory_in": ["Standard Tax Invoice (B2B)"]
        }
    ]

    applicable_checks = [c for c in checklist if target_standard in c["mandatory_in"]]
    satisfied_count = sum(1 for c in applicable_checks if c["satisfied"])
    completeness_ratio = round(satisfied_count / max(1, len(applicable_checks)), 2)

    missing_items = [c["requirement"] for c in applicable_checks if not c["satisfied"]]

    # Compliance Rating
    if completeness_ratio >= 0.90 and trn_audit["is_valid"]:
        compliance_status = "COMPLIANT"
        summary_msg = f"Preliminary assessment: Document meets mandatory requirements for a UAE {target_standard}."
    elif completeness_ratio >= 0.60:
        compliance_status = "PARTIALLY COMPLIANT / REVIEW REQUIRED"
        summary_msg = f"Document contains key invoice details but lacks mandatory requirements: {', '.join(missing_items[:3])}."
    else:
        compliance_status = "POTENTIALLY NON-COMPLIANT"
        summary_msg = "Document lacks essential UAE statutory invoice elements required under Federal Decree-Law No. (8) of 2017."

    return {
        "classification": target_standard,
        "is_high_value_transaction": is_high_value,
        "compliance_status": compliance_status,
        "completeness_score": completeness_ratio,
        "seller_trn_audit": trn_audit,
        "customer_trn_audit": customer_trn_audit,
        "standard_vat_rate_percent": 5.0,
        "currency": currency or "AED",
        "checklist": applicable_checks,
        "missing_mandatory_elements": missing_items,
        "summary_assessment": summary_msg,
        "regulatory_disclaimer": "This analysis provides a preliminary completeness assessment against UAE VAT Executive Regulations and does not constitute formal certification by the Federal Tax Authority (FTA)."
    }
