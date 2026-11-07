"""
CivicResolve AI - Invoice and Receipt Parser
Extracts structured purchase fields from unstructured raw document text.
Normalizes amounts, dates, currencies, and detects warranty specifications.
"""
import re
from typing import Dict, Any, Optional
from datetime import datetime


def parse_invoice_text(text: str) -> Dict[str, Any]:
    """
    Parses unstructured text from an invoice, receipt, or warranty slip.
    Returns a dictionary of validated extracted fields with confidence scores.
    """
    if not text or not text.strip():
        return {
            "merchant": None,
            "invoice_number": None,
            "purchase_date": None,
            "product_description": None,
            "amount": None,
            "currency": "AED",
            "warranty_period": None,
            "trn": None,
            "confidence_score": 0.0,
            "missing_fields": ["merchant", "invoice_number", "purchase_date", "product_description", "amount"]
        }

    merchant = _extract_merchant(text)
    invoice_number = _extract_invoice_number(text)
    purchase_date = _extract_date(text)
    product_description = _extract_product(text)
    amount, currency = _extract_amount(text)
    warranty_period = _extract_warranty(text)
    trn = _extract_trn(text)

    # Compute confidence based on key fields
    critical_fields = [merchant, invoice_number, purchase_date, amount, product_description]
    found_critical = sum(1 for f in critical_fields if f is not None)
    confidence = round(found_critical / len(critical_fields), 2)

    missing_fields = []
    if not merchant:
        missing_fields.append("merchant")
    if not invoice_number:
        missing_fields.append("invoice_number")
    if not purchase_date:
        missing_fields.append("purchase_date")
    if not amount:
        missing_fields.append("amount")
    if not product_description:
        missing_fields.append("product_description")
    if not warranty_period:
        missing_fields.append("warranty_period")

    return {
        "merchant": merchant,
        "invoice_number": invoice_number,
        "purchase_date": purchase_date,
        "product_description": product_description,
        "amount": amount,
        "currency": currency or "AED",
        "warranty_period": warranty_period,
        "trn": trn,
        "confidence_score": confidence,
        "missing_fields": missing_fields
    }


def _extract_merchant(text: str) -> Optional[str]:
    """Identifies the merchant or retailer name from header lines or labels."""
    # Direct label matches
    patterns = [
        r"(?:Merchant|Seller|Store|Company|Vendor|Retailer|Billed By)\s*[:\-]\s*([A-Za-z0-9\s&.,'\-]{3,60})",
        r"^(?:Tax Invoice|Receipt|Cash Invoice)\s*\n+([A-Za-z0-9\s&.,'\-]{3,60})",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE | re.MULTILINE)
        if m:
            name = m.group(1).strip()
            if not any(stop in name.lower() for stop in ["date", "invoice", "trn", "tel", "phone"]):
                return name

    # Common known UAE electronics & retail outlets if found near top
    known_merchants = [
        "Sharaf DG", "Lulu Hypermarket", "Carrefour", "Emax", "Jumbo Electronics",
        "Amazon UAE", "Noon", "Jacky's Electronics", "Union Coop", "Al-Futtaim ACE",
        "Virgin Megastore", "IKEA", "Home Centre", "Samsung Store", "Apple Store Dubai"
    ]
    for km in known_merchants:
        if re.search(r"\b" + re.escape(km) + r"\b", text, re.IGNORECASE):
            return km

    # Fallback to top non-empty line
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if lines:
        first_line = lines[0]
        if len(first_line) < 50 and not re.search(r"(invoice|receipt|page|date)", first_line, re.IGNORECASE):
            return first_line
    return None


