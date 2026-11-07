"""
CivicResolve AI - Multi-Agent End-to-End Workflow & Human Approval Tests
Tests the 7-agent pipeline execution, verification gates, and human approval enforcement.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.supervisor import SupervisorAgent
from workflows.approval_workflow import process_user_approval


def test_end_to_end_air_conditioner_sample_workflow():
    supervisor = SupervisorAgent()
    desc = (
        "A Dubai consumer purchases an air conditioner for AED 2,500 from Sharaf DG. "
        "The product stops working after two weeks. The seller does not respond."
    )
    mock_file = {
        "filename": "TaxInvoice_SharafDG.txt",
        "bytes": b"TAX INVOICE\nSharaf DG\nInvoice: INV-992\nAmount: AED 2,500.00\nDate: 2026-01-20\nProduct: Split AC 2.0 Ton\n"
    }

    result = supervisor.run_full_pipeline(
        complaint_description=desc,
        uploaded_files=[mock_file]
    )

    # 1. Classification
    assert result["complaint"]["category"] == "defective_product"
    assert result["complaint"]["amount"] == 2500.0

    # 2. Document Extraction
    assert len(result["documents"]) == 1
    assert result["documents"][0]["extracted_fields"]["invoice_number"] == "INV-992"

    # 3. Rights & Jurisdiction
    assert "Dubai" in result["rights"]["primary_authority"]

    # 4. Resolution Plan
    assert len(result["resolution_plan"]["action_steps"]) == 4

    # 5. Action Package
    assert "Federal Law No. 15 of 2020" in result["action_package"]["official_complaint_draft"]
    assert result["action_package"]["requires_human_approval"] is True
    assert result["action_package"]["approval_granted"] is False

    # 6. Verification
    assert result["verification"]["overall_status"] in ["passed", "warning"]
    assert result["verification"]["verification_score"] >= 0.80

    # 7. Next step enforces approval
    assert result["next_step"] == "awaiting_user_approval"


def test_human_approval_enforcement():
    # If approval is False, status is rejected_by_user and no action taken
    rej = process_user_approval(
        complaint_id="CASE-001",
        approved=False
    )
    assert rej["approved"] is False
    assert rej["status"] == "rejected_by_user"

    # If approval is True, status is approved_and_ready
    appr = process_user_approval(
        complaint_id="CASE-001",
        approved=True,
        user_notes="Proceed with submission to DET"
    )
    assert appr["approved"] is True
    assert appr["status"] == "approved_and_ready"
    assert "n8n" in appr["dispatch_url"] or "civicresolve" in appr["dispatch_url"]
