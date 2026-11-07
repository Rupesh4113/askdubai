"""
CivicResolve AI - Classification Agent Tests
Verifies category identification and entity extraction accuracy across core problem types.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.complaint_agent import classify_complaint


def test_defective_product_classification():
    text = "I purchased an air conditioner from Sharaf DG for AED 2,500 two weeks ago. The unit stopped cooling and leaked water."
    res = classify_complaint(text)
    assert res["category"] == "defective_product"
    assert res["merchant"] == "Sharaf DG"
    assert res["amount"] == 2500.0
    assert res["currency"] == "AED"
    assert res["confidence"] >= 0.80


def test_warranty_dispute_classification():
    text = "Carrefour refused to repair my microwave under warranty, saying parts are not available."
    res = classify_complaint(text)
    assert res["category"] == "warranty_dispute"
    assert res["merchant"] == "Carrefour"
    assert res["confidence"] >= 0.70


def test_delayed_delivery_classification():
    text = "I ordered furniture from IKEA for AED 3,000 and the shipment has not arrived for three weeks with repeated delivery delays."
    res = classify_complaint(text)
    assert res["category"] == "delayed_delivery"
    assert res["merchant"] == "IKEA"
    assert res["amount"] == 3000.0


def test_refund_dispute_classification():
    text = "Lulu refuses to issue a money back refund for an unopened blender returned within 3 days."
    res = classify_complaint(text)
    assert res["category"] == "refund_dispute"
    assert res["merchant"] == "Lulu"


def test_empty_complaint_handling():
    res = classify_complaint("")
    assert res["category"] == "other"
    assert res["confidence"] == 0.0