def _extract_invoice_number(text: str) -> Optional[str]:
    """Extracts invoice, receipt, or transaction reference number."""
    # Priority 1: standard reference codes like INV-2026-9912, ORD-12345
    m_code = re.search(r"\b(?:INV|REC|ORD|REF)[-_][A-Za-z0-9-_]{3,20}\b", text, re.IGNORECASE)
    if m_code:
        return m_code.group(0).strip()

    # Priority 2: Labelled lines with No, Number, #, or colon
    patterns = [
        r"(?:Invoice|Receipt|Bill|Order|Ref)\s*(?:No\.?|Number|#|ID|Code)\s*[:\s-]*([A-Za-z0-9\-_/]{3,30})",
        r"(?:Invoice|Bill|Order)\s*[:]\s*([A-Za-z0-9\-_/]{3,30})",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val.lower() not in ["date", "from", "paid", "amount", "total", "cash"]:
                return val
    return None


def _extract_date(text: str) -> Optional[str]:
    """Finds purchase or issue date and normalizes to standard YYYY-MM-DD where possible."""
    patterns = [
        r"(?:Date|Invoice Date|Dated|Purchase Date|Billing Date)\s*[:\-\s]*([0-9]{1,4}[\/\.\-][0-9]{1,2}[\/\.\-][0-9]{1,4})",
        r"\b([0-9]{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+[0-9]{4})\b",
        r"\b([0-9]{4}[\/\.\-][0-9]{1,2}[\/\.\-][0-9]{1,2})\b",
        r"\b([0-9]{1,2}[\/\.\-][0-9]{1,2}[\/\.\-][0-9]{2,4})\b"
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            raw_date = m.group(1).strip()
            # Attempt parsing
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d %b %Y", "%d %B %Y", "%Y/%m/%d"):
                try:
                    dt = datetime.strptime(raw_date, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return raw_date
    return None


def _extract_amount(text: str) -> tuple[Optional[float], str]:
    """Extracts total transaction amount and confirms currency (AED)."""
    # Priority on Total, Net Total, Grand Total, Amount Paid
    patterns = [
        r"(?:Total|Grand Total|Net Total|Amount Paid|Balance Due|Total Amount)\s*(?:[\(]?(?:AED|Dhs|Dirhams)[\)]?)?\s*[:\-\s]*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)\s*(AED|Dhs|Dirham)?",
        r"(?:AED|Dhs|Dirhams)\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)",
        r"([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)\s*(?:AED|Dhs|Dirhams)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            raw_val = m.group(1).replace(",", "")
            try:
                amt = float(raw_val)
                if amt > 0.5:  # avoid zero/trivial line items
                    return amt, "AED"
            except ValueError:
                continue
    return None, "AED"


def _extract_product(text: str) -> Optional[str]:
    """Finds product or service description from item lines."""
    patterns = [
        r"(?:Item|Product|Description|Model|Particulars)\s*[:\-]\s*([A-Za-z0-9\s\-–\.\(\)\/]{4,80})",
        r"\b(?:Split Air Conditioner|Inverter AC|Refrigerator|Washing Machine|Smart TV|iPhone|Laptop|Microwave|Oven)\b[^\n,]*",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            prod = m.group(1).strip() if len(m.groups()) >= 1 else m.group(0).strip()
            return prod
    return None


def _extract_warranty(text: str) -> Optional[str]:
    """Identifies warranty terms stated in invoice or attached warranty card."""
    patterns = [
        r"(?:Warranty|Guarantee)\s*(?:Period|Terms)?\s*[:\-]?\s*([0-9]+\s*(?:Year|Years|Month|Months|Day|Days)[^\n\.;]*)",
        r"\b([0-9]+\s*(?:Year|Years|Month|Months)\s*(?:Comprehensive|Compressor|Standard)?\s*Warranty)\b",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip() if len(m.groups()) >= 1 else m.group(0).strip()
    return None


def _extract_trn(text: str) -> Optional[str]:
    """Extracts 15-digit UAE Tax Registration Number (TRN)."""
    m = re.search(r"\b(?:TRN|Tax Registration No\.?|VAT No\.?)\s*[:\-]?\s*([10][0-9]{14})\b", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None
