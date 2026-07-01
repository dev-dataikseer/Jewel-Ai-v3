from contextlib import asynccontextmanager
from pathlib import Path

import os
import redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routers import assets, auth, jobs, misc, models, prompts, providers, public, users
from app.config import get_settings, validate_production_settings
from app.database import Base, SessionLocal, engine
import app.models  # noqa: F401 — register all tables before create_all
from app.logging_config import setup_logging
from app.providers import circuit_breaker
from app.middleware.rate_limit import RateLimitMiddleware
from app.tasks.generate import sweep_stuck_jobs
from seeds.run_seeds import run_all_seeds

settings = get_settings()
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    from app.pipeline.db_migrate import migrate_layer_columns, migrate_job_indexes

    migrate_layer_columns(engine)
    migrate_job_indexes(engine)
    db = SessionLocal()
    try:
        from app.pipeline.db_migrate import migrate_workflow_subjects

        migrate_workflow_subjects(db)
        run_all_seeds(db)
        sweep_stuck_jobs()
    finally:
        db.close()
    circuit_breaker.init_circuit_breaker()
    for warning in validate_production_settings():
        import logging

        logging.getLogger(__name__).warning("Production config: %s", warning)
    yield


app = FastAPI(title="Jewel V3 API", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

uploads_path = Path(settings.uploads_dir)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(prompts.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(misc.router, prefix="/api")
app.include_router(public.router, prefix="/api")


@app.get("/health")
def health():
    db_ok = False
    redis_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    try:
        r = redis.from_url(settings.redis_url)
        redis_ok = r.ping()
    except Exception:
        pass
    return {
        "status": "ok" if db_ok else "degraded",
        "service": "jewel-ai-api",
        "database": db_ok,
        "redis": redis_ok,
        "version": "3.0.0",
    }


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("uploads/") or full_path == "health":
            raise HTTPException(status_code=404, detail="Not found")
        candidate = STATIC_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        index = STATIC_DIR / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Not found")
