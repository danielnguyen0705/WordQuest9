from contextlib import asynccontextmanager
import os
import sys
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

SERVICES_DIR = Path(__file__).resolve().parents[1]
SHARED_DIR = SERVICES_DIR.parent / "shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

from wordquest_shared.config import settings
from wordquest_shared.database import SessionLocal, init_db
from wordquest_shared.ingestion import ingest_notebook_data
from wordquest_shared.models import Unit

GATEWAY_MODE = os.getenv("GATEWAY_MODE", "proxy").lower()  # "proxy" (Docker microservices) | "embedded" (single-process cloud deploy)

SERVICE_PREFIX_MAP = {
    "/api/v1/auth": settings.identity_service_url,
    "/api/v1/content": settings.vocabulary_service_url,
    "/api/v1/quiz": settings.quiz_engine_service_url,
    "/api/v1/progress": settings.progress_service_url,
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if GATEWAY_MODE == "embedded":
        init_db()
        db = SessionLocal()
        try:
            if db.query(Unit).count() == 0:
                ingest_notebook_data(db=db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="WordQuest 9 - API Gateway",
    version="1.0.0",
    description="Unified API Gateway routing requests across Identity, Vocabulary, Quiz Engine, and Progress microservices.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _mount_embedded_routers() -> None:
    import importlib.util

    service_specs = [
        ("identity_service", SERVICES_DIR / "identity_service" / "routes.py"),
        ("vocabulary_service", SERVICES_DIR / "vocabulary_service" / "routes.py"),
        ("quiz_engine_service", SERVICES_DIR / "quiz_engine_service" / "routes.py"),
        ("progress_service", SERVICES_DIR / "progress_service" / "routes.py"),
    ]
    for name, route_file in service_specs:
        service_dir = str(route_file.parent)
        if service_dir not in sys.path:
            sys.path.insert(0, service_dir)
        spec = importlib.util.spec_from_file_location(f"wq_{name}_routes", route_file)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            app.include_router(mod.router)


if GATEWAY_MODE == "embedded":
    _mount_embedded_routers()


@app.get("/health")
async def gateway_health():
    if GATEWAY_MODE == "embedded":
        return {
            "service": "api-gateway",
            "mode": "embedded",
            "status": "ok",
            "services": {
                "identity": "ok",
                "vocabulary": "ok",
                "quiz_engine": "ok",
                "progress": "ok",
            },
        }

    statuses: dict[str, str] = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for prefix, base_url in SERVICE_PREFIX_MAP.items():
            svc_name = prefix.split("/")[-1]
            try:
                resp = await client.get(f"{base_url}/health")
                statuses[svc_name] = "ok" if resp.status_code == 200 else f"error:{resp.status_code}"
            except Exception as exc:
                statuses[svc_name] = f"unreachable:{type(exc).__name__}"

    overall = "ok" if all(v == "ok" for v in statuses.values()) else "degraded"
    return {
        "service": "api-gateway",
        "mode": "proxy",
        "status": overall,
        "services": statuses,
    }


if GATEWAY_MODE != "embedded":
    @app.api_route("/api/v1/{service_group}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    @app.api_route("/api/v1/{service_group}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def proxy_request(service_group: str, request: Request, path: str = ""):
        prefix = f"/api/v1/{service_group}"
        target_base = SERVICE_PREFIX_MAP.get(prefix)
        if not target_base:
            return Response(content='{"detail":"Unknown service route"}', status_code=404, media_type="application/json")

        target_url = f"{target_base}{prefix}"
        if path:
            target_url = f"{target_url}/{path}"
        if request.url.query:
            target_url = f"{target_url}?{request.url.query}"

        headers = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in ("host", "content-length")
        }
        body = await request.body()

        async with httpx.AsyncClient(timeout=30.0) as client:
            upstream = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
            )

        excluded = {"content-encoding", "transfer-encoding", "connection", "content-length"}
        resp_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in excluded}
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=resp_headers,
            media_type=upstream.headers.get("content-type"),
        )
