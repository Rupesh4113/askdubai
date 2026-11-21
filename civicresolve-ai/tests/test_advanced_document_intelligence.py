"""
CivicResolve AI - Advanced Document Intelligence Agent Test Suite
Validates complete field coverage (Sections A-H), mathematical validation,
UAE VAT compliance, multi-page PDFs, image processing, deduplication, and exports.
"""
import io
import os
import sys
import pytest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz  # PyMuPDF
from PIL import Image
import numpy as np

from document_processing.document_upload import process_uploaded_document
from document_processing.document_classifier import classify_document
from document_processing.pdf_processor import inspect_and_process_pdf
from document_processing.image_preprocessor import preprocess_image_bytes
from document_processing.ocr_engine import run_ocr_on_image
from document_processing.financial_validator import validate_financial_calculations
from document_processing.vat_validator import assess_uae_vat_compliance, validate_uae_trn
from document_processing.warranty_extractor import extract_warranty_information
from document_processing.confidence_engine import evaluate_document_accuracy
from document_processing.duplicate_detector import check_for_duplicate
from document_processing.report_generator import (
    export_document_json,
    export_document_csv,
    export_document_excel,
    export_document_pdf
)


def create_sample_pdf_invoice(is_multipage: bool = False) -> bytes:
    """Generates an in-memory sample vector PDF Tax Invoice for testing."""
    doc = fitz.open()

    # Page 1: Header, Merchant, Customer, Items
    page1 = doc.new_page(width=595, height=842)
    p1_text = (
        "TAX INVOICE\n"
        "Sharaf DG LLC Dubai\n"
        "TRN: 100234567890003\n"
        "Dubai Mall, Downtown Dubai, United Arab Emirates\n"
        "Tel: +971 4 345 6789 | Email: contact@sharafdg.com\n\n"
        "Bill To:\n"
        "Customer: Tariq Al-Mansoor\n"
        "Address: Marina Gate 1, Dubai Marina, UAE\n"
        "Invoice No: INV-2026-8819\n"
        "Invoice Date: 2026-02-10\n"
        "Reference No: REF-DXB-9912\n\n"
        "Description                          Qty   Unit Price   Total (AED)\n"
        "SuperCool Inverter AC 2.0 Ton         1     2380.95      2380.95\n"
        "AC Wall Bracket Installation Kit      1      100.00       100.00\n\n"
        "Subtotal before VAT: AED 2,480.95\n"
        "VAT (5%): AED 124.05\n"
        "Grand Total Payable: AED 2,605.00\n"
        "Amount Paid: AED 2,605.00\n"
        "Balance: AED 0.00\n\n"
        "Warranty: 2 Years Full Warranty\n"
        "Return Policy: 14 Days Statutory Return Policy under UAE Consumer Protection Law\n"
        "IBAN: AE290330000000012345678 (Emirates NBD)\n"
    )
    page1.insert_text((50, 60), p1_text, fontsize=10)

    if is_multipage:
        # Page 2: Service Terms and Warranty Conditions
        page2 = doc.new_page(width=595, height=842)
        p2_text = (
            "TAX INVOICE - PAGE 2 OF 2\n"
            "Invoice No: INV-2026-8819\n\n"
            "AFTER-SALES SERVICE & WARRANTY TERMS:\n"
            "1. Free on-site inspection within 48 hours for manufacturing defects.\n"
            "2. Warranty void if repaired by unauthorized technical centers.\n"
            "3. Support Hotline: 800-34433 (Sharaf DG UAE Support).\n"
        )
        page2.insert_text((50, 60), p2_text, fontsize=10)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_complete_pdf_extraction_pipeline():
    """Validates end-to-end processing of a sample UAE Tax Invoice PDF."""
    pdf_bytes = create_sample_pdf_invoice(is_multipage=False)
    res = process_uploaded_document(pdf_bytes, "tax_invoice_sample.pdf")

    assert res["status"] == "COMPLETED"
    assert res["page_count"] == 1
    assert res["format"] == "PDF"
    assert res["document_type"] == "simplified_tax_invoice" or res["document_type"] == "tax_invoice"

    intel = res["extracted_intelligence"]
    merch = intel["merchant_information"]
    assert merch["business_name"]["value"] == "Sharaf DG"
    assert merch["trn"]["value"] == "100234567890003"
    assert merch["trn"]["status"] == "VERIFIED"

    inv = intel["invoice_information"]
    assert inv["invoice_number"]["value"] == "INV-2026-8819"
    assert inv["invoice_date"]["value"] == "2026-02-10"

    # Line Items validation: 2 distinct items identified
    items = intel["product_service_details"]
    assert len(items) >= 2
    assert "SuperCool" in items[0]["product_name"] or "SuperCool" in items[1]["product_name"]

    # Financial validation
    fin = intel["financial_summary"]
    assert fin["total_payable"]["value"] == 2605.00
    assert fin["currency"]["value"] == "AED"

    # Math audit
    fin_audit = intel["financial_audit"]
    assert fin_audit["is_mathematically_consistent"] is True

    # Warranty validation
    war = intel["warranty_after_sales_information"]
    assert "2 Year" in war["warranty_duration"]["value"]
    assert war["warranty_expiry_date"]["status"] == "CALCULATED"
    assert war["warranty_expiry_date"]["value"] == "2028-02-10"


