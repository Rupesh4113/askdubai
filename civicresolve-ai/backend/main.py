"""
CivicResolve AI - FastAPI Application Server
Multi-agent backend connecting LangGraph, FAISS RAG, and Document Intelligence.
"""
import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database.database import init_db
from rag.ingestion import build_faiss_index
from agents.llm_client import check_ollama_status

# Import routers
from backend.routes.auth import router as auth_router
from backend.routes.complaints import router as complaints_router
from backend.routes.documents import router as documents_router
from backend.routes.chat import router as chat_router
from backend.routes.approvals import router as approvals_router

app = FastAPI(
    title="CivicResolve AI API",
    description="Multilingual AI-Powered Consumer Dispute Resolution System for Dubai and the UAE",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(complaints_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(approvals_router)

# Ensure database tables are created immediately
init_db()


@app.on_event("startup")
def on_startup():
    """Initializes SQLite database and FAISS official knowledge index."""
    print("[Startup] Initializing database schema...")
    init_db()
    print("[Startup] Ensuring official knowledge base FAISS index...")
    build_faiss_index()
    ollama_info = check_ollama_status()
    print(f"[Startup] LLM Status: {'Available' if ollama_info['available'] else 'Offline/Fallback'} (Active: {ollama_info['active_model']})")


@app.get("/api/v1/health", tags=["Health"])
def health_check():
    """Health check endpoint reporting system components and LLM status."""
    ollama_info = check_ollama_status()
    return {
        "status": "healthy",
        "service": "CivicResolve AI",
        "version": "1.0.0",
        "jurisdiction": "Dubai / United Arab Emirates",
        "llm_engine": ollama_info,
        "database": "sqlite_connected"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred in CivicResolve AI.", "error_type": type(exc).__name__}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
