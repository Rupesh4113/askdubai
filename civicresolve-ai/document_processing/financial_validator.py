"""
CivicResolve AI - Financial & Mathematical Verification Engine
Independently verifies invoice subtotals, VAT amounts, discounts, and balances.
Flags discrepancies without modifying original printed invoice values.
"""
from typing import Dict, Any, List, Optional


def validate_financial_calculations(
    subtotal: Optional[float],
    vat_amount: Optional[float],
    vat_rate: Optional[float],
    discounts: Optional[float],
    additional_charges: Optional[float],
    printed_total: Optional[float],
    amount_paid: Optional[float] = None,
    outstanding_balance: Optional[float] = None,
    line_items: Optional[List[Dict[str, Any]]] = None,
    currency: str = "AED"
) -> Dict[str, Any]:
    """
    Performs rigorous 5-point mathematical verification:
    1. Line items sum check vs subtotal
    2. Subtotal + VAT + Charges - Discounts == Total
    3. Taxable Amount * VAT Rate == VAT Amount
    4. Amount Paid + Outstanding Balance == Total
    5. Discrepancy flagging (preserves printed value, never silently overwrites)
    """
    discrepancies = []
    audit_notes = []
    math_status = "VERIFIED"

    # Normalize optional inputs
    disc = discounts if discounts is not None else 0.0
    charges = additional_charges if additional_charges is not None else 0.0

    # 1. Line items sum validation
    calculated_line_total = 0.0
    has_line_items = False
    if line_items and len(line_items) > 0:
        has_line_items = True
        for idx, item in enumerate(line_items):
            item_total = item.get("total") or item.get("line_item_total")
            if item_total is not None:
                calculated_line_total += float(item_total)

        if subtotal is not None and abs(calculated_line_total - subtotal) > 0.10:
            diff = round(calculated_line_total - subtotal, 2)
            discrepancies.append(
                f"Line Items Sum discrepancy: Sum of items is {currency} {calculated_line_total:.2f}, "
                f"but printed Subtotal is {currency} {subtotal:.2f} (Difference: {currency} {diff:+.2f})."
            )
            math_status = "REVIEW REQUIRED"
        elif subtotal is not None:
            audit_notes.append(f"Line items sum ({currency} {calculated_line_total:.2f}) matches printed Subtotal.")

    # 2. Subtotal + VAT + Charges - Discounts == Printed Total
    expected_total = None
    if subtotal is not None and vat_amount is not None:
        expected_total = round(subtotal + vat_amount + charges - disc, 2)
        if printed_total is not None:
            diff = round(expected_total - printed_total, 2)
            if abs(diff) > 0.05:
                discrepancies.append(
                    f"Grand Total Discrepancy: Printed Total is {currency} {printed_total:.2f}, "
                    f"but Subtotal ({subtotal:.2f}) + VAT ({vat_amount:.2f}) + Charges ({charges:.2f}) - Discounts ({disc:.2f}) "
                    f"equals {currency} {expected_total:.2f} (Discrepancy: {currency} {diff:+.2f})."
                )
                math_status = "REVIEW REQUIRED"
            else:
                audit_notes.append(f"Mathematical equation verified: Subtotal + VAT + Charges - Discounts = Printed Total ({currency} {printed_total:.2f}).")

    # 3. VAT Rate vs VAT Amount check
    if subtotal is not None and vat_rate is not None and vat_amount is not None:
        expected_vat = round(subtotal * (vat_rate / 100.0), 2)
        vat_diff = round(expected_vat - vat_amount, 2)
        if abs(vat_diff) > 0.10:
            discrepancies.append(
                f"VAT calculation mismatch: Based on {vat_rate}% of Subtotal ({subtotal:.2f}), "
                f"expected VAT is {currency} {expected_vat:.2f}, but printed VAT is {currency} {vat_amount:.2f} (Difference: {currency} {vat_diff:+.2f})."
            )
            math_status = "REVIEW REQUIRED"
        else:
            audit_notes.append(f"VAT calculation verified: {vat_rate}% of {currency} {subtotal:.2f} = {currency} {vat_amount:.2f}.")

    # 4. Payment & Balance Check
    if printed_total is not None and amount_paid is not None:
        expected_balance = max(0.0, round(printed_total - amount_paid, 2))
        if outstanding_balance is not None and abs(expected_balance - outstanding_balance) > 0.10:
            discrepancies.append(
                f"Balance mismatch: Expected Outstanding Balance ({currency} {expected_balance:.2f}), "
                f"printed balance is {currency} {outstanding_balance:.2f}."
            )
            math_status = "REVIEW REQUIRED"
        elif outstanding_balance is not None:
            audit_notes.append(f"Payment reconciliation verified: Amount Paid ({currency} {amount_paid:.2f}) + Balance ({currency} {outstanding_balance:.2f}) = {currency} {printed_total:.2f}.")

    return {
        "math_validation_status": math_status,
        "is_mathematically_consistent": len(discrepancies) == 0,
        "calculated_line_total": round(calculated_line_total, 2) if has_line_items else None,
        "expected_total": expected_total,
        "printed_total_preserved": printed_total,
        "discrepancies": discrepancies,
        "audit_notes": audit_notes
    }
