"""
CivicResolve AI - Document Intelligence Export & Report Generator
Generates structured exports in JSON, CSV, Excel (.xlsx), and PDF formats.
"""
import io
import csv
import json
from typing import Dict, Any

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    openpyxl = None

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
except ImportError:
    SimpleDocTemplate = None


def export_document_json(doc_data: Dict[str, Any]) -> str:
    """Exports full document intelligence payload as formatted JSON string."""
    return json.dumps(doc_data, indent=2, ensure_ascii=False)


def export_document_csv(doc_data: Dict[str, Any]) -> str:
    """Exports document metadata and structured line items as CSV text."""
    intel = doc_data.get("extracted_intelligence", {})
    output = io.StringIO()
    writer = csv.writer(output)

    # Header section
    writer.writerow(["CivicResolve AI - Document Intelligence Export"])
    writer.writerow(["Document ID", doc_data.get("document_id", "")])
    writer.writerow(["Filename", doc_data.get("filename", "")])
    writer.writerow(["Document Classification", doc_data.get("type_display", "")])
    writer.writerow(["Invoice Number", intel.get("invoice_information", {}).get("invoice_number", {}).get("value", "")])
    writer.writerow(["Invoice Date", intel.get("invoice_information", {}).get("invoice_date", {}).get("value", "")])
    writer.writerow(["Validation Status", doc_data.get("validation_status", "")])
    writer.writerow(["Confidence Score", f"{int(doc_data.get('confidence_score', 0) * 100)}%"])
    writer.writerow([])

    # Merchant Information
    merch = intel.get("merchant_information", {})
    writer.writerow(["--- MERCHANT / SELLER DETAILS ---"])
    writer.writerow(["Business Name", merch.get("business_name", {}).get("value", "")])
    writer.writerow(["TRN", merch.get("trn", {}).get("value", "")])
    writer.writerow(["Address", merch.get("business_address", {}).get("value", "")])
    writer.writerow(["Emirate", merch.get("emirate", {}).get("value", "")])
    writer.writerow([])

    # Line Items
    items = intel.get("product_service_details", [])
    writer.writerow(["--- LINE ITEMS TABLE ---"])
    writer.writerow(["S.No", "Product Name", "Brand", "Model", "Qty", "Unit Price (AED)", "Taxable Amount (AED)", "VAT (5%)", "Total (AED)"])
    for itm in items:
        writer.writerow([
            itm.get("serial_number", ""),
            itm.get("product_name", ""),
            itm.get("brand", ""),
            itm.get("model_number", ""),
            itm.get("quantity", ""),
            itm.get("unit_price", ""),
            itm.get("taxable_amount", ""),
            itm.get("vat_amount", ""),
            itm.get("line_item_total", "")
        ])
    writer.writerow([])

    # Financial Summary
    fin = intel.get("financial_summary", {})
    writer.writerow(["--- FINANCIAL RECONCILIATION ---"])
    writer.writerow(["Subtotal before VAT", fin.get("subtotal", {}).get("value", "")])
    writer.writerow(["VAT Amount (5%)", fin.get("vat_amount", {}).get("value", "")])
    writer.writerow(["Discounts", fin.get("total_discounts", {}).get("value", "")])
    writer.writerow(["Delivery & Charges", fin.get("additional_charges", {}).get("value", "")])
    writer.writerow(["Total Payable (Gross)", fin.get("total_payable", {}).get("value", "")])
    writer.writerow(["Amount Paid", fin.get("amount_paid", {}).get("value", "")])
    writer.writerow(["Outstanding Balance", fin.get("outstanding_balance", {}).get("value", "")])

    return output.getvalue()


