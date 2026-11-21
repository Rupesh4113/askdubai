"""
CivicResolve AI - Vercel Serverless Function Handler (Repository Root)
Routes requests to the CivicResolve AI multi-agent FastAPI app.
Optimized for Vercel Serverless Lambda runtime (lightweight bundle, fast cold-start).
"""
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
# Check if running from inside api/ directory
if os.path.basename(REPO_ROOT) == "api":
    REPO_ROOT = os.path.dirname(REPO_ROOT)

CIVICRESOLVE_DIR = os.path.join(REPO_ROOT, "civicresolve-ai")

if CIVICRESOLVE_DIR not in sys.path:
    sys.path.insert(0, CIVICRESOLVE_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Set serverless environment flag
os.environ.setdefault("VERCEL", "1")
if "DATABASE_URL" not in os.environ:
    if os.name == "nt":
        db_path = os.path.join(tempfile.gettempdir(), "civicresolve.db").replace("\\", "/")
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    else:
        os.environ["DATABASE_URL"] = "sqlite:////tmp/civicresolve.db"

from database.database import init_db
from backend.main import app

# Resilient startup for serverless environment
try:
    init_db()
except Exception as e:
    print(f"[Vercel Startup] Database init notice: {e}")

# Export both app and handler for Vercel Serverless runtime
handler = app
