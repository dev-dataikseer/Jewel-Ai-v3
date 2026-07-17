from contextlib import asynccontextmanager
from pathlib import Path

import redis
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routers import assets, auth, billing, jobs, misc, models, prompts, providers, public, storage_files, users
from app.config import get_settings, validate_production_settings, assert_production_settings
from app.database import Base, SessionLocal, engine
import app.models  # noqa: F401 — register all tables before create_all
from app.logging_config import setup_logging
from app.providers import circuit_breaker
from app.middleware.rate_limit import RateLimitMiddleware
from app.storage.local import storage
from app.tasks.generate import sweep_stuck_jobs
from seeds.run_seeds import run_all_seeds

settings = get_settings()
setup_logging()

APP_VERSION = "4.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # When SCHEMA_VIA_ALEMBIC=true, operators run `alembic upgrade head` instead of create_all.
    if not settings.schema_via_alembic:
        Base.metadata.create_all(bind=engine)
        from app.pipeline.db_migrate import (
            migrate_layer_columns,
            migrate_job_indexes,
            migrate_tenancy_columns,
            migrate_batch_user_column,
        )

        migrate_layer_columns(engine)
        migrate_job_indexes(engine)
        migrate_tenancy_columns(engine)
        migrate_batch_user_column(engine)
    db = SessionLocal()
    try:
        from app.pipeline.db_migrate import migrate_workflow_subjects

        migrate_workflow_subjects(db)
        run_all_seeds(db)
        sweep_stuck_jobs()
    finally:
        db.close()
    circuit_breaker.init_circuit_breaker()
    # Warm fal credits cache in background — never block startup / generation
    try:
        import threading

        def _warm_credits() -> None:
            db_local = SessionLocal()
            try:
                from app.providers.fal_billing.service import get_credits_view

                get_credits_view(db_local, refresh=True)
            except Exception:
                pass
            finally:
                db_local.close()

        threading.Thread(target=_warm_credits, daemon=True, name="fal-credits-warm").start()
    except Exception:
        pass
    if settings.is_production:
        assert_production_settings()
    for warning in validate_production_settings():
        import logging

        logging.getLogger(__name__).warning("Production config: %s", warning)
    yield


_docs_url = None if settings.is_production else "/docs"
_redoc_url = None if settings.is_production else "/redoc"

app = FastAPI(
    title="Jewel V4 API",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob: https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'",
        )
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

if storage.uses_object_storage:
    app.include_router(storage_files.router)
else:
    uploads_path = Path(settings.uploads_dir)
    uploads_path.mkdir(parents=True, exist_ok=True)
    # Always serve via signed/auth router (no anonymous StaticFiles).
    app.include_router(storage_files.router)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(prompts.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(misc.router, prefix="/api")
app.include_router(public.router, prefix="/api")


@app.get("/health")
def health():
    """Liveness — process is up (no dependency checks)."""
    return {"status": "ok", "service": "jewel-ai-api", "version": APP_VERSION}


@app.get("/ready")
def ready(response: Response):
    """Readiness — DB + Redis required for traffic."""
    db_ok = False
    redis_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    try:
        r = redis.from_url(settings.redis_url, socket_connect_timeout=1)
        redis_ok = bool(r.ping())
    except Exception:
        pass
    ok = db_ok and redis_ok
    if not ok:
        response.status_code = 503
    return {
        "status": "ok" if ok else "not_ready",
        "service": "jewel-ai-api",
        "database": db_ok,
        "redis": redis_ok,
        "version": APP_VERSION,
    }


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("uploads/") or full_path in ("health", "ready"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = STATIC_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        index = STATIC_DIR / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Not found")
