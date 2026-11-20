"""
Vercel Serverless Entrypoint for WordQuest 9 Backend API (Embedded 4-Microservices Gateway).
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
SHARED_DIR = BACKEND_DIR / "shared"
GATEWAY_DIR = BACKEND_DIR / "services" / "api_gateway"

for p in (SHARED_DIR, GATEWAY_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

os.environ["GATEWAY_MODE"] = "embedded"
os.environ.setdefault("DATA_DIR", str(ROOT_DIR / "data"))
if os.getenv("VERCEL") and not os.getenv("DATABASE_URL"):
    # Fallback to writable /tmp SQLite if Neon/Supabase DATABASE_URL is not yet configured
    os.environ["DATABASE_URL"] = "sqlite:////tmp/wordquest9.db"

from wordquest_shared.database import SessionLocal, init_db
from wordquest_shared.ingestion import ingest_notebook_data
from wordquest_shared.models import Unit
from main import app  # noqa: E402, F401


def _ensure_seeded() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(Unit).count() == 0:
            ingest_notebook_data(db=db, data_dir=ROOT_DIR / "data")
    finally:
        db.close()


_ensure_seeded()
