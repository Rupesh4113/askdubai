"""
CivicResolve AI - RAG & Rights Retrieval Tests
Verifies FAISS vector store, citation domain integrity, and jurisdiction routing.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.retriever import search_official_rights
from rag.source_registry import is_verified_official_source
from agents.rights_agent import research_official_rights


def test_official_source_verification():
    assert is_verified_official_source("https://consumerrights.gov.ae/en/Pages/default.aspx") is True
    assert is_verified_official_source("https://www.moec.gov.ae/en/consumer-protection") is True
    assert is_verified_official_source("https://u.ae/en/information-and-services") is True
    assert is_verified_official_source("https://random-unverified-blog.com/uae-rights") is False


def test_rag_retrieval_returns_verified_citations():
    query = "air conditioner stopped working within 14 days warranty replacement"
    results = search_official_rights(query, top_k=3)
    assert len(results) > 0
    for r in results:
        assert is_verified_official_source(r["source_url"]) is True
        assert r["confidence_score"] > 0.0
        assert r["authority"] != ""


def test_jurisdiction_routing_retail_vs_telecom_vs_bank():
    # 1. Retail Appliance
    res_retail = research_official_rights({"category": "defective_product", "description": "AC broken", "merchant": "Sharaf DG"})
    assert "Dubai" in res_retail["primary_authority"]

    # 2. Telecom
    res_telecom = research_official_rights({"category": "incorrect_billing", "description": "Etisalat charged for cancelled data plan", "merchant": "Etisalat"})
    assert "Telecommunications" in res_telecom["primary_authority"]

    # 3. Bank / Financial
    res_bank = research_official_rights({"category": "incorrect_billing", "description": "Credit card unauthorized transaction bank dispute", "merchant": "Commercial Bank"})
    assert "Sanadak" in res_bank["primary_authority"]
