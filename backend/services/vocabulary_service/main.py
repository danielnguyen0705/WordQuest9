from contextlib import asynccontextmanager
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

SHARED_DIR = Path(__file__).resolve().parents[2] / "shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

from wordquest_shared.config import settings
from wordquest_shared.database import SessionLocal, init_db
from wordquest_shared.ingestion import ingest_notebook_data
from wordquest_shared.models import Unit
from routes import router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    # Auto-seed from data/ directory if units table is empty
    db = SessionLocal()
    try:
        if db.query(Unit).count() == 0:
            ingest_notebook_data(db=db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="WordQuest 9 - Vocabulary & Content Service",
    version="1.0.0",
    description="Manages Tiếng Anh 9 Units, Vocabularies, Word Forms, Question Bank, and Notebook JSON ingestion.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"service": "vocabulary-service", "status": "ok"}
