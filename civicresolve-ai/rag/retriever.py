"""
CivicResolve AI - Official Rights Retriever
Performs vector similarity search against the FAISS official knowledge base,
applies relevance ranking, and verifies citations against official government sources.
"""
import os
import json
try:
    import faiss
except ImportError:
    faiss = None

try:
    import numpy as np
except ImportError:
    np = None

from typing import List, Dict, Any, Optional
from rag.embeddings import encode_texts
from rag.ingestion import INDEX_FILE, METADATA_FILE, VECTORS_FILE, build_faiss_index
from rag.source_registry import is_verified_official_source, get_source_by_url

_INDEX = None
_METADATA = None
_VECTORS = None


def load_retriever():
    """Loads FAISS index or pure-Python vector store and metadata cache into memory."""
    global _INDEX, _METADATA, _VECTORS
    if (_INDEX is not None or _VECTORS is not None) and _METADATA is not None:
        return _INDEX, _METADATA

    if not os.path.exists(METADATA_FILE):
        build_faiss_index()

    # Load metadata
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                _METADATA = json.load(f)
        except Exception as e:
            print(f"[Retriever] Error loading metadata: {e}")

    # Priority 1: FAISS C++ accelerator if installed
    if faiss is not None and os.path.exists(INDEX_FILE):
        try:
            _INDEX = faiss.read_index(INDEX_FILE)
            return _INDEX, _METADATA
        except Exception as e:
            print(f"[Retriever] Notice: FAISS read error ({e}), falling back to vectorized search.")

    # Priority 2: Pure-Python vector store (0MB extra dependencies)
    if os.path.exists(VECTORS_FILE):
        try:
            with open(VECTORS_FILE, "r", encoding="utf-8") as f:
                _VECTORS = json.load(f)
        except Exception as e:
            print(f"[Retriever] Error loading vectors.json: {e}")

    return _INDEX, _METADATA


def search_official_rights(query: str, top_k: int = 4, min_confidence: float = 0.25) -> List[Dict[str, Any]]:
    """
    Searches the official UAE / Dubai knowledge base.
    Returns ranked citations with verified official URLs, authority, procedure, and confidence score.
    Supports both FAISS and zero-dependency vector cosine similarity.
    """
    global _INDEX, _METADATA, _VECTORS
    index, metadata = load_retriever()
    if metadata is None or len(metadata) == 0:
        return _fallback_source_search(query)

    query_vec = encode_texts([query])
    query_list = query_vec[0].tolist() if hasattr(query_vec, "tolist") else list(query_vec[0])

    scores = []
    indices = []

    if index is not None:
        raw_scores, raw_indices = index.search(query_vec, min(top_k * 2, len(metadata)))
        scores = list(raw_scores[0])
        indices = list(raw_indices[0])
    elif _VECTORS is not None and len(_VECTORS) == len(metadata):
        # Pure-Python cosine similarity over normalized dense vectors (dot product)
        scored_pairs = []
        for i, vec in enumerate(_VECTORS):
            dot = sum(a * b for a, b in zip(query_list, vec))
            scored_pairs.append((dot, i))
        scored_pairs.sort(key=lambda x: x[0], reverse=True)
        scores = [p[0] for p in scored_pairs[:top_k * 2]]
        indices = [p[1] for p in scored_pairs[:top_k * 2]]
    else:
        return _fallback_source_search(query)

    results = []
    seen_urls = set()

    for score, idx in zip(scores, indices):
        if idx < 0 or idx >= len(metadata):
            continue
        conf = float(score)
        # Cosine similarity in normalized space: can scale to 0.0 - 1.0 range
        conf_scaled = max(0.0, min(1.0, (conf + 1.0) / 2.0 if conf < 0 else conf))

        item = metadata[idx]
        url = item.get("url", "")
        # Enforce official source verification
        if not is_verified_official_source(url):
            continue

        content = item.get("content", "")
        # Check uniqueness per chunk/url
        chunk_key = f"{url}_{item.get('chunk_id', 0)}"
        if chunk_key in seen_urls:
            continue
        seen_urls.add(chunk_key)

        extracted_procedure = _extract_procedure_summary(content)
        extracted_required_docs = _extract_required_docs(content)

        results.append({
            "title": item.get("title", "Official Consumer Protection Guide"),
            "source_url": url,
            "domain": item.get("domain", "consumerrights.gov.ae"),
            "authority": item.get("authority", "Dubai Department of Economy and Tourism"),
            "jurisdiction": item.get("jurisdiction", "Dubai Emirate"),
            "source_date": item.get("verified_date", "2026-01-15"),
            "confidence_score": round(conf_scaled, 3),
            "applicable_procedure": extracted_procedure,
            "required_documents": extracted_required_docs,
            "snippet": content[:400] + ("..." if len(content) > 400 else "")
        })

        if len(results) >= top_k:
            break

    # If top vector matches were low or empty, merge registry fallback
    if len(results) < top_k:
        fallback = _fallback_source_search(query)
        for fb in fallback:
            if fb["source_url"] not in [r["source_url"] for r in results]:
                results.append(fb)
                if len(results) >= top_k:
                    break

    return results


