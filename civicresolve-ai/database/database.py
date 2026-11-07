"""
CivicResolve AI - Database Connection and Session Management
Supports SQLite for MVP development and is fully compatible with PostgreSQL.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "")

# In Vercel serverless functions, the root filesystem is read-only; use /tmp for SQLite
if not DATABASE_URL:
    if os.getenv("VERCEL") == "1" or os.path.exists("/tmp"):
        DATABASE_URL = "sqlite:////tmp/civicresolve.db"
    else:
        DATABASE_URL = "sqlite:///./civicresolve.db"
elif DATABASE_URL.startswith("sqlite:///./") and (os.getenv("VERCEL") == "1" or os.name != "nt" and os.path.exists("/tmp")):
    DATABASE_URL = "sqlite:////tmp/civicresolve.db"

# SQLite thread safety configuration
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency injection helper for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables in the configured database."""
    from database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
