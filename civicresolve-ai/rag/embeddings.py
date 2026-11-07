"""
CivicResolve AI - Embeddings Generator
Provides high-performance vector embeddings for FAISS.
Uses SentenceTransformers with a resilient fallback mechanism.
"""
import os
import numpy as np
from typing import List

_MODEL_INSTANCE = None
_FALLBACK_VECTORIZER = None
_WARNED = False


def get_embedding_model():
    """Lazy loader for SentenceTransformer model with fallback."""
    global _MODEL_INSTANCE, _WARNED
    if _MODEL_INSTANCE is not None:
        return _MODEL_INSTANCE

    model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    try:
        from sentence_transformers import SentenceTransformer
        _MODEL_INSTANCE = SentenceTransformer(model_name)
        return _MODEL_INSTANCE
    except Exception as e:
        if not _WARNED:
            print(f"[Embeddings] Notice: Using internal fast embedding fallback: {e}")
            _WARNED = True
        return None


def encode_texts(texts: List[str]) -> np.ndarray:
    """Encodes a list of text strings into float32 numpy vectors."""
    if not texts:
        return np.empty((0, 384), dtype=np.float32)

    model = get_embedding_model()
    if model is not None:
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.astype(np.float32)

    # Resilient fallback: 384-dimensional deterministic feature vectors
    # Based on character/word hashing and frequency distribution
    return _generate_fallback_embeddings(texts, dim=384)


def _generate_fallback_embeddings(texts: List[str], dim: int = 384) -> np.ndarray:
    """Generates normalized deterministic dense vectors when sentence_transformers is unavailable."""
    matrix = np.zeros((len(texts), dim), dtype=np.float32)
    for i, text in enumerate(texts):
        tokens = text.lower().split()
        if not tokens:
            continue
        vec = np.zeros(dim, dtype=np.float32)
        for token in tokens:
            idx = abs(hash(token)) % dim
            vec[idx] += 1.0
        # Add character trigrams for semantic robustness
        for j in range(len(text) - 2):
            trigram = text[j:j+3].lower()
            idx = abs(hash(trigram)) % dim
            vec[idx] += 0.5
        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec = vec / norm
        matrix[i] = vec
    return matrix
