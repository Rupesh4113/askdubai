"""
CivicResolve AI - Complaint Classification Agent (Agent 2)
Classifies user grievances into standard consumer protection categories,
and extracts key transaction entities: merchant, date, amount, description, and requested resolution.
"""
import re
import json
from typing import Dict, Any, Optional
from agents.llm_client import call_llm

VALID_CATEGORIES = [
    "defective_product",
    "warranty_dispute",
    "refund_dispute",
    "delayed_delivery",
    "misleading_advertising",
    "poor_service",
    "incorrect_billing",
    "product_safety",
    "other"
]

CATEGORY_LABELS = {
    "defective_product": "Defective Product / Manufacturing Malfunction",
    "warranty_dispute": "Warranty Breach / Refusal to Repair",
    "refund_dispute": "Unlawful Refund Denial / Return Issue",
    "delayed_delivery": "Delayed Delivery / Supply Failure",
    "misleading_advertising": "Misleading Advertising / Price Deception",
    "poor_service": "Substandard Commercial Service",
    "incorrect_billing": "Incorrect Billing / Unauthorized Charge",
    "product_safety": "Product Safety Hazard",
    "other": "General Consumer Dispute"
}


def classify_complaint(text: str) -> Dict[str, Any]:
    """
    Classifies a natural language complaint description and extracts critical metadata.
    Uses LLM when available with strict JSON formatting, and deterministic regex/heuristic fallback.
    """
    clean_text = text.strip()
    if not clean_text:
        return {
            "category": "other",
            "category_label": CATEGORY_LABELS["other"],
            "confidence": 0.0,
            "merchant": None,
            "purchase_date": None,
            "amount": None,
            "currency": "AED",
            "problem_description": "",
            "requested_resolution": None
        }

    # Attempt LLM Classification
    llm_result = _classify_with_llm(clean_text)
    if llm_result:
        return llm_result

    # Fallback to high-precision semantic rule classifier
    return _classify_rule_based(clean_text)


def _classify_with_llm(text: str) -> Optional[Dict[str, Any]]:
    system_prompt = (
        "You are an expert UAE Consumer Protection Classification Agent for CivicResolve AI. "
        "Analyze the consumer complaint and output ONLY valid JSON with keys: "
        "category (one of: defective_product, warranty_dispute, refund_dispute, delayed_delivery, "
        "misleading_advertising, poor_service, incorrect_billing, product_safety, other), "
        "merchant (string or null), amount (number or null), currency (always AED), "
        "purchase_date (string or null), problem_description (concise summary), "
        "requested_resolution (replacement, refund, repair, billing_correction, or null), "
        "confidence (float between 0.0 and 1.0)."
    )
    prompt = f"Consumer complaint text:\n'''{text}'''\nProvide valid JSON output only:"

    response = call_llm(prompt, system_prompt=system_prompt)
    if response:
        try:
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                cat = data.get("category", "other").lower().strip()
                if cat not in VALID_CATEGORIES:
                    cat = "other"
                data["category"] = cat
                data["category_label"] = CATEGORY_LABELS.get(cat, CATEGORY_LABELS["other"])
                data["currency"] = data.get("currency") or "AED"
                return data
        except Exception:
            pass
    return None


