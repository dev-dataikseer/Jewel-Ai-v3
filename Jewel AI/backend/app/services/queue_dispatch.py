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


def celery_worker_available() -> bool:
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


def _celery_worker_available() -> bool:
    return celery_worker_available()


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


def _persist_celery_task_id(job_id: str, task_id: str | None) -> None:
    if not task_id:
        return
    db = SessionLocal()
    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if job:
            job.celery_task_id = task_id
            db.commit()
    except Exception as exc:
        logger.warning("Failed to persist celery_task_id for %s: %s", job_id, exc)
    finally:
        db.close()


def enqueue_image_job(job_id: str) -> None:
    if _celery_worker_available():
        from app.tasks.generate import process_image_job

        async_result = process_image_job.delay(job_id)
        _persist_celery_task_id(job_id, getattr(async_result, "id", None))
        logger.info("Job queued via Celery", extra={"extra_fields": {"job_id": job_id, "celery_task_id": async_result.id}})
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
            logger.error(
                "Background job thread failed",
                extra={"extra_fields": {"job_id": job_id, "error": str(exc)}},
            )

    threading.Thread(target=_run, daemon=True, name=f"job-{job_id[:8]}").start()


def enqueue_image_jobs(job_ids: list[str], *, stagger_ms: int = 250) -> None:
    """Enqueue many jobs with a small stagger to avoid fal.ai stampede on bulk."""
    if not job_ids:
        return
    if len(job_ids) == 1 or stagger_ms <= 0:
        for jid in job_ids:
            enqueue_image_job(jid)
        return

    if _celery_worker_available():
        from app.tasks.generate import process_image_job

        for i, jid in enumerate(job_ids):
            countdown = (i * stagger_ms) / 1000.0
            async_result = process_image_job.apply_async(args=[jid], countdown=countdown)
            _persist_celery_task_id(jid, getattr(async_result, "id", None))
            logger.info(
                "Job queued via Celery (staggered)",
                extra={"extra_fields": {"job_id": jid, "countdown_s": countdown, "celery_task_id": async_result.id}},
            )
        return

    for i, jid in enumerate(job_ids):
        delay = (i * stagger_ms) / 1000.0

        def _later(job_id: str = jid, wait: float = delay) -> None:
            if wait > 0:
                time.sleep(wait)
            enqueue_image_job(job_id)

        threading.Thread(target=_later, daemon=True, name=f"bulk-enq-{jid[:8]}").start()
