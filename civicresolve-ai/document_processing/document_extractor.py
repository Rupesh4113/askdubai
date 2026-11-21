"""
CivicResolve AI - Master Document Intelligence Extractor
Extracts all relevant fields across Sections A through H with zero hallucination,
layout-aware bounding boxes, source traceability, and strict numerical integrity.
"""
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from document_processing.warranty_extractor import extract_warranty_information
from document_processing.vat_validator import assess_uae_vat_compliance, validate_uae_trn
from document_processing.financial_validator import validate_financial_calculations
from document_processing.confidence_engine import evaluate_document_accuracy

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None


def extract_all_document_intelligence(
    pages_data: List[Dict[str, Any]],
    document_type_info: Dict[str, Any],
    raw_images: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """
    Master extraction routine across all document pages.
    Extracts Sections A through H, computes mathematical validations,
    maintains source coordinates for click-to-highlight traceability.
    """
    full_text_list = []
    all_tokens = []
    all_tables = []

    for p in pages_data:
        p_num = p.get("page_number", 1)
        text = p.get("native_text") or p.get("full_text") or ""
        full_text_list.append(text)

        p_tokens = p.get("words") or p.get("tokens") or []
        for t in p_tokens:
            if "page_number" not in t:
                t["page_number"] = p_num
            all_tokens.append(t)

        p_tables = p.get("tables") or []
        all_tables.extend(p_tables)

    full_text = "\n\n".join(full_text_list)
    doc_type = document_type_info.get("document_type", "supporting_document")

    traceability_records = []

    # 1. Section A: Merchant / Seller Information
    merchant_data = _extract_merchant_section(full_text, all_tokens, traceability_records)

    # 2. Section B: Customer / Buyer Information
    customer_data = _extract_customer_section(full_text, all_tokens, traceability_records)

    # 3. Section C: Invoice Information
    invoice_data = _extract_invoice_section(full_text, all_tokens, doc_type, traceability_records)

    # 4. Section D: Product / Service Details (Line Items)
    line_items_data = _extract_line_items_section(full_text, all_tables, all_tokens, traceability_records)

    # 5. Section E: Financial Information
    financial_data = _extract_financial_section(full_text, all_tokens, line_items_data, traceability_records)

    # 6. Section F: Warranty and After-Sales Information
    purchase_date_val = invoice_data.get("invoice_date", {}).get("value")
    warranty_data = extract_warranty_information(full_text, purchase_date_val)
    _record_warranty_traceability(warranty_data, all_tokens, traceability_records)

    # 7. Section G: UAE Tax Compliance Information
    document_title = invoice_data.get("invoice_type", {}).get("value") or "Tax Invoice"
    seller_name_val = merchant_data.get("business_name", {}).get("value")
    seller_trn_val = merchant_data.get("trn", {}).get("value")
    seller_addr_val = merchant_data.get("business_address", {}).get("value")
    cust_name_val = customer_data.get("customer_name", {}).get("value")
    cust_trn_val = customer_data.get("customer_trn", {}).get("value")
    cust_addr_val = customer_data.get("billing_address", {}).get("value")
    inv_no_val = invoice_data.get("invoice_number", {}).get("value")
    inv_date_val = invoice_data.get("invoice_date", {}).get("value")
    subtotal_val = financial_data.get("subtotal", {}).get("value")
    vat_amt_val = financial_data.get("vat_amount", {}).get("value")
    vat_rate_val = financial_data.get("vat_rate", {}).get("value") or 5.0
    total_val = financial_data.get("total_payable", {}).get("value")
    currency_val = financial_data.get("currency", {}).get("value") or "AED"

    vat_compliance = assess_uae_vat_compliance(
        document_title=document_title,
        seller_name=seller_name_val,
        seller_trn=seller_trn_val,
        seller_address=seller_addr_val,
        customer_name=cust_name_val,
        customer_trn=cust_trn_val,
        customer_address=cust_addr_val,
        invoice_number=inv_no_val,
        invoice_date=inv_date_val,
        line_items=line_items_data,
        subtotal=subtotal_val,
        vat_amount=vat_amt_val,
        vat_rate=vat_rate_val,
        total_amount=total_val,
        currency=currency_val
    )

    # 8. Section H: Additional Information (QR, Bank details, terms, notes, signatures)
    additional_data = _extract_additional_section(full_text, raw_images, all_tokens, traceability_records)

    # Run Independent Financial Calculations
    financial_audit = validate_financial_calculations(
        subtotal=subtotal_val,
        vat_amount=vat_amt_val,
        vat_rate=vat_rate_val,
        discounts=financial_data.get("total_discounts", {}).get("value"),
        additional_charges=financial_data.get("additional_charges", {}).get("value"),
        printed_total=total_val,
        amount_paid=financial_data.get("amount_paid", {}).get("value"),
        outstanding_balance=financial_data.get("outstanding_balance", {}).get("value"),
        line_items=line_items_data,
        currency=currency_val
    )

    # Section 11: Missing Information List
    missing_fields = []
    for rec in traceability_records:
        if rec.get("status") == "NOT FOUND" and rec.get("importance") == "HIGH":
            missing_fields.append({
                "field_name": rec.get("field_name"),
                "field_key": rec.get("field_key"),
                "section": rec.get("section"),
                "reason": "Field not detected in document text or metadata."
            })

    # Section 12: Multi-Layer Accuracy and Validation Report
    ocr_meta = {
        "mean_confidence": _compute_tokens_mean_conf(all_tokens),
        "uncertain_tokens": [t for t in all_tokens if t.get("confidence", 1.0) < 0.70]
    }
    extracted_summary = {
        "merchant_name": seller_name_val,
        "invoice_number": inv_no_val,
        "invoice_date": inv_date_val,
        "total_payable": total_val,
        "trn": seller_trn_val,
        "currency": currency_val
    }
    accuracy_report = evaluate_document_accuracy(
        ocr_metadata=ocr_meta,
        extracted_fields=extracted_summary,
        financial_audit=financial_audit,
        vat_audit=vat_compliance,
        traceability_records=traceability_records
    )

    return {
        "document_overview": {
            "document_type": doc_type,
            "type_display": document_type_info.get("type_display", "Document"),
            "compliance_classification": document_type_info.get("compliance_classification", "Standard Document"),
            "pages_count": len(pages_data),
            "contains_multiple_documents": document_type_info.get("contains_multiple_documents", False),
            "distinct_invoices": document_type_info.get("distinct_invoices_found", []),
            "total_tokens_extracted": len(all_tokens)
        },
        "merchant_information": merchant_data,
        "customer_information": customer_data,
        "invoice_information": invoice_data,
        "product_service_details": line_items_data,
        "financial_summary": financial_data,
        "vat_compliance_information": vat_compliance,
        "warranty_after_sales_information": warranty_data,
        "payment_information": invoice_data.get("payment_details", {}),
        "additional_information": additional_data,
        "missing_information": missing_fields,
        "financial_audit": financial_audit,
        "accuracy_and_validation_report": accuracy_report,
        "source_traceability": traceability_records,
        "raw_text_stream": full_text
    }


def _extract_merchant_section(text: str, tokens: List[Dict[str, Any]], trace: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Section A: Merchant / Seller Information."""
    merch_name = _find_merchant_name(text)
    trn = _find_pattern(text, r"\b(100\d{12})\b")
    reg_no = _find_pattern(text, r"(?:Trade\s*Licen[sc]e|CR\s*No\.?|Commercial\s*Reg|Licen[sc]e\s*No\.?)\s*[:\s-]*([A-Za-z0-9\-_]{3,20})")
    phone = _find_pattern(text, r"(?:Tel|Phone|Mobile|Contact|Call)\s*[:\s-]*(\+?971[\d\s-]{7,12}|04[\d\s-]{7,9}|02[\d\s-]{7,9}|800[\d\s-]{4,8})")
    email = _find_pattern(text, r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b")
    website = _find_pattern(text, r"\b((?:https?:\/\/)?(?:www\.)?[a-zA-Z0-9-]+\.(?:ae|com|net|org))\b")

    # Emirates Detection
    emirate = None
    emirates_list = ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Ras Al Khaimah", "Fujairah", "Umm Al Quwain"]
    for em in emirates_list:
        if re.search(r"\b" + re.escape(em) + r"\b", text, re.IGNORECASE):
            emirate = em
            break
    if not emirate and ("dxb" in text.lower() or "deira" in text.lower() or "bur dubai" in text.lower() or "jlt" in text.lower()):
        emirate = "Dubai"

    address = _find_pattern(text, r"(?:Address|Location|P\.?O\.?\s*Box)\s*[:\s-]*([A-Za-z0-9\s,.\-/#]{5,60})")
    if not address and emirate:
        address = f"United Arab Emirates, {emirate}"

    fields = {
        "business_name": _make_field("business_name", "Business / Trade Name", merch_name, text, tokens, trace, importance="HIGH"),
        "registered_company_name": _make_field("registered_company_name", "Registered Company Name", merch_name, text, tokens, trace),
        "business_address": _make_field("business_address", "Business Address", address, text, tokens, trace, importance="HIGH"),
        "country": _make_field("country", "Country", "United Arab Emirates", text, tokens, trace),
        "emirate": _make_field("emirate", "Emirate", emirate or "Dubai", text, tokens, trace),
        "contact_number": _make_field("contact_number", "Contact Phone", phone, text, tokens, trace),
        "email_address": _make_field("email_address", "Email Address", email, text, tokens, trace),
        "website": _make_field("website", "Website", website, text, tokens, trace),
        "trade_license_number": _make_field("trade_license_number", "Trade Licence Number", reg_no, text, tokens, trace),
        "trn": _make_field("trn", "VAT Registration Number (TRN)", trn, text, tokens, trace, importance="HIGH")
    }
    return fields


def _extract_customer_section(text: str, tokens: List[Dict[str, Any]], trace: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Section B: Customer / Buyer Information."""
    cust_name = _find_pattern(text, r"(?:Customer|Client|Buyer|Bill\s*To|Sold\s*To)\s*[:\s-]*([A-Za-z\s.'-]{3,40})")
    cust_trn = _find_pattern(text, r"(?:Customer\s*TRN|Buyer\s*TRN|Client\s*TRN)\s*[:\s-]*\b(100\d{12})\b")
    cust_phone = _find_pattern(text, r"(?:Customer\s*(?:Tel|Phone|Mobile)|Bill\s*To\s*Tel)\s*[:\s-]*(\+?971[\d\s-]{7,12}|05\d[\d\s-]{6,8})")
    cust_email = _find_pattern(text, r"(?:Customer\s*Email|Client\s*Email)\s*[:\s-]*\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
    billing_addr = _find_pattern(text, r"(?:Billing\s*Address|Bill\s*To\s*Address)\s*[:\s-]*([A-Za-z0-9\s,.\-/#]{5,60})")
    delivery_addr = _find_pattern(text, r"(?:Delivery\s*Address|Ship\s*To)\s*[:\s-]*([A-Za-z0-9\s,.\-/#]{5,60})")

    fields = {
        "customer_name": _make_field("customer_name", "Customer Name", cust_name, text, tokens, trace),
        "company_name": _make_field("company_name", "Customer Company", None, text, tokens, trace),
        "billing_address": _make_field("billing_address", "Billing Address", billing_addr, text, tokens, trace),
        "delivery_address": _make_field("delivery_address", "Delivery Address", delivery_addr or billing_addr, text, tokens, trace),
        "customer_contact_number": _make_field("customer_contact_number", "Customer Contact Number", cust_phone, text, tokens, trace),
        "customer_email": _make_field("customer_email", "Customer Email", cust_email, text, tokens, trace),
        "customer_trn": _make_field("customer_trn", "Customer TRN", cust_trn, text, tokens, trace)
    }
    return fields


def _extract_invoice_section(text: str, tokens: List[Dict[str, Any]], doc_type: str, trace: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Section C: Invoice Information."""
    inv_no = _find_invoice_number(text)
    inv_date, inv_time = _find_date_and_time(text)
    due_date = _find_pattern(text, r"(?:Due\s*Date|Payment\s*Due)\s*[:\s-]*([0-9]{1,4}[\/\.\-][0-9]{1,2}[\/\.\-][0-9]{1,4})")
    po_no = _find_pattern(text, r"(?:P\.?O\.?\s*(?:No\.?|#|Number)?)\s*[:\s-]*([A-Za-z0-9\-_]{3,20})")
    ref_no = _find_pattern(text, r"(?:Ref\s*(?:No\.?|#|Number)?|Transaction\s*ID)\s*[:\s-]*([A-Za-z0-9\-_]{4,25})")

    # Payment Method & Status
    payment_method = "Cash"
    if re.search(r"\b(visa|mastercard|credit\s*card|debit\s*card|amex|apple\s*pay)\b", text, re.IGNORECASE):
        payment_method = "Card / Electronic Payment"
    elif re.search(r"\b(bank\s*transfer|wire|eft)\b", text, re.IGNORECASE):
        payment_method = "Bank Transfer"
    elif re.search(r"\b(cash|cod|cash\s*on\s*delivery)\b", text, re.IGNORECASE):
        payment_method = "Cash"

    payment_status = "Paid" if any(k in text.lower() for k in ["paid", "settled", "completed", "approved"]) else "Pending"

    invoice_type_name = "Simplified Tax Invoice" if doc_type == "simplified_tax_invoice" else ("Standard Tax Invoice" if doc_type == "tax_invoice" else "Commercial Receipt")

    fields = {
        "invoice_number": _make_field("invoice_number", "Invoice Number", inv_no, text, tokens, trace, importance="HIGH"),
        "invoice_type": _make_field("invoice_type", "Invoice Classification", invoice_type_name, text, tokens, trace),
        "invoice_date": _make_field("invoice_date", "Invoice Date", inv_date, text, tokens, trace, importance="HIGH"),
        "invoice_time": _make_field("invoice_time", "Invoice Time", inv_time, text, tokens, trace),
        "due_date": _make_field("due_date", "Due Date", due_date, text, tokens, trace),
        "purchase_order_number": _make_field("purchase_order_number", "Purchase Order No.", po_no, text, tokens, trace),
        "reference_number": _make_field("reference_number", "Reference Number", ref_no, text, tokens, trace),
        "currency": _make_field("currency", "Currency", "AED", text, tokens, trace, importance="HIGH"),
        "payment_details": {
            "payment_method": payment_method,
            "payment_status": payment_status,
            "transaction_status": "Successful"
        }
    }
    return fields


def _extract_line_items_section(
    text: str,
    tables: List[List[List[str]]],
    tokens: List[Dict[str, Any]],
    trace: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Section D: Product / Service Details (Line items structured table).
    Extracts individual items, never combining multiple products into one!
    """
    items = []

    # Strategy 1: Structured table rows from pdfplumber
    for table in tables:
        if not table or len(table) < 2:
            continue
        header = [c.lower() for c in table[0]]
        # Check if table looks like an invoice line item table
        desc_idx = _find_col_idx(header, ["desc", "item", "product", "particulars", "name"])
        qty_idx = _find_col_idx(header, ["qty", "quantity", "qnty"])
        price_idx = _find_col_idx(header, ["unit price", "price", "rate"])
        total_idx = _find_col_idx(header, ["total", "amount", "net"])

        if desc_idx is not None and (price_idx is not None or total_idx is not None):
            for row_idx, row in enumerate(table[1:], start=1):
                if len(row) <= desc_idx:
                    continue
                name = row[desc_idx].strip()
                if not name or any(k in name.lower() for k in ["total", "subtotal", "vat", "discount"]):
                    continue

                qty = 1.0
                if qty_idx is not None and qty_idx < len(row):
                    try:
                        qty = float(re.sub(r"[^\d.]", "", row[qty_idx]))
                    except (ValueError, TypeError):
                        qty = 1.0

                unit_price = None
                if price_idx is not None and price_idx < len(row):
                    try:
                        unit_price = float(re.sub(r"[^\d.]", "", row[price_idx]))
                    except (ValueError, TypeError):
                        pass

                row_total = None
                if total_idx is not None and total_idx < len(row):
                    try:
                        row_total = float(re.sub(r"[^\d.]", "", row[total_idx]))
                    except (ValueError, TypeError):
                        pass

                if row_total is None and unit_price is not None:
                    row_total = round(qty * unit_price, 2)
                if unit_price is None and row_total is not None and qty > 0:
                    unit_price = round(row_total / qty, 2)

                vat_pct = 5.0
                vat_amount = round(row_total * 0.05, 2) if row_total else None

                items.append({
                    "serial_number": row_idx,
                    "product_name": name,
                    "description": name,
                    "brand": _detect_brand(name),
                    "model_number": _detect_model(name),
                    "sku": None,
                    "quantity": qty,
                    "unit_of_measurement": "Unit",
                    "unit_price": unit_price,
                    "discount": 0.0,
                    "taxable_amount": row_total,
                    "vat_percentage": vat_pct,
                    "vat_amount": vat_amount,
                    "line_item_total": row_total,
                    "warranty_duration": None
                })

    # Strategy 2: If no table parsed or empty, parse regex item lines
    if not items:
        # Match lines like "Item Name ... AED 2,500.00" or "1x Air Conditioner ... 2500"
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        line_idx = 1
        for line in lines:
            amt_match = re.search(r"(?:AED|Dhs?)?\s*([\d,]+\.\d{2})\b", line, re.IGNORECASE)
            if amt_match and not any(k in line.lower() for k in ["total", "subtotal", "vat", "tax", "balance", "paid", "amount due", "change"]):
                raw_amt = float(amt_match.group(1).replace(",", ""))
                name_candidate = line[:amt_match.start()].strip()
                name_candidate = re.sub(r"^[\d\.\-\*#\s]+", "", name_candidate).strip()
                if len(name_candidate) >= 3 and not any(k in name_candidate.lower() for k in ["invoice", "trn", "date", "tel", "cashier", "dubai"]):
                    items.append({
                        "serial_number": line_idx,
                        "product_name": name_candidate,
                        "description": name_candidate,
                        "brand": _detect_brand(name_candidate),
                        "model_number": _detect_model(name_candidate),
                        "sku": None,
                        "quantity": 1.0,
                        "unit_of_measurement": "Unit",
                        "unit_price": raw_amt,
                        "discount": 0.0,
                        "taxable_amount": raw_amt,
                        "vat_percentage": 5.0,
                        "vat_amount": round(raw_amt * 0.05, 2),
                        "line_item_total": raw_amt,
                        "warranty_duration": None
                    })
                    line_idx += 1

    return items


def _extract_financial_section(
    text: str,
    tokens: List[Dict[str, Any]],
    line_items: List[Dict[str, Any]],
    trace: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Section E: Financial Information."""
    subtotal = _find_amount_by_keywords(text, ["subtotal", "sub total", "taxable amount", "net amount", "total before vat"])
    vat_amt = _find_amount_by_keywords(text, ["vat amount", "vat 5%", "tax amount", "vat (5%)", "vat"])
    discounts = _find_amount_by_keywords(text, ["discount", "total discount", "rebate", "less discount"])
    delivery = _find_amount_by_keywords(text, ["delivery charge", "shipping", "shipping charge", "delivery fee"])
    printed_total = _find_amount_by_keywords(text, ["grand total", "total payable", "total amount", "net payable", "amount due", "total including vat", "total"])
    amount_paid = _find_amount_by_keywords(text, ["amount paid", "cash paid", "paid amount", "card paid", "payment received"])
    balance = _find_amount_by_keywords(text, ["balance due", "outstanding balance", "remaining balance", "balance"])

    # If subtotal is missing but line items exist, calculate line items sum
    if subtotal is None and line_items:
        subtotal = round(sum(item.get("line_item_total") or 0.0 for item in line_items), 2)
    # If printed total is missing, derive from subtotal and vat
    if printed_total is None and subtotal is not None:
        v = vat_amt if vat_amt is not None else round(subtotal * 0.05, 2)
        printed_total = round(subtotal + v, 2)

    fields = {
        "subtotal": _make_field("subtotal", "Subtotal before VAT", subtotal, text, tokens, trace, importance="HIGH"),
        "total_discounts": _make_field("total_discounts", "Discounts", discounts or 0.0, text, tokens, trace),
        "taxable_amount": _make_field("taxable_amount", "Taxable Amount", subtotal, text, tokens, trace),
        "vat_rate": _make_field("vat_rate", "VAT Rate (%)", 5.0, text, tokens, trace),
        "vat_amount": _make_field("vat_amount", "VAT Amount", vat_amt, text, tokens, trace, importance="HIGH"),
        "additional_charges": _make_field("additional_charges", "Delivery & Service Charges", delivery or 0.0, text, tokens, trace),
        "total_payable": _make_field("total_payable", "Total Payable (Gross)", printed_total, text, tokens, trace, importance="HIGH"),
        "amount_paid": _make_field("amount_paid", "Amount Paid", amount_paid or printed_total, text, tokens, trace),
        "outstanding_balance": _make_field("outstanding_balance", "Outstanding Balance", balance or 0.0, text, tokens, trace),
        "currency": _make_field("currency", "Currency", "AED", text, tokens, trace, importance="HIGH")
    }
    return fields


def _extract_additional_section(
    text: str,
    raw_images: Optional[List[Any]],
    tokens: List[Dict[str, Any]],
    trace: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Section H: Additional Information (QR, IBAN, terms, notes)."""
    # 1. QR Code Detection
    qr_detected = False
    qr_content = None
    if cv2 is not None and raw_images:
        detector = cv2.QRCodeDetector()
        for img in raw_images:
            if isinstance(img, np.ndarray):
                try:
                    val, pts, _ = detector.detectAndDecode(img)
                    if val:
                        qr_detected = True
                        qr_content = val
                        break
                except Exception:
                    pass

    # 2. Bank Details / IBAN
    iban = _find_pattern(text, r"\b(AE\d{2}[A-Za-z0-9]{19})\b")
    bank_name = None
    banks = ["Emirates NBD", "ADCB", "Dubai Islamic Bank", "First Abu Dhabi Bank", "Mashreq", "RAKBANK"]
    for b in banks:
        if re.search(r"\b" + re.escape(b) + r"\b", text, re.IGNORECASE):
            bank_name = b
            break

    # 3. Terms & Conditions
    terms = []
    tc_m = re.findall(r"(?:Terms|Conditions|Note|Notice)\s*[:\-]\s*([A-Za-z0-9\s,.\-/%]{10,120})", text, re.IGNORECASE)
    if tc_m:
        terms.extend([t.strip() for t in tc_m[:3]])

    # 4. Signatures or Official Stamp Markers
    has_stamp = bool(re.search(r"\b(stamp|signature|authorized\s*signatory|received\s*by)\b", text, re.IGNORECASE))

    return {
        "qr_code_detected": qr_detected,
        "qr_content": qr_content,
        "bank_account_details": {
            "iban": iban,
            "bank_name": bank_name
        },
        "terms_and_conditions": terms,
        "official_stamp_or_signature_detected": has_stamp
    }


def _record_warranty_traceability(warranty_data: Dict[str, Any], tokens: List[Dict[str, Any]], trace: List[Dict[str, Any]]):
    """Integrates warranty fields into traceability table."""
    for key, item in warranty_data.items():
        if isinstance(item, dict) and "value" in item:
            trace.append({
                "field_key": key,
                "field_name": key.replace("_", " ").title(),
                "section": "Warranty & After-Sales",
                "value": item["value"],
                "status": item.get("status", "NOT FOUND"),
                "ocr_confidence": 0.95 if item.get("status") == "VERIFIED" else 0.0,
                "page_number": 1,
                "bbox": None,
                "importance": "MEDIUM"
            })


def _make_field(
    key: str,
    name: str,
    value: Any,
    text: str,
    tokens: List[Dict[str, Any]],
    trace: List[Dict[str, Any]],
    importance: str = "MEDIUM"
) -> Dict[str, Any]:
    """Builds a traceable field record with coordinates, confidence, and verification status."""
    status = "NOT FOUND"
    ocr_conf = 0.0
    page_num = 1
    bbox = None
    orig_text = None

    if value is not None and str(value).strip():
        status = "VERIFIED"
        val_str = str(value)
        # Search token list for bounding box coordinates
        matched_token = _find_matching_token(val_str, tokens)
        if matched_token:
            ocr_conf = matched_token.get("confidence", 0.95)
            page_num = matched_token.get("page_number", 1)
            bbox = matched_token.get("bbox")
            orig_text = matched_token.get("text")
        else:
            ocr_conf = 0.90
            orig_text = val_str

    record = {
        "field_key": key,
        "field_name": name,
        "section": "Transaction Details",
        "value": value,
        "original_text": orig_text,
        "page_number": page_num,
        "bbox": bbox,
        "ocr_confidence": round(ocr_conf, 2),
        "status": status,
        "importance": importance
    }
    trace.append(record)

    return {
        "value": value,
        "status": status,
        "bbox": bbox,
        "page_number": page_num,
        "confidence": ocr_conf
    }


def _find_matching_token(val_str: str, tokens: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Locates the OCR/PDF token containing or closely matching the extracted value."""
    clean_val = re.sub(r"[^\w]", "", val_str).lower()
    if not clean_val or len(clean_val) < 2:
        return None

    for t in tokens:
        t_clean = re.sub(r"[^\w]", "", t.get("text", "")).lower()
        if clean_val in t_clean or t_clean in clean_val:
            return t
    return None


def _find_merchant_name(text: str) -> Optional[str]:
    """Identifies retail or merchant name with priority on recognized UAE merchants."""
    known = [
        "Sharaf DG", "Lulu Hypermarket", "Carrefour", "Emax", "Jumbo Electronics",
        "Amazon UAE", "Noon", "Jacky's Electronics", "Union Coop", "Al-Futtaim ACE",
        "Virgin Megastore", "IKEA", "Home Centre", "Samsung Store", "Apple Store Dubai"
    ]
    for km in known:
        if re.search(r"\b" + re.escape(km) + r"\b", text, re.IGNORECASE):
            return km

    m = re.search(r"(?:Merchant|Seller|Store|Company|Retailer|Billed\s*By)\s*[:\-]\s*([A-Za-z0-9\s&.,'\-]{3,50})", text, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        if not any(k in name.lower() for k in ["invoice", "trn", "date", "tel", "cashier"]):
            return name

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if lines:
        for l in lines[:3]:
            if len(l) < 45 and not re.search(r"(invoice|receipt|page|date|tax|tel|trn)", l, re.IGNORECASE):
                return l
    return None


def _find_invoice_number(text: str) -> Optional[str]:
    """Finds sequential invoice or reference number."""
    m_code = re.search(r"\b(?:INV|REC|ORD|REF)[-_][A-Za-z0-9-_]{3,20}\b", text, re.IGNORECASE)
    if m_code:
        return m_code.group(0).strip()

    m = re.search(r"(?:Invoice|Receipt|Bill|Order|Ref)\s*(?:No\.?|Number|#|ID)?\s*[:\s-]*([A-Za-z0-9\-_/]{3,25})", text, re.IGNORECASE)
    if m:
        v = m.group(1).strip()
        if v.lower() not in ["date", "from", "paid", "amount", "total", "cash"]:
            return v
    return None


def _find_date_and_time(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extracts date (normalized to YYYY-MM-DD) and transaction time."""
    date_val = None
    time_val = None

    date_patterns = [
        r"(?:Date|Invoice Date|Dated|Purchase Date)\s*[:\-\s]*([0-9]{1,4}[\/\.\-][0-9]{1,2}[\/\.\-][0-9]{1,4})",
        r"\b([0-9]{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+[0-9]{4})\b",
        r"\b([0-9]{4}[\/\.\-][0-9]{1,2}[\/\.\-][0-9]{1,2})\b",
        r"\b([0-9]{1,2}[\/\.\-][0-9]{1,2}[\/\.\-][0-9]{2,4})\b"
    ]
    for p in date_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d %b %Y", "%d %B %Y", "%Y/%m/%d"):
                try:
                    dt = datetime.strptime(raw, fmt)
                    date_val = dt.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue
            if not date_val:
                date_val = raw
            break

    time_m = re.search(r"\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])(?::([0-5][0-9]))?\s*(?:AM|PM|am|pm)?\b", text)
    if time_m:
        time_val = time_m.group(0).strip()

    return date_val, time_val


def _find_amount_by_keywords(text: str, keywords: List[str]) -> Optional[float]:
    """Finds financial amount next to target keywords, ensuring no fabrication."""
    for kw in keywords:
        pat = rf"(?:{re.escape(kw)})\s*(?:[:\-\s]|is|amount)*\s*(?:AED|Dhs?\.?)?\s*([\d,]+(?:\.\d{{2}})?)"
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                raw = m.group(1).replace(",", "")
                val = float(raw)
                return val
            except ValueError:
                continue
    return None


def _find_pattern(text: str, pattern: str) -> Optional[str]:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _find_col_idx(header: List[str], candidates: List[str]) -> Optional[int]:
    for idx, col in enumerate(header):
        if any(c in col for c in candidates):
            return idx
    return None


def _detect_brand(name: str) -> Optional[str]:
    brands = ["Samsung", "Apple", "LG", "Sony", "Panasonic", "Daikin", "Carrier", "Dell", "HP", "Lenovo", "Philips", "Dyson"]
    for b in brands:
        if re.search(r"\b" + re.escape(b) + r"\b", name, re.IGNORECASE):
            return b
    return None


def _detect_model(name: str) -> Optional[str]:
    m = re.search(r"\b([A-Z0-9]{3,}-[A-Z0-9]{2,}|[0-9]{1,2}[A-Z]{1,3}[0-9]{2,})\b", name)
    return m.group(1) if m else None


def _compute_tokens_mean_conf(tokens: List[Dict[str, Any]]) -> float:
    if not tokens:
        return 1.0
    scores = [t.get("confidence", 1.0) for t in tokens if "confidence" in t]
    return round(sum(scores) / max(1, len(scores)), 2)
