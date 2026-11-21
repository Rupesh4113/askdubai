"""
CivicResolve AI - Dedicated Document Intelligence Processing Microservice
Standalone Docker-deployable FastAPI service hosting heavyweight OCR (PaddleOCR/RapidOCR),
OpenCV image preprocessing, PyMuPDF rendering, and full financial/VAT validation.
"""
import os
import sys
import json
from typing import Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure root paths are in sys.path
SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SERVICE_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from document_processing.document_upload import (
    process_uploaded_document,
    get_cached_document,
    get_cached_page_preview
)
from document_processing.report_generator import (
    export_document_json,
    export_document_csv,
    export_document_excel,
    export_document_pdf
)

app = FastAPI(
    title="CivicResolve AI - Document Intelligence Service",
    description="Heavyweight document parsing, OCR, and financial validation microservice",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint reporting microservice status and available engines."""
    engines = {
        "pymupdf": False,
        "opencv": False,
        "ocr": False,
        "reportlab": False,
        "openpyxl": False
    }
    try:
        import fitz
        engines["pymupdf"] = True
    except ImportError:
        pass
    try:
        import cv2
        engines["opencv"] = True
    except ImportError:
        pass
    try:
        import reportlab
        engines["reportlab"] = True
    except ImportError:
        pass
    try:
        import openpyxl
        engines["openpyxl"] = True
    except ImportError:
        pass

    return {
        "status": "healthy",
        "service": "CivicResolve AI - Document Intelligence Microservice",
        "version": "1.0.0",
        "engines": engines
    }


@app.post("/api/v1/documents/process", tags=["Processing"])
async def process_document(
    file: UploadFile = File(...),
    complaint_data: Optional[str] = Form(None)
):
    """
    Receives uploaded invoice/receipt bytes from the Vercel API or client.
    Executes full multi-page PyMuPDF, OpenCV preprocessing, RapidOCR,
    and Sections A-H master extraction with mathematical and UAE VAT compliance auditing.
    """
    try:
        file_bytes = await file.read()
        parsed_complaint = None
        if complaint_data:
            try:
                parsed_complaint = json.loads(complaint_data)
            except Exception:
                pass

        doc_res = process_uploaded_document(
            file_bytes=file_bytes,
            filename=file.filename,
            complaint_data=parsed_complaint
        )
        return doc_res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Heavyweight document processing error: {str(e)}"
        )


@app.get("/api/v1/documents/{document_id}/page/{page_number}/image", tags=["Previews"])
def get_page_preview(document_id: str, page_number: int = 1):
    """Returns high-resolution rendered PNG preview of a document page."""
    png_bytes = get_cached_page_preview(document_id, page_number)
    if not png_bytes:
        raise HTTPException(status_code=404, detail="Page preview image not found in service cache.")
    return Response(content=png_bytes, media_type="image/png")


@app.post("/api/v1/documents/export/{export_format}", tags=["Exports"])
async def export_document(export_format: str, payload: Dict[str, Any]):
    """Generates structured exports (json, csv, excel, pdf) from document intelligence payload."""
    fmt = export_format.lower()
    if fmt == "json":
        return Response(content=export_document_json(payload), media_type="application/json")
    elif fmt == "csv":
        return Response(content=export_document_csv(payload), media_type="text/csv")
    elif fmt == "excel":
        try:
            return Response(
                content=export_document_excel(payload),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    elif fmt == "pdf":
        try:
            return Response(
                content=export_document_pdf(payload),
                media_type="application/pdf"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{export_format}'")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
