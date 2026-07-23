import asyncio
import time
from datetime import datetime, timezone


from app.constants import TERMINAL_JOB_STATUSES as _TERMINAL_JOB_STATUSES
from app.database import SessionLocal
from app.logging_config import get_logger
from app.models import GenerationJob
from app.pipeline.image_packet import apply_logo_compose_if_needed
from app.storage.local import storage
from app.tasks.celery_app import celery_app
from app.services.latency_trace import (
    emit_summary,
    enabled as latency_trace_enabled,
    log_event,
    merge_job_trace,
)

logger = get_logger(__name__)

# Fallback defaults — settings values take precedence at runtime via the helpers below.
from app.tasks.helpers import update_batch
from app.tasks.redis_leases import _acquire_webhook_finalize_lease, _release_webhook_finalize_lease

@celery_app.task(name="app.tasks.generate.finalize_fal_webhook")
def finalize_fal_webhook(job_id: str, payload: dict) -> None:
    """Durable webhook image download/save (survives API process restart)."""
    asyncio.run(_finalize_fal_webhook_async(job_id, payload))


async def _finalize_fal_webhook_async(job_id: str, payload: dict) -> None:
    from uuid import uuid4

    from app.providers.fal_response import extract_image_urls
    from app.providers.registry import get_model_definition
    from app.security.url_fetch import safe_fetch_image_bytes

    finalize_t0 = time.perf_counter() if latency_trace_enabled() else None
    lease_held = False

    if not _acquire_webhook_finalize_lease(job_id):
        logger.info(
            "Skip webhook finalize — lease held",
            extra={"extra_fields": {"job_id": job_id}},
        )
        return
    lease_held = True

    db = SessionLocal()
    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).with_for_update().first()
        if not job or job.status in _TERMINAL_JOB_STATUSES:
            return
        if job.status != "PROCESSING":
            return
        if (job.provider_metadata or {}).get("webhook_completed"):
            return

        # Defense in depth: refuse finalize if payload request_id does not match job.
        from app.api.routers.providers import (
            _stamp_webhook_observability,
            extract_fal_webhook_request_id,
        )
        from app.services.job_timing import extract_fal_inference_seconds, record_job_eta_sample

        expected = (job.provider_metadata or {}).get("fal_request_id") or (
            (job.provider_metadata or {}).get("usage") or {}
        ).get("request_id")
        got = extract_fal_webhook_request_id(payload if isinstance(payload, dict) else {})
        if not expected or not got or str(got) != str(expected):
            logger.warning(
                "finalize_request_id_mismatch",
                extra={"extra_fields": {"job_id": job_id, "expected": expected, "got": got}},
            )
            return

        # Best-effort receipt stamp for poll recovery (webhook path already stamped).
        meta0 = _stamp_webhook_observability(dict(job.provider_metadata or {}), payload or {})
        job.provider_metadata = meta0
        db.commit()

        model_def = get_model_definition(db, job.provider_model) if job.provider_model else None
        config = (model_def.config or {}) if model_def else {}
        payload_data = payload.get("payload") or {}
        img_urls = extract_image_urls(payload, config) or extract_image_urls(payload_data, config)

        if not img_urls:
            if job.status not in _TERMINAL_JOB_STATUSES:
                job.status = "FAILED"
                job.error_message = "Webhook OK status but no images in payload"
                db.commit()
                if job.batch_id:
                    update_batch(db, job.batch_id)
            return

        meta_peek = job.provider_metadata or {}
        logo_mode = meta_peek.get("logoMode") or "omit"
        logo_url = meta_peek.get("logoUrl")

        extra_urls: list[str] = []
        primary_url = ""
        for idx, img_url in enumerate(img_urls):
            content = await safe_fetch_image_bytes(img_url)
            content = apply_logo_compose_if_needed(
                content, logo_mode=logo_mode, logo_url=logo_url, storage=storage
            )
            saved_url = storage.save_bytes(content, filename=f"generated_{uuid4().hex}.png")
            if idx == 0:
                primary_url = saved_url
            else:
                extra_urls.append(saved_url)

        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).with_for_update().first()
        if not job or job.status != "PROCESSING":
            return
        meta = dict(job.provider_metadata or {})
        if job.cost is None and model_def and model_def.cost_per_call is not None:
            job.cost = float(model_def.cost_per_call)
        job.output_url = primary_url
        job.output_urls = extra_urls if extra_urls else None
        job.status = "COMPLETED"
        if not job.final_prompt and meta.get("composedPrompt"):
            job.final_prompt = meta.get("composedPrompt")

        now_iso = datetime.now(timezone.utc).isoformat()
        timing = dict(meta.get("timing") or {})
        timing.setdefault("fal_webhook_received", now_iso)
        timing["storage_saved"] = now_iso
        timing["completed"] = now_iso
        if meta.get("fal_inference_time") is None:
            inference = extract_fal_inference_seconds(payload)
            if inference is not None:
                meta["fal_inference_time"] = inference

        merged = {
            **meta,
            "webhook_completed": True,
            "progressStage": "completed",
            "logoApplied": logo_mode if logo_url else "none",
            "timing": timing,
        }
        job.provider_metadata = merged
        db.commit()
        if latency_trace_enabled() and finalize_t0 is not None:
            t3_post_ms = int(round((time.perf_counter() - finalize_t0) * 1000))
            trace = dict(meta.get("latencyTrace") or {})
            fal_req = meta.get("fal_request_id") or got
            log_event(
                "T3_webhook_finalize",
                job_id=job_id,
                fal_request_id=str(fal_req) if fal_req else None,
                T3_post_ms=t3_post_ms,
            )
            emit_summary(
                job_id=job_id,
                fal_request_id=str(fal_req) if fal_req else None,
                t0_api_ms=trace.get("T0_api_ms"),
                celery_queue_ms=trace.get("celery_queue_ms"),
                t1_prep_ms=trace.get("T1_prep_ms"),
                t2_fal_api_ms=trace.get("T2_fal_api_ms"),
                t2_fal_mode=trace.get("T2_fal_mode") or "webhook_submit",
                t3_post_ms=t3_post_ms,
                extra={"path": "webhook_finalize"},
            )
            merge_job_trace(db, job_id, {"T3_post_ms": t3_post_ms})
        try:
            record_job_eta_sample(job, merged)
        except Exception:
            pass
        if job.batch_id:
            update_batch(db, job.batch_id)
    except Exception as e:
        logger.error("Failed to process webhook image for job %s: %s", job_id, e)
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if job and job.status not in _TERMINAL_JOB_STATUSES:
            job.status = "FAILED"
            job.error_message = f"Webhook image download failed: {str(e)}"
            db.commit()
            if job.batch_id:
                update_batch(db, job.batch_id)
    finally:
        if lease_held:
            _release_webhook_finalize_lease(job_id)
        db.close()
