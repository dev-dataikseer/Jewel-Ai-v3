from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import TERMINAL_JOB_STATUSES as _TERMINAL_JOB_STATUSES
from app.database import SessionLocal
from app.logging_config import get_logger
from app.models import Batch, GenerationJob

logger = get_logger(__name__)

_DEFAULT_STUCK_MINUTES = 15
_DEFAULT_WEBHOOK_TIMEOUT_MINUTES = 20


def stuck_cutoff_minutes() -> int:
    try:
        return int(get_settings().stuck_job_minutes or _DEFAULT_STUCK_MINUTES)
    except Exception:
        return _DEFAULT_STUCK_MINUTES


def webhook_timeout_minutes() -> int:
    try:
        return int(get_settings().webhook_pending_timeout_minutes or _DEFAULT_WEBHOOK_TIMEOUT_MINUTES)
    except Exception:
        return _DEFAULT_WEBHOOK_TIMEOUT_MINUTES


def get_meta(job: GenerationJob) -> dict:
    return job.provider_metadata or {}


def update_batch(db: Session, batch_id: str) -> None:
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return
    now = datetime.now(timezone.utc)
    if getattr(batch, "started_at", None) is None:
        # First child progress — mark batch wall-clock start
        any_started = (
            db.query(GenerationJob.id)
            .filter(
                GenerationJob.batch_id == batch_id,
                GenerationJob.status.in_(("PROCESSING", "COMPLETED", "FAILED", "CANCELLED")),
            )
            .first()
        )
        if any_started:
            batch.started_at = now

    completed = (
        db.query(GenerationJob)
        .filter(GenerationJob.batch_id == batch_id, GenerationJob.status == "COMPLETED")
        .count()
    )
    failed = (
        db.query(GenerationJob)
        .filter(GenerationJob.batch_id == batch_id, GenerationJob.status == "FAILED")
        .count()
    )
    cancelled = (
        db.query(GenerationJob)
        .filter(GenerationJob.batch_id == batch_id, GenerationJob.status == "CANCELLED")
        .count()
    )
    batch.completed_jobs = completed
    if completed + failed + cancelled >= batch.total_jobs:
        if failed == 0 and cancelled == 0:
            batch.status = "COMPLETED"
        elif completed == 0 and failed == 0:
            batch.status = "CANCELLED"
        else:
            batch.status = "COMPLETED_WITH_ERRORS"
        if getattr(batch, "completed_at", None) is None:
            batch.completed_at = now
    db.commit()


def mark_batch_started(db: Session, batch_id: str | None) -> None:
    if not batch_id:
        return
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return
    if getattr(batch, "started_at", None) is None:
        batch.started_at = datetime.now(timezone.utc)
        db.commit()


def mark_job_failed_terminal(job_id: str, message: str) -> None:
    """Force a job into FAILED after Celery exhausts retries (poison pill)."""
    db = SessionLocal()
    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job or job.status in _TERMINAL_JOB_STATUSES:
            return
        job.status = "FAILED"
        job.error_message = message
        meta = dict(job.provider_metadata or {})
        meta["poison_max_retries"] = True
        job.provider_metadata = meta
        db.commit()
        if job.batch_id:
            try:
                update_batch(db, job.batch_id)
            except Exception:
                logger.exception("Batch update after poison fail for %s", job_id)
    finally:
        db.close()
