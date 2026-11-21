"""
CivicResolve AI - Document Intelligence Agent (Agent 3)
Coordinates OCR and invoice parsing, audits documentary evidence,
identifies missing mandatory documents, and verifies consistency with complaint statements.
"""
from typing import Dict, Any, List, Optional

from document_processing.document_upload import process_uploaded_document
from document_processing.validator import assess_missing_documents_for_category


def process_document(file_bytes: bytes, filename: str, complaint_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes end-to-end extraction on an uploaded document using the advanced
    Document Intelligence Agent pipeline.
    """
    res = process_uploaded_document(
        file_bytes=file_bytes,
        filename=filename,
        complaint_data=complaint_data
    )

    intel = res.get("extracted_intelligence", {})
    fin_audit = intel.get("financial_audit", {})
    vat_audit = intel.get("vat_compliance_information", {})

    validation_notes = []
    for disc in fin_audit.get("discrepancies", []):
        validation_notes.append(disc)
    for m in intel.get("missing_information", []):
        validation_notes.append(f"Missing field: {m.get('field_name')}")
    if not res.get("extracted_fields", {}).get("trn"):
        validation_notes.append("Standard UAE 15-digit TRN not detected; manual merchant verification recommended.")

    res["file_hash"] = res.get("duplicate_audit", {}).get("file_hash", "")
    res["validation_notes"] = validation_notes

    return res


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
