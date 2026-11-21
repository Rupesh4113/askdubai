"""
CivicResolve AI - Duplicate Document & Fraud Detection Service
Detects duplicate file uploads and identical transaction signatures
across cases and active sessions.
"""
import hashlib
import re
from typing import Dict, Any, Optional

_REGISTERED_SIGNATURES = set()
_REGISTERED_FILE_HASHES = set()


def compute_file_hash(file_bytes: bytes) -> str:
    """Computes standard SHA-256 binary hash."""
    return hashlib.sha256(file_bytes).hexdigest()


def compute_transaction_signature(
    merchant: Optional[str],
    invoice_number: Optional[str],
    amount: Optional[float],
    date: Optional[str]
) -> Optional[str]:
    """Generates structural fingerprint for invoice deduplication."""
    if not (merchant or invoice_number) or amount is None:
        return None

    clean_merch = re.sub(r"[^\w]", "", (merchant or "").lower())[:15]
    clean_inv = re.sub(r"[^\w]", "", (invoice_number or "").lower())[:20]
    amt_str = f"{float(amount):.2f}"
    clean_date = (date or "").replace("-", "").replace("/", "")[:8]

    signature_raw = f"{clean_merch}|{clean_inv}|{amt_str}|{clean_date}"
    return hashlib.sha256(signature_raw.encode("utf-8")).hexdigest()


def check_for_duplicate(
    file_bytes: bytes,
    merchant: Optional[str] = None,
    invoice_number: Optional[str] = None,
    amount: Optional[float] = None,
    date: Optional[str] = None,
    existing_docs: Optional[list] = None
) -> Dict[str, Any]:
    """
    Checks if binary hash or transaction fingerprint matches previously processed invoices.
    """
    file_hash = compute_file_hash(file_bytes)
    tx_signature = compute_transaction_signature(merchant, invoice_number, amount, date)

    is_exact_file_duplicate = False
    is_tx_signature_duplicate = False
    duplicate_reason = None

    if file_hash in _REGISTERED_FILE_HASHES:
        is_exact_file_duplicate = True
        duplicate_reason = "Identical file binary already processed in system."
    elif tx_signature and tx_signature in _REGISTERED_SIGNATURES:
        is_tx_signature_duplicate = True
        duplicate_reason = f"Duplicate transaction detected with identical merchant, invoice number ({invoice_number}), and amount."

    # Also check against database existing docs if provided
    if existing_docs and not (is_exact_file_duplicate or is_tx_signature_duplicate):
        for doc in existing_docs:
            if hasattr(doc, "storage_reference") and file_hash in str(doc.storage_reference):
                is_exact_file_duplicate = True
                duplicate_reason = f"File hash matches previous document record '{getattr(doc, 'filename', '')}'."
                break

    # Register current file and signature for session detection
    _REGISTERED_FILE_HASHES.add(file_hash)
    if tx_signature:
        _REGISTERED_SIGNATURES.add(tx_signature)

    return {
        "is_duplicate": is_exact_file_duplicate or is_tx_signature_duplicate,
        "is_exact_file_duplicate": is_exact_file_duplicate,
        "is_transaction_duplicate": is_tx_signature_duplicate,
        "duplicate_reason": duplicate_reason,
        "file_hash": file_hash,
        "transaction_signature": tx_signature
    }