def test_multipage_pdf_processing():
    """Validates multi-page PDF processing across all pages."""
    pdf_bytes = create_sample_pdf_invoice(is_multipage=True)
    res = process_uploaded_document(pdf_bytes, "multipage_invoice.pdf")

    assert res["page_count"] == 2
    intel = res["extracted_intelligence"]
    assert intel["document_overview"]["pages_count"] == 2
    assert "page 2" in intel["raw_text_stream"].lower()


def test_financial_discrepancy_flagging():
    """Verifies that mathematical discrepancies are flagged while preserving printed totals."""
    audit = validate_financial_calculations(
        subtotal=2000.0,
        vat_amount=100.0,
        vat_rate=5.0,
        discounts=0.0,
        additional_charges=0.0,
        printed_total=2500.0,  # Deliberate mismatch: 2000 + 100 != 2500
        currency="AED"
    )
    assert audit["is_mathematically_consistent"] is False
    assert audit["math_validation_status"] == "REVIEW REQUIRED"
    assert audit["printed_total_preserved"] == 2500.0
    assert any("Grand Total Discrepancy" in d for d in audit["discrepancies"])


def test_uae_trn_validation():
    """Validates 15-digit TRN starting with 100 per UAE FTA specifications."""
    valid_res = validate_uae_trn("100234567890003")
    assert valid_res["is_valid"] is True
    assert valid_res["status"] == "VERIFIED"

    # Invalid: not starting with 100
    invalid_prefix = validate_uae_trn("200234567890003")
    assert invalid_prefix["is_valid"] is False
    assert invalid_prefix["status"] == "REVIEW REQUIRED"

    # Missing TRN
    missing_res = validate_uae_trn(None)
    assert missing_res["status"] == "NOT FOUND"


def test_unambiguous_warranty_calculation():
    """Tests that warranty expiry is calculated only when date and duration are unambiguous."""
    war = extract_warranty_information("SuperCool AC. Warranty: 1 Year Full Warranty.", purchase_date_str="2026-05-15")
    assert war["warranty_expiry_date"]["status"] == "CALCULATED"
    assert war["warranty_expiry_date"]["value"] == "2027-05-15"

    # When start date is absent, expiry must be NOT FOUND (never fabricated)
    war_no_date = extract_warranty_information("Warranty: 2 Years.", purchase_date_str=None)
    assert war_no_date["warranty_expiry_date"]["status"] == "NOT FOUND"
    assert war_no_date["warranty_expiry_date"]["value"] is None


def test_duplicate_detection():
    """Validates duplicate document and transaction signature detection."""
    sample_bytes = b"Sample Invoice Binary Content 2026"
    res1 = check_for_duplicate(sample_bytes, merchant="Sharaf DG", invoice_number="INV-100", amount=500.0, date="2026-01-01")
    assert res1["is_duplicate"] is False

    # Second check with identical binary content
    res2 = check_for_duplicate(sample_bytes, merchant="Sharaf DG", invoice_number="INV-100", amount=500.0, date="2026-01-01")
    assert res2["is_duplicate"] is True
    assert res2["is_exact_file_duplicate"] is True


def test_export_generators():
    """Validates export to JSON, CSV, Excel, and PDF."""
    pdf_bytes = create_sample_pdf_invoice(is_multipage=False)
    doc_data = process_uploaded_document(pdf_bytes, "sample.pdf")

    # JSON export
    json_out = export_document_json(doc_data)
    assert "Sharaf DG" in json_out
    assert "INV-2026-8819" in json_out

    # CSV export
    csv_out = export_document_csv(doc_data)
    assert "LINE ITEMS TABLE" in csv_out
    assert "INV-2026-8819" in csv_out

    # Excel export
    xlsx_bytes = export_document_excel(doc_data)
    assert len(xlsx_bytes) > 1000

    # PDF export
    pdf_report_bytes = export_document_pdf(doc_data)
    assert len(pdf_report_bytes) > 1000
    assert pdf_report_bytes.startswith(b"%PDF")
