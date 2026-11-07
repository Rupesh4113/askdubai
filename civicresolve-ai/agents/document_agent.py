"""
CivicResolve AI - Document Intelligence Agent (Agent 3)
Coordinates OCR and invoice parsing, audits documentary evidence,
identifies missing mandatory documents, and verifies consistency with complaint statements.
"""
from typing import Dict, Any, List, Optional
from document_processing.ocr import extract_text_from_file
from document_processing.invoice_parser import parse_invoice_text
from document_processing.validator import validate_document_fields, assess_missing_documents_for_category, compute_file_hash


def process_document(file_bytes: bytes, filename: str, complaint_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes end-to-end extraction on an uploaded document.
    Audits extracted fields against stated complaint attributes and detects conflicts.
    """
    file_hash = compute_file_hash(file_bytes)
    extracted_text, ocr_meta = extract_text_from_file(file_bytes, filename)
    parsed_fields = parse_invoice_text(extracted_text)
    field_validation = validate_document_fields(parsed_fields)

    # Document type inference
    doc_type = _infer_document_type(filename, extracted_text)

    # Cross-reference with complaint data to detect discrepancies
    consistency_audit = []
    if complaint_data:
        # Check merchant
        stated_merchant = complaint_data.get("merchant")
        if stated_merchant and parsed_fields.get("merchant"):
            if stated_merchant.lower() in parsed_fields["merchant"].lower() or parsed_fields["merchant"].lower() in stated_merchant.lower():
                consistency_audit.append(f"Merchant matched: '{parsed_fields['merchant']}'.")
            else:
                consistency_audit.append(f"Discrepancy: User reported merchant '{stated_merchant}', but document specifies '{parsed_fields['merchant']}'.")

        # Check amount
        stated_amount = complaint_data.get("amount")
        if stated_amount and parsed_fields.get("amount"):
            diff = abs(float(stated_amount) - float(parsed_fields["amount"]))
            if diff < 1.0:
                consistency_audit.append(f"Amount confirmed: AED {parsed_fields['amount']:.2f}.")
            else:
                consistency_audit.append(f"Discrepancy: User reported AED {stated_amount}, but document states AED {parsed_fields['amount']}.")

    return {
        "filename": filename,
        "file_hash": file_hash,
        "document_type": doc_type,
        "extracted_text_preview": extracted_text[:300] + ("..." if len(extracted_text) > 300 else ""),
        "extracted_fields": parsed_fields,
        "validation_status": field_validation["status"],
        "confidence_score": field_validation["confidence"],
        "validation_notes": field_validation["validation_notes"],
        "consistency_audit": consistency_audit,
        "is_authentic_claim": False,  # Strict safeguard: never claim authenticity without formal verification
        "ocr_performed": ocr_meta.get("ocr_performed", False)
    }


def analyze_evidence_package(category: str, processed_documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates the complete evidence portfolio uploaded by the consumer.
    Returns completeness score and missing required documents list.
    """
    doc_types = [doc.get("document_type", "unknown") for doc in processed_documents]
    missing = assess_missing_documents_for_category(category, doc_types)

    # Aggregate extracted key metrics
    best_merchant = None
    best_amount = None
    best_invoice_no = None
    best_date = None

    for doc in processed_documents:
        fields = doc.get("extracted_fields", {})
        if not best_merchant and fields.get("merchant"):
            best_merchant = fields.get("merchant")
        if not best_amount and fields.get("amount"):
            best_amount = fields.get("amount")
        if not best_invoice_no and fields.get("invoice_number"):
            best_invoice_no = fields.get("invoice_number")
        if not best_date and fields.get("purchase_date"):
            best_date = fields.get("purchase_date")

    total_required = max(1, len(missing) + len(processed_documents))
    completeness_score = round(len(processed_documents) / total_required, 2)

    return {
        "total_documents": len(processed_documents),
        "uploaded_types": doc_types,
        "missing_evidence": missing,
        "completeness_score": min(1.0, completeness_score),
        "consolidated_merchant": best_merchant,
        "consolidated_amount": best_amount,
        "consolidated_invoice_no": best_invoice_no,
        "consolidated_date": best_date
    }


def _infer_document_type(filename: str, text: str) -> str:
    lower_name = filename.lower()
    lower_text = text.lower()

    if any(k in lower_name or k in lower_text for k in ["warranty", "guarantee", "service card"]):
        return "warranty_document"
    if any(k in lower_name or k in lower_text for k in ["invoice", "tax invoice", "bill", "tax_inv"]):
        return "tax_invoice"
    if any(k in lower_name or k in lower_text for k in ["receipt", "pos receipt", "cash memo"]):
        return "purchase_receipt"
    if any(k in lower_name or k in lower_text for k in ["email", "chat", "whatsapp", "ticket", "communication", "complaint"]):
        return "merchant_communication"
    if any(k in lower_name for k in [".png", ".jpg", ".jpeg", "photo", "defect", "damage"]):
        return "product_photograph"
    return "supporting_document"