def export_document_excel(doc_data: Dict[str, Any]) -> bytes:
    """Generates styled multi-tab Excel workbook (.xlsx)."""
    if openpyxl is None:
        raise RuntimeError("openpyxl is not installed.")

    wb = openpyxl.Workbook()
    intel = doc_data.get("extracted_intelligence", {})

    # Tab 1: Overview
    ws1 = wb.active
    ws1.title = "Overview & Parties"
    ws1.views.sheetView[0].showGridLines = True

    header_font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
    section_fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
    bold_font = Font(name="Calibri", size=11, bold=True)

    ws1.merge_cells("A1:D1")
    ws1["A1"] = "CivicResolve AI - Document Intelligence & Verification Report"
    ws1["A1"].font = header_font
    ws1["A1"].fill = header_fill
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")

    meta_rows = [
        ("Document ID", doc_data.get("document_id", "")),
        ("Original Filename", doc_data.get("filename", "")),
        ("Document Type", doc_data.get("type_display", "")),
        ("Validation Status", doc_data.get("validation_status", "")),
        ("Verification Confidence", f"{int(doc_data.get('confidence_score', 0) * 100)}%"),
        ("Pages Processed", doc_data.get("page_count", 1))
    ]

    r_idx = 3
    for label, val in meta_rows:
        ws1.cell(row=r_idx, column=1, value=label).font = bold_font
        ws1.cell(row=r_idx, column=2, value=str(val))
        r_idx += 1

    r_idx += 1
    ws1.cell(row=r_idx, column=1, value="MERCHANT / SELLER INFORMATION").fill = section_fill
    ws1.cell(row=r_idx, column=1).font = bold_font
    r_idx += 1

    merch = intel.get("merchant_information", {})
    merch_rows = [
        ("Business Name", merch.get("business_name", {}).get("value", "Not Found")),
        ("TRN (VAT ID)", merch.get("trn", {}).get("value", "Not Found")),
        ("Address", merch.get("business_address", {}).get("value", "Not Found")),
        ("Emirate", merch.get("emirate", {}).get("value", "Not Found")),
        ("Phone", merch.get("contact_number", {}).get("value", "Not Found")),
        ("Email", merch.get("email_address", {}).get("value", "Not Found"))
    ]
    for label, val in merch_rows:
        ws1.cell(row=r_idx, column=1, value=label).font = bold_font
        ws1.cell(row=r_idx, column=2, value=str(val))
        r_idx += 1

    # Tab 2: Line Items
    ws2 = wb.create_sheet(title="Line Items")
    ws2.views.sheetView[0].showGridLines = True
    th_fill = PatternFill(start_color="0D9488", end_color="0D9488", fill_type="solid")
    th_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    headers = ["S.No", "Product / Service", "Brand", "Model", "Qty", "Unit Price", "Discount", "Taxable Amount", "VAT (5%)", "Line Total (AED)"]
    for c_idx, h in enumerate(headers, start=1):
        c = ws2.cell(row=1, column=c_idx, value=h)
        c.fill = th_fill
        c.font = th_font
        c.alignment = Alignment(horizontal="center")

    items = intel.get("product_service_details", [])
    for row_idx, itm in enumerate(items, start=2):
        ws2.cell(row=row_idx, column=1, value=itm.get("serial_number"))
        ws2.cell(row=row_idx, column=2, value=itm.get("product_name"))
        ws2.cell(row=row_idx, column=3, value=itm.get("brand") or "-")
        ws2.cell(row=row_idx, column=4, value=itm.get("model_number") or "-")
        ws2.cell(row=row_idx, column=5, value=itm.get("quantity"))
        ws2.cell(row=row_idx, column=6, value=itm.get("unit_price"))
        ws2.cell(row=row_idx, column=7, value=itm.get("discount") or 0.0)
        ws2.cell(row=row_idx, column=8, value=itm.get("taxable_amount"))
        ws2.cell(row=row_idx, column=9, value=itm.get("vat_amount"))
        ws2.cell(row=row_idx, column=10, value=itm.get("line_item_total"))

    # Tab 3: Traceability Log
    ws3 = wb.create_sheet(title="Source Traceability")
    ws3.views.sheetView[0].showGridLines = True
    t_headers = ["Field Key", "Field Name", "Extracted Value", "Status", "OCR Confidence", "Page", "Bounding Box"]
    for c_idx, h in enumerate(t_headers, start=1):
        c = ws3.cell(row=1, column=c_idx, value=h)
        c.fill = th_fill
        c.font = th_font

    trace_records = intel.get("source_traceability", [])
    for row_idx, rec in enumerate(trace_records, start=2):
        ws3.cell(row=row_idx, column=1, value=rec.get("field_key"))
        ws3.cell(row=row_idx, column=2, value=rec.get("field_name"))
        ws3.cell(row=row_idx, column=3, value=str(rec.get("value") or "Not Found"))
        ws3.cell(row=row_idx, column=4, value=rec.get("status"))
        ws3.cell(row=row_idx, column=5, value=f"{int(rec.get('ocr_confidence', 0) * 100)}%")
        ws3.cell(row=row_idx, column=6, value=rec.get("page_number"))
        ws3.cell(row=row_idx, column=7, value=str(rec.get("bbox") or "N/A"))

    # Auto-adjust column widths
    for sheet in [ws1, ws2, ws3]:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_document_pdf(doc_data: Dict[str, Any]) -> bytes:
    """Generates formal PDF Evidence & Verification Audit Report."""
    if SimpleDocTemplate is None:
        raise RuntimeError("reportlab is not installed.")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F766E")
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569")
    )
    h2_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0F172A")
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1E293B")
    )

    story = []

    # Title
    story.append(Paragraph("CivicResolve AI | Document Intelligence & Evidence Report", title_style))
    story.append(Paragraph("Automated Evidence Extraction & UAE Consumer Protection Verification Audit", subtitle_style))
    story.append(Spacer(1, 14))

    # Overview Table
    intel = doc_data.get("extracted_intelligence", {})
    merch = intel.get("merchant_information", {})
    inv = intel.get("invoice_information", {})
    fin = intel.get("financial_summary", {})
    acc = intel.get("accuracy_and_validation_report", {})

    status_badge = doc_data.get("validation_status", "REVIEW REQUIRED")
    conf_pct = f"{int(doc_data.get('confidence_score', 0) * 100)}%"

    overview_data = [
        [Paragraph("<b>Document ID:</b>", body_style), Paragraph(doc_data.get("document_id", ""), body_style),
         Paragraph("<b>Validation Status:</b>", body_style), Paragraph(f"<b>{status_badge}</b> ({conf_pct})", body_style)],
        [Paragraph("<b>Document Type:</b>", body_style), Paragraph(doc_data.get("type_display", ""), body_style),
         Paragraph("<b>Invoice No:</b>", body_style), Paragraph(inv.get("invoice_number", {}).get("value") or "Not Found", body_style)],
        [Paragraph("<b>Merchant Name:</b>", body_style), Paragraph(merch.get("business_name", {}).get("value") or "Not Found", body_style),
         Paragraph("<b>Invoice Date:</b>", body_style), Paragraph(inv.get("invoice_date", {}).get("value") or "Not Found", body_style)],
        [Paragraph("<b>Supplier TRN:</b>", body_style), Paragraph(merch.get("trn", {}).get("value") or "Not Found", body_style),
         Paragraph("<b>Total Payable:</b>", body_style), Paragraph(f"AED {fin.get('total_payable', {}).get('value', '0.00')}", body_style)]
    ]

    t_overview = Table(overview_data, colWidths=[110, 150, 110, 150])
    t_overview.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_overview)
    story.append(Spacer(1, 14))

    # Line Items Section
    story.append(Paragraph("Product & Service Details (Itemized Table)", h2_style))
    story.append(Spacer(1, 6))

    items = intel.get("product_service_details", [])
    if items:
        table_rows = [["S.No", "Description", "Brand/Model", "Qty", "Unit Price", "Total (AED)"]]
        for itm in items:
            bm = f"{itm.get('brand') or ''} {itm.get('model_number') or ''}".strip() or "-"
            table_rows.append([
                str(itm.get("serial_number", "")),
                itm.get("product_name", ""),
                bm,
                str(itm.get("quantity", 1)),
                f"{itm.get('unit_price', 0):.2f}" if itm.get('unit_price') is not None else "-",
                f"{itm.get('line_item_total', 0):.2f}" if itm.get('line_item_total') is not None else "-"
            ])
        t_items = Table(table_rows, colWidths=[35, 230, 95, 40, 60, 60])
        t_items.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F766E")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_items)
    else:
        story.append(Paragraph("<i>No itemized product rows detected in document.</i>", body_style))
    story.append(Spacer(1, 14))

    # UAE VAT & Mathematical Verification Summary
    story.append(Paragraph("UAE Tax Compliance & Financial Verification", h2_style))
    story.append(Spacer(1, 6))

    vat_info = intel.get("vat_compliance_information", {})
    fin_audit = intel.get("financial_audit", {})
    vat_status = vat_info.get("compliance_status", "PENDING")
    math_status = fin_audit.get("math_validation_status", "VERIFIED")

    audit_summary_p = (
        f"<b>UAE VAT Standard:</b> {vat_info.get('classification', 'Tax Invoice')} | "
        f"<b>Compliance Rating:</b> {vat_status}<br/>"
        f"<b>Mathematical Integrity:</b> {math_status}<br/>"
        f"<b>Discrepancies:</b> {len(fin_audit.get('discrepancies', []))} flagged."
    )
    story.append(Paragraph(audit_summary_p, body_style))
    story.append(Spacer(1, 14))

    # Legal Disclaimer
    disclaimer = (
        "<b>Notice:</b> This document intelligence report was generated by CivicResolve AI through multi-layered "
        "OCR, layout analysis, and arithmetic cross-verification. Extracted values are linked to original source coordinates. "
        "This report supports consumer dispute filing under UAE Federal Law No. 15 of 2020."
    )
    story.append(Paragraph(disclaimer, subtitle_style))

    doc.build(story)
    return buf.getvalue()