def _classify_rule_based(text: str) -> Dict[str, Any]:
    clean_text = text.strip()
    lower = clean_text.lower()

    # Category Scoring
    scores = {cat: 0 for cat in VALID_CATEGORIES}

    # Defective product patterns
    if re.search(r"\b(defective|broken|stopped working|doesn't work|leaking|malfunction|faulty|damaged|not cooling|shut down|black screen|dead|burned out|burn out|heating element|stopped heating)\b", lower):
        scores["defective_product"] += 4
    if re.search(r"\b(air conditioner|ac|fridge|refrigerator|tv|phone|washing machine|appliance|compressor|oven|cooker|microwave)\b", lower):
        scores["defective_product"] += 2

    # Warranty dispute patterns
    if re.search(r"\b(warranty|guarantee|refused to repair|free service|service center|parts not available|within warranty)\b", lower):
        scores["warranty_dispute"] += 4

    # Refund dispute patterns
    if re.search(r"\b(refund|money back|return|returned|credit note|refusing to refund|denied return)\b", lower):
        scores["refund_dispute"] += 4

    # Delayed delivery patterns
    if re.search(r"\b(delayed|delivery|not delivered|shipping delay|has not arrived|waiting for delivery|where is my order|late shipment|postponed)\b", lower):
        scores["delayed_delivery"] += 5

    # Misleading advertising patterns
    if re.search(r"\b(misleading|false advertising|bait and switch|hidden fee|wrong price|different from picture|fake offer|deceptive)\b", lower):
        scores["misleading_advertising"] += 5

    # Incorrect billing patterns
    if re.search(r"\b(charged twice|overcharged|incorrect bill|unauthorized charge|double charge|extra charge|wrong amount charged|cashier charged|charged.*instead of|charged.*after cancellation|charged.*inactive|billing)\b", lower):
        scores["incorrect_billing"] += 5

    # Product safety patterns
    if re.search(r"\b(fire|spark|electric shock|explosion|hazard|toxic|poison|injury|burn|smoke)\b", lower):
        scores["product_safety"] += 6

    # Poor service patterns
    if re.search(r"\b(rude|unprofessional|poor service|bad customer support|no response|ignored calls|negligence)\b", lower):
        scores["poor_service"] += 3

    # Pick top category
    sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_cat, top_score = sorted_cats[0]
    if top_score < 2:
        best_cat = "other"
        confidence = 0.50
    else:
        confidence = min(0.98, 0.70 + (top_score * 0.05))

    # Entity Extraction
    # 1. Amount
    amount = None
    amt_match = re.search(r"(?:aed|dhs|dirhams|\$)?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?|[0-9]+)\s*(?:aed|dhs|dirhams)?", text, re.IGNORECASE)
    if amt_match:
        try:
            val = float(amt_match.group(1).replace(",", ""))
            if val > 1.0:
                amount = val
        except ValueError:
            pass

    # 2. Merchant
    merchant = None
    known_merchants = [
        "Sharaf DG", "Lulu", "Carrefour", "Emax", "Jumbo Electronics",
        "Amazon UAE", "Amazon", "Noon", "Jacky's Electronics", "Union Coop",
        "Al-Futtaim ACE", "Virgin Megastore", "IKEA", "Home Centre"
    ]
    for km in known_merchants:
        if re.search(r"\b" + re.escape(km) + r"\b", text, re.IGNORECASE):
            merchant = km
            break

    # 3. Date / Timeframe
    purchase_date = None
    date_match = re.search(r"\b(two weeks ago|2 weeks ago|last week|yesterday|a month ago|[0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})\b", text, re.IGNORECASE)
    if date_match:
        purchase_date = date_match.group(1).strip()

    # 4. Requested resolution
    requested_res = None
    if re.search(r"\b(replacement|replace)\b", lower):
        requested_res = "Immediate replacement of defective unit"
    elif re.search(r"\b(refund|money back|reimburse)\b", lower):
        requested_res = "Full refund to original payment method"
    elif re.search(r"\b(repair|fix)\b", lower):
        requested_res = "Free repair under statutory warranty"
    elif re.search(r"\b(delivery|deliver)\b", lower):
        requested_res = "Immediate fulfillment or order cancellation with full refund"

    return {
        "category": best_cat,
        "category_label": CATEGORY_LABELS[best_cat],
        "confidence": round(confidence, 2),
        "merchant": merchant,
        "purchase_date": purchase_date,
        "amount": amount,
        "currency": "AED",
        "problem_description": clean_text,
        "requested_resolution": requested_res
    }
