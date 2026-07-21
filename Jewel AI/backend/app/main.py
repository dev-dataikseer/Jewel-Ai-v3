from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

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


def _init_sentry() -> None:
    dsn = (settings.sentry_dsn or "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=settings.node_env,
            release=f"jewel-ai-api@{APP_VERSION}",
            traces_sample_rate=0.1 if settings.is_production else 0.0,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
            ],
        )
    except Exception:
        import logging

        logging.getLogger(__name__).exception("Sentry init failed (API)")


_init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # When SCHEMA_VIA_ALEMBIC=true, operators run `alembic upgrade head` instead of create_all.
    # Still apply additive, idempotent column patches so new columns never block boot.
    from app.pipeline.db_migrate import (
        migrate_layer_columns,
        migrate_job_indexes,
        migrate_tenancy_columns,
        migrate_batch_user_column,
        migrate_provider_admin_key_column,
        migrate_generation_job_runtime_columns,
        migrate_prompt_fragments,
        migrate_mfa_and_audit,
    )

    if not settings.schema_via_alembic:
        Base.metadata.create_all(bind=engine)
        migrate_layer_columns(engine)
        migrate_job_indexes(engine)
        migrate_tenancy_columns(engine)
        migrate_batch_user_column(engine)
        migrate_generation_job_runtime_columns(engine)
        migrate_prompt_fragments(engine)
        migrate_provider_admin_key_column(engine)
        migrate_mfa_and_audit(engine)
    # When SCHEMA_VIA_ALEMBIC=true, operators run `alembic upgrade head` — no boot DDL.
    db = SessionLocal()
    try:
        from app.pipeline.db_migrate import migrate_workflow_subjects

        migrate_workflow_subjects(db)
        run_all_seeds(db)
        try:
            sweep_stuck_jobs()
        except Exception:
            import logging

            logging.getLogger(__name__).exception("sweep_stuck_jobs skipped during startup")
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


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        request.state.request_id = request_id
        try:
            import sentry_sdk

            sentry_sdk.set_tag("request_id", request_id)
        except Exception:
            pass
        response = await call_next(request)
        response.headers.setdefault("X-Request-ID", request_id)
        return response


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
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID", "X-CSRF-Token"],
    expose_headers=["X-Request-ID", "X-MFA-Required"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)

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

# API version alias — /api/v1/* mirrors /api/* for future breaking-change freeze.
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(assets.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(prompts.router, prefix="/api/v1")
app.include_router(providers.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(misc.router, prefix="/api/v1")
app.include_router(public.router, prefix="/api/v1")


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

    @app.get("/share/{token}")
    def share_og_html(token: str):
        """HTML shell with Open Graph tags for crawlers / link previews."""
        from fastapi.responses import HTMLResponse

        from app.database import SessionLocal
        from app.models import GenerationJob, ShareLink
        from app.security.media_signing import sign_media_url

        title = "Jewel AI — Shared generation"
        description = "Shared jewelry generation from Jewel AI Studio"
        image = ""
        db = SessionLocal()
        try:
            link = db.query(ShareLink).filter(ShareLink.token == token).first()
            if link:
                job = db.query(GenerationJob).filter(GenerationJob.id == link.job_id).first()
                if job:
                    title = f"Jewel AI — {job.workflow}"
                    if job.jewelry_type:
                        description = f"{job.jewelry_type} · {job.workflow}"
                    raw = job.output_url or ((job.output_urls or [None])[0])
                    if raw:
                        signed = sign_media_url(raw) or raw
                        if signed.startswith("http"):
                            image = signed
                        else:
                            image = f"{settings.api_public_url.rstrip('/')}{signed}"
        finally:
            db.close()

        index = STATIC_DIR / "index.html"
        # Prefer injecting into SPA index so React still boots for humans.
        body = index.read_text(encoding="utf-8") if index.is_file() else "<!doctype html><html><head></head><body></body></html>"
        og = f"""
    <meta property="og:title" content="{title.replace(chr(34), '')}" />
    <meta property="og:description" content="{description.replace(chr(34), '')}" />
    <meta property="og:type" content="website" />
    <meta name="twitter:card" content="summary_large_image" />
"""
        if image:
            og += f'    <meta property="og:image" content="{image.replace(chr(34), "")}" />\n'
            og += f'    <meta name="twitter:image" content="{image.replace(chr(34), "")}" />\n'
        if "</head>" in body:
            body = body.replace("</head>", og + "</head>", 1)
        else:
            body = og + body
        return HTMLResponse(body)

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("uploads/") or full_path in ("health", "ready"):
            raise HTTPException(status_code=404, detail="Not found")
        if full_path.startswith("share/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = STATIC_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        index = STATIC_DIR / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Not found")
