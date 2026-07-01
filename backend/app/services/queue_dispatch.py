"""Dispatch image jobs to Celery when a worker is available, else process in-process."""
import asyncio
import threading

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


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
    if not _redis_available():
        return False
    try:
        from app.tasks.celery_app import celery_app

        inspect = celery_app.control.inspect(timeout=1.5)
        ping = inspect.ping()
        if ping:
            return True
        stats = inspect.stats()
        return bool(stats)
    except Exception as exc:
        logger.debug("Celery worker check failed: %s", exc)
        return False


def enqueue_image_job(job_id: str) -> None:
    if _celery_worker_available():
        from app.tasks.generate import process_image_job

        process_image_job.delay(job_id)
        logger.info("Job queued via Celery", extra={"extra_fields": {"job_id": job_id}})
        return

    from app.tasks.generate import _process_job_async

    reason = "no Redis" if not _redis_available() else "no Celery worker"
    logger.info(
        "Processing job in background thread (%s)",
        reason,
        extra={"extra_fields": {"job_id": job_id}},
    )

    def _run() -> None:
        try:
            asyncio.run(_process_job_async(job_id))
        except Exception as exc:
            logger.error("Background job thread failed", extra={"extra_fields": {"job_id": job_id, "error": str(exc)}})

    threading.Thread(target=_run, daemon=True, name=f"job-{job_id[:8]}").start()
