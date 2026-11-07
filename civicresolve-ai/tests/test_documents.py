"""
CivicResolve AI - Document Intelligence Agent Tests
Validates text extraction, invoice field parsing, and missing document auditing.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from document_processing.invoice_parser import parse_invoice_text
from document_processing.validator import validate_document_fields, assess_missing_documents_for_category
from agents.document_agent import process_document


def test_invoice_text_parsing():
    raw_invoice = (
        "TAX INVOICE\n"
        "Sharaf DG LLC Dubai\n"
        "TRN: 100234567890003\n"
        "Invoice No: INV-2026-9912\n"
        "Date: 2026-01-20\n"
        "Item: SuperCool Split Air Conditioner 2.0 Ton\n"
        "Total Amount: AED 2,500.00\n"
        "Warranty: 2 Years Full Warranty\n"
    )
    data = parse_invoice_text(raw_invoice)
    assert data["merchant"] == "Sharaf DG"
    assert data["invoice_number"] == "INV-2026-9912"
    assert data["amount"] == 2500.0
    assert data["currency"] == "AED"
    assert data["purchase_date"] == "2026-01-20"
    assert data["trn"] == "100234567890003"
    assert data["confidence_score"] >= 0.80


def test_missing_field_detection():
    incomplete_invoice = "Receipt from unknown corner store. Paid 50."
    data = parse_invoice_text(incomplete_invoice)
    assert "invoice_number" in data["missing_fields"]
    assert "purchase_date" in data["missing_fields"]
    val = validate_document_fields(data)
    assert val["status"] in ["incomplete", "flagged"]


def test_missing_evidence_checklist_defective():
    # Only invoice provided; warranty card and photos missing
    missing = assess_missing_documents_for_category("defective_product", ["tax_invoice"])
    assert any("warranty" in m.lower() for m in missing)
    assert any("photo" in m.lower() or "defect" in m.lower() for m in missing)


def test_process_document_consistency_audit():
    invoice_text = "Sharaf DG\nInvoice: INV-44\nTotal: AED 2,500.00\nDate: 2026-01-15\n"
    res = process_document(
        file_bytes=invoice_text.encode("utf-8"),
        filename="invoice.txt",
        complaint_data={"merchant": "Sharaf DG", "amount": 2500.0}
    )
    assert "Merchant matched" in " ".join(res["consistency_audit"])
    assert "Amount confirmed" in " ".join(res["consistency_audit"])
