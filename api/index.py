"""
CivicResolve AI - Vercel Serverless Function Handler (Repository Root)
Routes requests to the CivicResolve AI multi-agent FastAPI app.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIVICRESOLVE_DIR = os.path.join(REPO_ROOT, "civicresolve-ai")

if CIVICRESOLVE_DIR not in sys.path:
    sys.path.insert(0, CIVICRESOLVE_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

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
