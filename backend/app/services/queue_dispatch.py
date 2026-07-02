"""Dispatch image jobs to Celery when a worker is available, else process in-process."""
import asyncio
import threading
import time

from app.config import get_settings
from app.database import SessionLocal
from app.logging_config import get_logger
from app.models import GenerationJob

logger = get_logger(__name__)
settings = get_settings()

_worker_cache: dict[str, float | bool] = {"checked_at": 0.0, "available": False}
_WORKER_CACHE_TTL = 30.0


def _redis_available() -> bool:
    try:
        import redis

        client = redis.from_url(settings.redis_url, socket_connect_timeout=1)
        client.ping()
        return True
    except Exception:
        return False


def _celery_worker_available() -> bool:
    """Redis alone is not enough — without a Celery worker, .delay() never runs."""
    now = time.time()
    if now - float(_worker_cache["checked_at"]) < _WORKER_CACHE_TTL:
        return bool(_worker_cache["available"])

    available = False
    if _redis_available():
        try:
            from app.tasks.celery_app import celery_app

            inspect = celery_app.control.inspect(timeout=1.5)
            ping = inspect.ping()
            if ping:
                available = True
            else:
                stats = inspect.stats()
                available = bool(stats)
        except Exception as exc:
            logger.debug("Celery worker check failed: %s", exc)

    _worker_cache["checked_at"] = now
    _worker_cache["available"] = available
    return available


def _fail_job_enqueue(job_id: str, message: str) -> None:
    db = SessionLocal()
    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if job and job.status == "PENDING":
            job.status = "FAILED"
            job.error_message = message
            db.commit()
    finally:
        db.close()


def enqueue_image_job(job_id: str) -> None:
    if _celery_worker_available():
        from app.tasks.generate import process_image_job

        process_image_job.delay(job_id)
        logger.info("Job queued via Celery", extra={"extra_fields": {"job_id": job_id}})
        return

    if settings.is_production:
        msg = "No Celery worker available — job cannot be processed in production"
        logger.error(msg, extra={"extra_fields": {"job_id": job_id}})
        _fail_job_enqueue(job_id, msg)
        return

    from app.tasks.generate import _process_job_async

    reason = "no Redis" if not _redis_available() else "no Celery worker"
    logger.warning(
        "Processing job in background thread (%s) — not durable across restarts",
        reason,
        extra={"extra_fields": {"job_id": job_id}},
    )

    def _run() -> None:
        try:
            asyncio.run(_process_job_async(job_id))
        except Exception as exc:
            logger.error("Background job thread failed", extra={"extra_fields": {"job_id": job_id, "error": str(exc)}})

    threading.Thread(target=_run, daemon=True, name=f"job-{job_id[:8]}").start()
