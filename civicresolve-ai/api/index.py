"""
CivicResolve AI - Vercel Serverless Function Handler
Entrypoint for Vercel deployment of FastAPI backend and Multi-Agent API.
"""
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

SUB_DIR = os.path.join(PROJECT_ROOT, "civicresolve-ai")
if os.path.exists(SUB_DIR) and SUB_DIR not in sys.path:
    sys.path.insert(0, SUB_DIR)

from database.database import init_db
from rag.ingestion import build_faiss_index
from backend.main import app

# Safe startup for serverless environment
try:
    init_db()
except Exception as e:
    print(f"[Vercel Startup] Database init notice: {e}")

try:
    build_faiss_index()
except Exception as e:
    print(f"[Vercel Startup] FAISS index notice: {e}")

# Export both app and handler for Vercel Serverless runtime
handler = app
