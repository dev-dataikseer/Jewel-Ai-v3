import asyncio
from datetime import datetime, timedelta, timezone


from app.config import get_settings
from app.constants import TERMINAL_JOB_STATUSES as _TERMINAL_JOB_STATUSES
from app.database import SessionLocal
from app.logging_config import get_logger
from app.models import GenerationJob
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)

# Fallback defaults — settings values take precedence at runtime via the helpers below.
from app.tasks.helpers import stuck_cutoff_minutes, webhook_timeout_minutes, update_batch
from app.tasks.redis_leases import _acquire_requeue_lease

@celery_app.task(name="app.tasks.generate.sweep_stuck_jobs")
def sweep_stuck_jobs() -> int:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        stuck_cutoff = now - timedelta(minutes=stuck_cutoff_minutes())
        webhook_cutoff = now - timedelta(minutes=webhook_timeout_minutes())
        # Recover finished fal jobs quickly if webhook finalize was dropped by Celery.
        poll_cutoff = now - timedelta(seconds=45)
        stuck = (
            db.query(GenerationJob)
            .filter(GenerationJob.status == "PROCESSING", GenerationJob.processing_started_at < stuck_cutoff)
            .all()
        )
        pending_webhook = (
            db.query(GenerationJob)
            .filter(
                GenerationJob.status == "PROCESSING",
                GenerationJob.processing_started_at < poll_cutoff,
            )
            .all()
        )
        
        pending_cutoff = now - timedelta(minutes=5)
        stuck_pending = (
            db.query(GenerationJob)
            .filter(GenerationJob.status == "PENDING", GenerationJob.created_at < pending_cutoff)
            .all()
        )

        acted = 0

        for job in stuck_pending:
            job.status = "FAILED"
            job.error_message = "Job failed to start (internal queue error)"
            meta = dict(job.provider_metadata or {})
            meta["queue_failed_refunded"] = True
            job.provider_metadata = meta
            db.commit()
            
            try:
                from app.services.credits import refund_credits
                refund_credits(
                    db,
                    job.user_id,
                    amount=1,
                    job_id=job.id,
                    description="job_stuck_pending_refund",
                )
            except Exception as exc:
                logger.warning("Credit refund for stuck pending job %s failed: %s", job.id, exc)
                
            if job.batch_id:
                update_batch(db, job.batch_id)
            acted += 1

        for job in pending_webhook:
            meta = dict(job.provider_metadata or {})
            if meta.get("webhook_completed"):
                continue
            if not (meta.get("webhook_pending") or meta.get("webhook_accepted") or meta.get("fal_request_id")):
                continue
            if _recover_fal_result(job.id):
                acted += 1

        for job in stuck:
            meta = dict(job.provider_metadata or {})
            started = job.processing_started_at
            webhook_pending = bool(
                (meta.get("webhook_pending") or meta.get("webhook_accepted"))
                and (meta.get("usage", {}).get("request_id") or meta.get("fal_request_id") or meta.get("webhook_accepted"))
            )
            if webhook_pending:
                # One more recovery attempt before failing.
                if _recover_fal_result(job.id):
                    acted += 1
                    continue
                # Fail permanently if fal webhook never arrives.
                if started and started < webhook_cutoff:
                    if job.status in _TERMINAL_JOB_STATUSES:
                        continue
                    job.status = "FAILED"
                    job.error_message = (
                        f"Timed out waiting for fal webhook after {webhook_timeout_minutes()} minutes"
                    )
                    meta["webhook_timed_out"] = True
                    job.provider_metadata = meta
                    db.commit()
                    if job.batch_id:
                        update_batch(db, job.batch_id)
                    acted += 1
                continue

            # Subscribe / sync path already submitted to fal — never requeue (double spend).
            # Try poll recovery once; otherwise fail after webhook timeout window.
            has_fal_req = bool(
                meta.get("fal_request_id") or (meta.get("usage") or {}).get("request_id")
            )
            if has_fal_req:
                if _recover_fal_result(job.id):
                    acted += 1
                    continue
                if started and started < webhook_cutoff:
                    continue  # still within timeout; wait
                if job.status in _TERMINAL_JOB_STATUSES:
                    continue
                job.status = "FAILED"
                job.error_message = (
                    f"Timed out while fal request was in flight after {stuck_cutoff_minutes()} minutes "
                    "(not requeued to avoid duplicate provider charges)"
                )
                meta["subscribe_timed_out"] = True
                job.provider_metadata = meta
                db.commit()
                if job.batch_id:
                    update_batch(db, job.batch_id)
                acted += 1
                continue

            # Never reached fal — do NOT requeue by default (deploy/restart used to
            # double-bill fal.ai). Fail closed unless ALLOW_STUCK_JOB_REQUEUE=true.
            if not get_settings().allow_stuck_job_requeue:
                if job.status in _TERMINAL_JOB_STATUSES:
                    continue
                job.status = "FAILED"
                job.error_message = (
                    "Job stuck in PROCESSING without a fal request id. "
                    "Not requeued (ALLOW_STUCK_JOB_REQUEUE is false) to protect fal credits. "
                    "Use Retry in Studio if you want a new generation."
                )
                meta["stuck_failed_no_requeue"] = True
                job.provider_metadata = meta
                db.commit()
                if job.batch_id:
                    update_batch(db, job.batch_id)
                acted += 1
                continue

            if not _acquire_requeue_lease(job.id):
                continue

            job.status = "PENDING"
            job.error_message = None
            job.celery_task_id = None
            db.commit()
            from app.services.queue_dispatch import enqueue_image_job

            enqueue_image_job(job.id)
            acted += 1
        return acted
    finally:
        db.close()


