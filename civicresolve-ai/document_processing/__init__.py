"""
CivicResolve AI - Advanced Document Intelligence Module
Exports core processing pipelines, extractors, validators, and report generators.
"""
from document_processing.document_upload import process_uploaded_document, get_cached_document, get_cached_page_preview
from document_processing.document_classifier import classify_document
from document_processing.pdf_processor import inspect_and_process_pdf, PDFProcessingError
from document_processing.image_preprocessor import preprocess_image_bytes
from document_processing.ocr_engine import run_ocr_on_image
from document_processing.document_extractor import extract_all_document_intelligence
from document_processing.financial_validator import validate_financial_calculations
from document_processing.vat_validator import assess_uae_vat_compliance, validate_uae_trn
from document_processing.warranty_extractor import extract_warranty_information
from document_processing.confidence_engine import evaluate_document_accuracy
from document_processing.duplicate_detector import check_for_duplicate
from document_processing.report_generator import (
    export_document_json,
    export_document_csv,
    export_document_excel,
    export_document_pdf
)
from document_processing.invoice_parser import parse_invoice_text
from document_processing.validator import validate_document_fields, assess_missing_documents_for_category

__all__ = [
    "process_uploaded_document",
    "get_cached_document",
    "get_cached_page_preview",
    "classify_document",
    "inspect_and_process_pdf",
    "PDFProcessingError",
    "preprocess_image_bytes",
    "run_ocr_on_image",
    "extract_all_document_intelligence",
    "validate_financial_calculations",
    "assess_uae_vat_compliance",
    "validate_uae_trn",
    "extract_warranty_information",
    "evaluate_document_accuracy",
    "check_for_duplicate",
    "export_document_json",
    "export_document_csv",
    "export_document_excel",
    "export_document_pdf",
    "parse_invoice_text",
    "validate_document_fields",
    "assess_missing_documents_for_category"
]
