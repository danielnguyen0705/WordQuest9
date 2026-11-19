from contextlib import asynccontextmanager
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

SHARED_DIR = Path(__file__).resolve().parents[2] / "shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

from wordquest_shared.config import settings
from wordquest_shared.database import init_db
from routes import router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="WordQuest 9 - Quiz & Game Engine Service",
    version="1.0.0",
    description="Hybrid Quiz Generator (Notebook Bank + Dynamic Generation), Flashcard Warm-up, Sudden-Death 1-Life Reset Engine, and Mistake Revenge orchestration.",
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
    return {"service": "quiz-engine-service", "status": "ok"}
