"""
CivicResolve AI - Document Classification & Multi-Receipt Detector
Classifies uploaded documents into tax invoices, simplified invoices, receipts,
warranty certificates, or service orders, and identifies multi-invoice files.
"""
import re
from typing import Dict, Any, List


def classify_document(full_text: str, filename: str, pages_text: List[str] = None) -> Dict[str, Any]:
    """
    Analyzes document text, keywords, and structural patterns to classify document type
    and determine if multiple invoices or receipts are combined.
    """
    text_lower = full_text.lower()
    name_lower = filename.lower()
    pages_text = pages_text or [full_text]

    # Check for multiple documents across pages
    detected_invoices_per_page = []
    inv_pattern = re.compile(r"(?:invoice|receipt|bill)\s*(?:no\.?|#|number|id)?\s*[:\s-]*([A-Za-z0-9\-_/]{4,25})", re.IGNORECASE)

    for idx, p_text in enumerate(pages_text):
        matches = inv_pattern.findall(p_text)
        if matches:
            detected_invoices_per_page.append({"page": idx + 1, "invoices": list(set(matches[:3]))})

    distinct_invoices = set()
    for item in detected_invoices_per_page:
        for inv in item["invoices"]:
            distinct_invoices.add(inv.upper())

    contains_multiple_documents = len(distinct_invoices) > 1 and len(pages_text) > 1

    # Classify Primary Document Type
    primary_type = "supporting_document"
    type_display = "Supporting Document"
    compliance_classification = "Standard Document"
    reasons = []

    has_tax_invoice_kw = bool(re.search(r"\b(tax\s*invoice|فاتورة\s*ضريبية)\b", text_lower))
    has_trn = bool(re.search(r"\b(100\d{12})\b", text_lower)) or bool(re.search(r"\btrn\b", text_lower))
    has_warranty_kw = bool(re.search(r"\b(warranty\s*card|guarantee\s*certificate|service\s*contract|بطاقة\s*الضمان)\b", text_lower))
    has_pos_kw = bool(re.search(r"\b(pos|cashier|terminal|visa|mastercard|card\s*number|approval\s*code|merchant\s*copy)\b", text_lower))
    has_service_kw = bool(re.search(r"\b(repair\s*order|job\s*card|work\s*order|service\s*estimate|diagnostic)\b", text_lower))
    has_delivery_kw = bool(re.search(r"\b(delivery\s*note|delivery\s*order|packing\s*slip|goods\s*received)\b", text_lower))

    if has_tax_invoice_kw or (has_trn and any(k in text_lower for k in ["invoice", "vat", "taxable"])):
        # Check if Standard or Simplified under UAE VAT law
        # Standard requires Customer TRN/Name and detailed itemization
        has_customer_trn = bool(re.search(r"(?:buyer|customer|client)\s*(?:trn|tax\s*id)\s*[:\s-]*100\d{12}", text_lower))
        if has_customer_trn:
            primary_type = "tax_invoice"
            type_display = "Standard UAE Tax Invoice"
            compliance_classification = "Standard Tax Invoice (Executive Reg. Art. 59(1))"
            reasons.append("Identified seller TRN, customer TRN, and formal tax invoice terminology.")
        else:
            primary_type = "simplified_tax_invoice"
            type_display = "Simplified UAE Tax Invoice"
            compliance_classification = "Simplified Tax Invoice (Executive Reg. Art. 59(5))"
            reasons.append("Identified UAE Tax Invoice with supplier TRN; issued to non-registered or retail consumer.")
    elif has_warranty_kw or any(k in name_lower for k in ["warranty", "guarantee"]):
        primary_type = "warranty_card"
        type_display = "Warranty Card / Service Certificate"
        compliance_classification = "Consumer Warranty Document"
        reasons.append("Explicit warranty certificate, terms of coverage, and after-sales provisions identified.")
    elif has_service_kw:
        primary_type = "service_invoice"
        type_display = "Service / Repair Job Invoice"
        compliance_classification = "Commercial Service Invoice"
        reasons.append("Contains maintenance, repair job card, or technical inspection details.")
    elif has_delivery_kw:
        primary_type = "delivery_note"
        type_display = "Delivery Note / Dispatch Slip"
        compliance_classification = "Proof of Delivery"
        reasons.append("Contains shipping, consignment, or delivery dispatch details.")
    elif has_pos_kw or "receipt" in text_lower or "cash" in text_lower:
        primary_type = "purchase_receipt"
        type_display = "Commercial Purchase Receipt / POS Slip"
        compliance_classification = "Commercial Purchase Proof"
        reasons.append("Contains register transaction details, payment card terminal markers, or cash slip headers.")
    elif any(k in text_lower for k in ["dear customer", "complaint", "ticket", "case no", "regards", "email"]):
        primary_type = "merchant_communication"
        type_display = "Merchant Communication / Notice"
        compliance_classification = "Evidence of Communication"
        reasons.append("Contains correspondence, customer support emails, or formal dispute letters.")

    return {
        "document_type": primary_type,
        "type_display": type_display,
        "compliance_classification": compliance_classification,
        "classification_reasons": reasons,
        "contains_multiple_documents": contains_multiple_documents,
        "distinct_invoices_found": list(distinct_invoices),
        "pages_analyzed": len(pages_text)
    }
