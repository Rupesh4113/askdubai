"""
CivicResolve AI - RAG Ingestion Pipeline
Parses official government sources, normalizes content, chunks passages,
generates embeddings, and builds the FAISS vector index with rich metadata.
"""
import os
import re
import json
import faiss
import numpy as np
from typing import List, Dict, Any
from rag.embeddings import encode_texts
from rag.source_registry import get_source_by_url, is_verified_official_source

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_DIR = os.path.join(BASE_DIR, "knowledge_base", "official_sources")
INDEX_DIR = os.path.join(BASE_DIR, "rag", "faiss_store")
INDEX_FILE = os.path.join(INDEX_DIR, "index.faiss")
METADATA_FILE = os.path.join(INDEX_DIR, "metadata.json")


def parse_source_document(filepath: str) -> Dict[str, Any]:
    """Reads a markdown or text source file and extracts header metadata and sections."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    metadata = {
        "source_file": os.path.basename(filepath),
        "url": "https://consumerrights.gov.ae/",
        "authority": "Official UAE Government Source",
        "jurisdiction": "Dubai / UAE",
        "verified_date": "2026-01-01"
    }

    url_match = re.search(r"\*\*Official URL\*\*:\s*(\S+)", text)
    if url_match:
        metadata["url"] = url_match.group(1)

    auth_match = re.search(r"\*\*Authority\*\*:\s*(.+)", text)
    if auth_match:
        metadata["authority"] = auth_match.group(1).strip()

    jur_match = re.search(r"\*\*Jurisdiction\*\*:\s*(.+)", text)
    if jur_match:
        metadata["jurisdiction"] = jur_match.group(1).strip()

    date_match = re.search(r"\*\*Verified Date\*\*:\s*(.+)", text)
    if date_match:
        metadata["verified_date"] = date_match.group(1).strip()

    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    metadata["title"] = title_match.group(1).strip() if title_match else os.path.basename(filepath)

    return {"metadata": metadata, "text": text}


def chunk_document(doc_data: Dict[str, Any], max_chunk_words: int = 250) -> List[Dict[str, Any]]:
    """Splits document text into coherent section-based chunks with metadata."""
    chunks = []
    text = doc_data["text"]
    meta = doc_data["metadata"]

    # Split by markdown headers
    sections = re.split(r"(?=(?:^|\n)##\s+)", text)
    for section in sections:
        section = section.strip()
        if not section:
            continue

        words = section.split()
        if len(words) <= max_chunk_words:
            chunks.append({
                "content": section,
                "metadata": {**meta, "chunk_id": len(chunks) + 1}
            })
        else:
            # Sub-chunk by paragraphs
            paragraphs = section.split("\n\n")
            curr_text = ""
            for p in paragraphs:
                p = p.strip()
                if not p:
                    continue
                if len((curr_text + "\n\n" + p).split()) <= max_chunk_words:
                    curr_text = (curr_text + "\n\n" + p).strip()
                else:
                    if curr_text:
                        chunks.append({
                            "content": curr_text,
                            "metadata": {**meta, "chunk_id": len(chunks) + 1}
                        })
                    curr_text = p
            if curr_text:
                chunks.append({
                    "content": curr_text,
                    "metadata": {**meta, "chunk_id": len(chunks) + 1}
                })

    return chunks


def build_faiss_index(force_rebuild: bool = False) -> bool:
    """Ingests official documents, computes embeddings, and persists FAISS index."""
    os.makedirs(INDEX_DIR, exist_ok=True)
    if not force_rebuild and os.path.exists(INDEX_FILE) and os.path.exists(METADATA_FILE):
        return True

    if not os.path.exists(SOURCES_DIR):
        os.makedirs(SOURCES_DIR, exist_ok=True)
        return False

    all_chunks = []
    for root, _, files in os.walk(SOURCES_DIR):
        for f in files:
            if f.endswith((".md", ".txt")):
                path = os.path.join(root, f)
                doc_data = parse_source_document(path)
                chunks = chunk_document(doc_data)
                all_chunks.extend(chunks)

    if not all_chunks:
        print("[RAG] No official documents found in knowledge_base/official_sources.")
        return False

    chunk_texts = [c["content"] for c in all_chunks]
    print(f"[RAG] Indexing {len(all_chunks)} chunks from official sources...")
    embeddings = encode_texts(chunk_texts)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner Product on normalized vectors = Cosine similarity
    index.add(embeddings)

    faiss.write_index(index, INDEX_FILE)

    metadata_list = [c["metadata"] for c in all_chunks]
    # Store text content alongside metadata for immediate retrieval
    for i, m in enumerate(metadata_list):
        m["content"] = chunk_texts[i]

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata_list, f, indent=2, ensure_ascii=False)

    print(f"[RAG] Successfully built FAISS index with {index.ntotal} vectors at {INDEX_FILE}")
    return True


if __name__ == "__main__":
    build_faiss_index(force_rebuild=True)