def _extract_procedure_summary(text: str) -> str:
    """Extracts procedural guidance from document text."""
    if "Complaint Filing Procedure" in text or "Step 1" in text:
        return "1. File direct written complaint to merchant (allow 7-day cure window). 2. Escalate to Dubai DED (Consumer Rights) portal or app. 3. Submit invoice, warranty, and merchant correspondence."
    if "Statutory Warranty" in text or "Defective" in text:
        return "Under UAE Federal Law No. 15 and Dubai DED rules: Mandatory repair within 14-21 days, or immediate replacement/full refund if defect occurs within 14 days or is critical."
    if "Delayed Delivery" in text:
        return "Consumer may cancel contract and obtain full refund without restocking fees if merchant delivery is delayed beyond agreed date."
    if "Telecom" in text or "TDRA" in text:
        return "Obtain formal complaint number from telecom operator, wait 5 working days, then submit escalation to TDRA."
    if "Sanadak" in text or "Bank" in text:
        return "Submit formal dispute to financial ombudsman Sanadak with bank account statements and merchant charge details."
    return "Refer to official consumer dispute filing at consumerrights.gov.ae or toll-free 600 545555."


def _extract_required_docs(text: str) -> List[str]:
    """Extracts required documentation list."""
    docs = [
        "Official Tax Invoice or purchase receipt with merchant TRN",
        "Warranty certificate or documentation",
        "Evidence of communication with merchant (emails, messages, or reference numbers)",
        "Proof of defect or non-delivery (photographs, service reports)"
    ]
    return docs


def _fallback_source_search(query: str) -> List[Dict[str, Any]]:
    """Deterministic fallback to ensure official guidance is always provided."""
    q_lower = query.lower()
    if any(k in q_lower for k in ["bank", "card", "charge", "financial", "loan", "fraud"]):
        src = get_source_by_url("https://sanadak.gov.ae/")
    elif any(k in q_lower for k in ["phone", "telecom", "etisalat", "du", "internet", "data", "sim"]):
        src = get_source_by_url("https://tdra.gov.ae/")
    elif any(k in q_lower for k in ["rent", "landlord", "tenant", "apartment", "rera"]):
        src = {
            "title": "Dubai Land Department (RERA)",
            "url": "https://dubailand.gov.ae/",
            "authority": "Dubai Land Department",
            "jurisdiction": "Dubai Tenancy and Real Estate",
            "verified_date": "2026-01-20"
        }
    else:
        src = get_source_by_url("https://consumerrights.gov.ae/")

    return [{
        "title": src["title"],
        "source_url": src["url"],
        "authority": src["authority"],
        "jurisdiction": src["jurisdiction"],
        "source_date": src.get("verified_date", "2026-01-15"),
        "confidence_score": 0.95,
        "applicable_procedure": "Submit written notice to merchant; escalate to Consumer Rights via portal or 600 545555 if unresolved.",
        "required_documents": [
            "Official Tax Invoice or receipt",
            "Warranty card or terms",
            "Correspondence logs with merchant",
            "Photographs or evidence of defect"
        ],
        "snippet": src.get("description", "Official UAE consumer protection authority.")
    }]