def _recover_fal_result(job_id: str) -> bool:
    """Poll fal queue for a completed request and finalize if images are ready."""
    import httpx

    from app.config import get_settings
    from app.providers.fal_billing.service import resolve_fal_api_key

    db = SessionLocal()
    envelope: dict | None = None
    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job or job.status != "PROCESSING":
            return False
        if (job.provider_metadata or {}).get("webhook_completed"):
            return False

        meta = dict(job.provider_metadata or {})
        request_id = meta.get("fal_request_id") or (meta.get("usage") or {}).get("request_id")
        endpoint = job.provider_model or meta.get("modelEndpointId")
        if not request_id or not endpoint:
            return False

        api_key = resolve_fal_api_key(db) or get_settings().fal_key
        if not api_key:
            return False

        headers = {"Authorization": f"Key {api_key}", "Accept": "application/json"}
        status_url = f"https://queue.fal.run/{endpoint}/requests/{request_id}/status"
        result_url = f"https://queue.fal.run/{endpoint}/requests/{request_id}"

        try:
            with httpx.Client(timeout=20.0) as client:
                st = client.get(status_url, headers=headers)
                if st.status_code >= 400:
                    return False
                st_body = st.json() if st.content else {}
                status = str((st_body or {}).get("status") or "").upper()
                if status in ("IN_QUEUE", "IN_PROGRESS", "PROCESSING"):
                    return False
                resp = client.get(result_url, headers=headers)
                if resp.status_code >= 400:
                    return False
                payload = resp.json()
        except Exception as exc:
            logger.debug("fal poll failed for %s: %s", job_id, exc)
            return False

        if not isinstance(payload, dict):
            return False
        from app.api.routers.providers import (
            _stamp_webhook_observability,
            extract_fal_webhook_request_id,
        )

        # Normalize to webhook-like envelope expected by finalize.
        envelope = payload if "payload" in payload else {"status": "OK", "payload": payload}
        # Ensure request_id is present for finalize matching (poll payloads vary).
        if not extract_fal_webhook_request_id(envelope) and request_id:
            envelope = {**envelope, "request_id": str(request_id)}

        meta = _stamp_webhook_observability(meta, envelope)
        meta["recovered_via_fal_poll"] = True
        job.provider_metadata = meta
        db.commit()
    finally:
        db.close()

    if not envelope:
        return False
    try:
        from app.tasks.webhook_finalize import _finalize_fal_webhook_async

        asyncio.run(_finalize_fal_webhook_async(job_id, envelope))
        return True
    except Exception as exc:
        logger.warning("fal poll finalize failed for %s: %s", job_id, exc)
        return False

