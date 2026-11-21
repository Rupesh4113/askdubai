"""
CivicResolve AI - Document Intelligence FastAPI Routes Test Suite
Tests API endpoints for document upload, multi-page image preview, field editing,
raw text retrieval, and multi-format export (JSON, CSV, Excel, PDF).
"""
import io
import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
import fitz

client = TestClient(app)


def get_test_pdf_bytes():
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 50), "TAX INVOICE\nSharaf DG LLC Dubai\nTRN: 100234567890003\nInvoice No: INV-2026-9912\nDate: 2026-01-20\nTotal: AED 2,500.00\n", fontsize=11)
    b = doc.tobytes()
    doc.close()
    return b


def test_api_document_upload_and_preview():
    pdf_bytes = get_test_pdf_bytes()
    files = {"file": ("invoice_test.pdf", pdf_bytes, "application/pdf")}
    res = client.post("/api/v1/documents/upload", files=files)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "document_id" in data
    doc_id = data["document_id"]
    assert data["filename"] == "invoice_test.pdf"
    assert data["extracted_intelligence"]["merchant_information"]["business_name"]["value"] == "Sharaf DG"

    # Test page preview image
    res_img = client.get(f"/api/v1/documents/{doc_id}/page/1/image")
    assert res_img.status_code == 200
    assert res_img.headers["content-type"] == "image/png"
    assert len(res_img.content) > 100

    # Test raw text retrieval
    res_text = client.get(f"/api/v1/documents/{doc_id}/text")
    assert res_text.status_code == 200
    assert "Sharaf DG" in res_text.json()["text"]

    # Test field editing
    edit_payload = {
        "merchant_name": "Sharaf DG Flagship",
        "invoice_number": "INV-2026-9912-MOD",
        "total_payable": 2750.00
    }
    res_edit = client.put(f"/api/v1/documents/{doc_id}/fields", json=edit_payload)
    assert res_edit.status_code == 200
    assert res_edit.json()["message"]

    # Test exports
    res_json = client.get(f"/api/v1/documents/{doc_id}/export/json")
    assert res_json.status_code == 200
    assert "INV-2026-9912" in res_json.text

    res_csv = client.get(f"/api/v1/documents/{doc_id}/export/csv")
    assert res_csv.status_code == 200
    assert "CivicResolve AI" in res_csv.text

    res_xlsx = client.get(f"/api/v1/documents/{doc_id}/export/excel")
    assert res_xlsx.status_code == 200
    assert len(res_xlsx.content) > 500

    res_pdf = client.get(f"/api/v1/documents/{doc_id}/export/pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.content.startswith(b"%PDF")
