"""
CivicResolve AI - Warranty & After-Sales Intelligence Extractor
Extracts warranty terms, service agreements, return/exchange policies,
exclusions, and unambiguously calculates expiry dates.
"""
import re
from datetime import datetime
from typing import Dict, Any, Optional


def extract_warranty_information(text: str, purchase_date_str: Optional[str] = None) -> Dict[str, Any]:
    """
    Extracts structured warranty specifications, return windows, repair policies,
    and calculates expiry dates where unambiguous mathematical derivation is possible.
    """
    text_lower = text.lower()

    # 1. Warranty Duration Pattern
    duration_patterns = [
        r"(\d+)\s*(?:year|yr)s?\s*(?:full\s*)?(?:warranty|guarantee|coverage)",
        r"warranty\s*[:\-]?\s*(\d+)\s*(?:year|yr)s?",
        r"(\d+)\s*(?:month|mo)s?\s*(?:warranty|guarantee)",
        r"warranty\s*[:\-]?\s*(\d+)\s*(?:month|mo)s?",
        r"(lifetime)\s*(?:warranty|guarantee)",
        r"warranty\s*(?:period)?\s*[:\-]?\s*([0-9]+\s*(?:year|month|day)s?)"
    ]

    duration_str = None
    duration_months = None

    for pat in duration_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw_match = m.group(0).strip()
            val = m.group(1).strip()
            if "lifetime" in val.lower():
                duration_str = "Lifetime Warranty"
                duration_months = 1200
            elif "month" in raw_match.lower():
                try:
                    num = int(val)
                    duration_months = num
                    duration_str = f"{num} Month{'s' if num > 1 else ''}"
                except ValueError:
                    duration_str = raw_match
            elif "year" in raw_match.lower() or "yr" in raw_match.lower():
                try:
                    num = int(val)
                    duration_months = num * 12
                    duration_str = f"{num} Year{'s' if num > 1 else ''}"
                except ValueError:
                    duration_str = raw_match
            else:
                duration_str = raw_match
            break

    # 2. Warranty Provider / Coverage Type
    provider = None
    if re.search(r"\b(apple\s*care|applecare)\b", text_lower):
        provider = "AppleCare / Apple Official Warranty"
    elif re.search(r"\b(samsung\s*care|samsung\s*gulf)\b", text_lower):
        provider = "Samsung Gulf Authorized Warranty"
    elif re.search(r"\b(manufacturer\s*warranty|brand\s*warranty)\b", text_lower):
        provider = "Official Manufacturer Warranty"
    elif re.search(r"\b(seller|dealer|store|retailer)\s*warranty\b", text_lower):
        provider = "Dealer / Retailer Warranty"

    # 3. Return & Exchange Policy
    return_policy = None
    ret_m = re.search(r"(\d+)\s*days?\s*(?:return|exchange|replacement|refund)\b", text, re.IGNORECASE)
    if ret_m:
        return_policy = f"{ret_m.group(1)} Days Statutory Return / Exchange Policy"
    elif "14 days" in text_lower or "14-day" in text_lower:
        return_policy = "14 Days Statutory Return (UAE Consumer Protection Executive Regulations)"
    elif "no return" in text_lower or "no refund" in text_lower:
        return_policy = "Strict No-Return / No-Refund Disclaimed by Merchant (Subject to UAE Consumer Protection Law Article 10 Review)"

    # 4. Repair Conditions & Exclusions
    exclusions = []
    if re.search(r"\b(physical\s*damage|water\s*damage|liquid|screen\s*crack)\b", text_lower):
        exclusions.append("Physical / Liquid Damage excluded from standard repair coverage.")
    if re.search(r"\b(unauthorized\s*repair|tamper|seal\s*broken)\b", text_lower):
        exclusions.append("Warranty void if warranty seal broken or repaired by unauthorized center.")
    if re.search(r"\b(consumable|accessories|cable|battery)\b", text_lower):
        exclusions.append("Consumables, chargers, or batteries may carry limited or distinct warranty duration.")

    # 5. Customer Support / Service Center Contacts
    support_phone = None
    phone_m = re.search(r"(?:toll\s*free|service|support|helpdesk|hotline)\s*[:\s-]*(\+?971[\d\s-]{7,12}|800[\d\s-]{4,8}|04[\d\s-]{7,9})", text, re.IGNORECASE)
    if phone_m:
        support_phone = phone_m.group(1).strip()

    # 6. Unambiguous Expiry Date Calculation
    expiry_date = None
    expiry_status = "NOT FOUND"
    calculation_formula = None

    if duration_months and purchase_date_str:
        try:
            # Parse purchase date
            dt = None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"):
                try:
                    dt = datetime.strptime(purchase_date_str, fmt)
                    break
                except ValueError:
                    continue

            if dt:
                # Add duration_months
                new_year = dt.year + (dt.month + duration_months - 1) // 12
                new_month = (dt.month + duration_months - 1) % 12 + 1
                new_day = min(dt.day, 28)  # Safe day boundary
                exp_dt = datetime(new_year, new_month, new_day)
                expiry_date = exp_dt.strftime("%Y-%m-%d")
                expiry_status = "CALCULATED"
                calculation_formula = f"Derived: Start Date ({purchase_date_str}) + {duration_str}"
        except Exception:
            pass

    return {
        "warranty_duration": {
            "value": duration_str,
            "status": "VERIFIED" if duration_str else "NOT FOUND"
        },
        "warranty_provider": {
            "value": provider or "Authorized UAE Distributor",
            "status": "VERIFIED" if provider else "NOT FOUND"
        },
        "warranty_start_date": {
            "value": purchase_date_str,
            "status": "VERIFIED" if purchase_date_str else "NOT FOUND"
        },
        "warranty_expiry_date": {
            "value": expiry_date,
            "status": expiry_status,
            "calculation_formula": calculation_formula
        },
        "return_policy": {
            "value": return_policy,
            "status": "VERIFIED" if return_policy else "NOT FOUND"
        },
        "warranty_exclusions": exclusions,
        "support_contact": {
            "value": support_phone,
            "status": "VERIFIED" if support_phone else "NOT FOUND"
        }
    }
