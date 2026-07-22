import asyncio
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.logging_config import get_logger
from app.models import Batch, GenerationJob, StylePreset
from app.pipeline.composer import ComposeInput
from app.pipeline.image_packet import apply_logo_compose_if_needed
from app.pipeline.image_prep import build_model_image_plan
from app.prompt_engine import build_final_prompt
from app.prompt_engine.attachments import ImageContext
from app.providers.model_catalog.registry import get_spec
from app.providers.router import route_generation
from app.providers.types import GenerationRequest
from app.storage.local import storage
from app.tasks.celery_app import celery_app
from app.config import get_settings
from app.services.latency_trace import (
    emit_summary,
    enabled as latency_trace_enabled,
    log_event,
    merge_job_trace,
)

logger = get_logger(__name__)
STUCK_MINUTES = 15
WEBHOOK_PENDING_TIMEOUT_MINUTES = 20


def _stuck_cutoff_minutes() -> int:
    try:
        return int(get_settings().stuck_job_minutes or STUCK_MINUTES)
    except Exception:
        return STUCK_MINUTES


def _webhook_timeout_minutes() -> int:
    try:
        return int(get_settings().webhook_pending_timeout_minutes or WEBHOOK_PENDING_TIMEOUT_MINUTES)
    except Exception:
        return WEBHOOK_PENDING_TIMEOUT_MINUTES


def _get_meta(job: GenerationJob) -> dict:
    return job.provider_metadata or {}


_TERMINAL_JOB_STATUSES = frozenset({"COMPLETED", "FAILED", "CANCELLED"})


def _mark_job_failed_terminal(job_id: str, message: str) -> None:
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
                _update_batch(db, job.batch_id)
            except Exception:
                logger.exception("Batch update after poison fail for %s", job_id)
    finally:
        db.close()


async def _process_job_async(job_id: str) -> None:
    db = SessionLocal()
    prompt = ""
    worker_timer = time.perf_counter() if latency_trace_enabled() else None
    prep_t0 = worker_timer
    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            return
        # Idempotent: never re-run finished jobs (Celery acks_late redelivery).
        if job.status in _TERMINAL_JOB_STATUSES:
            logger.info(
                "Skip job in terminal status",
                extra={"extra_fields": {"job_id": job_id, "status": job.status}},
            )
            return
        # Another worker already owns this job (duplicate delivery while in-flight).
        if job.status == "PROCESSING":
            logger.info(
                "Skip job already PROCESSING",
                extra={"extra_fields": {"job_id": job_id}},
            )
            return

        api_request_id = (job.provider_metadata or {}).get("request_id")
        logger.info(
            "Processing image job",
            extra={
                "extra_fields": {
                    "job_id": job_id,
                    "request_id": api_request_id,
                    "workflow": job.workflow,
                }
            },
        )
        try:
            import sentry_sdk

            if api_request_id:
                sentry_sdk.set_tag("request_id", str(api_request_id))
            sentry_sdk.set_tag("job_id", job_id)
        except Exception:
            pass

        # Atomic claim: only one worker may move PENDING → PROCESSING.
        now = datetime.now(timezone.utc)
        claimed = (
            db.query(GenerationJob)
            .filter(GenerationJob.id == job_id, GenerationJob.status == "PENDING")
            .update(
                {
                    GenerationJob.status: "PROCESSING",
                    GenerationJob.processing_started_at: now,
                    GenerationJob.error_message: None,
                },
                synchronize_session=False,
            )
        )
        db.commit()
        if not claimed:
            return

        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job or job.status != "PROCESSING":
            return

        meta = dict(_get_meta(job))
        timing = dict(meta.get("timing") or {})
        timing["worker_started"] = now.isoformat()
        meta["timing"] = timing
        meta["progressStage"] = "composing_prompt"
        job.provider_metadata = meta
        db.commit()
        if latency_trace_enabled():
            trace = dict(meta.get("latencyTrace") or {})
            api_enqueued = trace.get("t0_api_enqueued_at")
            celery_queue_ms = None
            if api_enqueued:
                try:
                    t_enqueue = datetime.fromisoformat(str(api_enqueued).replace("Z", "+00:00"))
                    celery_queue_ms = max(0, int((now - t_enqueue).total_seconds() * 1000))
                except Exception:
                    pass
            log_event(
                "worker_started",
                job_id=job_id,
                celery_queue_ms=celery_queue_ms,
            )
            merge_job_trace(
                db,
                job_id,
                {
                    "worker_started_at": now.isoformat(),
                    "celery_queue_ms": celery_queue_ms,
                },
            )
        _mark_batch_started(db, job.batch_id)

        preset_addon = None
        if job.style_preset_id:
            preset = db.query(StylePreset).filter(StylePreset.id == job.style_preset_id).first()
            preset_addon = preset.prompt_addon if preset else None

        aspect = meta.get("aspectRatio", "1:1")
        model_endpoint = meta.get("modelEndpointId") or meta.get("modelName")
        model_params = meta.get("modelParams") or {}

        model_spec = get_spec(model_endpoint) if model_endpoint else None
        plan = build_model_image_plan(
            job,
            model_spec=model_spec,
            model_endpoint_id=model_endpoint,
        )
        packet = plan.packet
        image_urls = packet.image_urls
        meta.update(packet.to_meta())
        if plan.warnings:
            meta["imagePrepWarnings"] = plan.warnings
        meta["imageFieldMap"] = plan.field_map
        job.provider_metadata = meta
        db.commit()

        final = build_final_prompt(
            db,
            ComposeInput(
                workflow=job.workflow,
                jewelry_type=job.jewelry_type,
                prompt_text=job.prompt_text,
                metal_type=job.metal_type,
                gemstone_type=job.gemstone_type,
                gemstone_target_color=job.gemstone_target_color,
                background_style=job.background_style,
                lighting_style=job.lighting_style,
                style_preset_id=job.style_preset_id,
                style_preset_addon=preset_addon,
                catalog_mode=meta.get("catalogMode") or meta.get("catalog_mode"),
                try_on_mode=meta.get("tryOnMode") or meta.get("try_on_mode"),
            ),
            model_endpoint_id=model_endpoint,
            image_ctx=ImageContext(**packet.to_image_context_kwargs()),
            user_id=job.user_id,
            job_id=job.id,
        )

        db.refresh(job)
        if job.status == "CANCELLED":
            return

        job.master_version_id = final.master_version_id
        job.subject_version_id = final.subject_version_id
        job.variant_version_id = final.variant_version_id

        prompt = final.text
        timing["prompt_ready"] = datetime.now(timezone.utc).isoformat()
        timing["fal_submit"] = datetime.now(timezone.utc).isoformat()
        t1_prep_ms = None
        if latency_trace_enabled() and prep_t0 is not None:
            t1_prep_ms = int(round((time.perf_counter() - prep_t0) * 1000))
            log_event("T1_prep_complete", job_id=job_id, T1_prep_ms=t1_prep_ms)
            merge_job_trace(db, job_id, {"T1_prep_ms": t1_prep_ms})
        meta = {
            **(job.provider_metadata or meta),
            "timing": timing,
            "progressStage": "waiting_on_fal",
            "statusHint": "Generating with fal.ai",
        }
        job.provider_metadata = meta
        db.commit()

        request = GenerationRequest(
            prompt=prompt,
            negative_prompt=final.negative_prompt,
            image_urls=image_urls,
            aspect_ratio=aspect,
            workflow=job.workflow,
            model_endpoint_id=model_endpoint,
            model_params=model_params,
            model_override=model_endpoint,
            person_generation=meta.get("personGeneration", "ALLOW_ADULT"),
            number_of_images=meta.get("numberOfImages", 1),
            job_id=job.id,
        )

        result, chain = await route_generation(db, request)
        t2_fal_ms = None
        t2_fal_mode = None
        fal_req_id = None
        if latency_trace_enabled():
            lt = (result.metadata or {}).get("latencyTrace") or {}
            t2_fal_ms = lt.get("T2_fal_api_ms")
            t2_fal_mode = lt.get("T2_fal_mode")
            fal_req_id = (result.metadata or {}).get("fal_request_id") or (result.usage or {}).get(
                "request_id"
            )

        db.refresh(job)
        if job.status == "CANCELLED":
            return

        if result.is_webhook_pending:
            timing["fal_queued"] = datetime.now(timezone.utc).isoformat()
            fal_req = (result.metadata or {}).get("fal_request_id") or (result.usage or {}).get("request_id")
            if not fal_req:
                job.status = "FAILED"
                job.error_message = "fal.ai webhook submit returned no request_id"
                job.provider_metadata = {
                    **meta,
                    "timing": timing,
                    "progressStage": "failed",
                }
                db.commit()
                if job.batch_id:
                    _update_batch(db, job.batch_id)
                return
            merged = {
                **meta,
                **packet.to_meta(),
                "promptDebug": final.debug,
                "providerChain": chain,
                "usage": result.usage,
                "webhook_pending": True,
                "composedPrompt": prompt,
                "timing": timing,
                "progressStage": "waiting_on_fal",
                "statusHint": "Queued at fal.ai — waiting for provider callback",
                "fal_request_id": fal_req,
            }
            job.provider_used = result.provider
            job.provider_model = result.model
            job.cost = result.cost
            job.final_prompt = prompt
            job.provider_metadata = merged
            db.commit()
            if latency_trace_enabled():
                trace = dict(meta.get("latencyTrace") or {})
                emit_summary(
                    job_id=job_id,
                    fal_request_id=str(fal_req) if fal_req else None,
                    t0_api_ms=trace.get("T0_api_ms"),
                    celery_queue_ms=trace.get("celery_queue_ms"),
                    t1_prep_ms=t1_prep_ms or trace.get("T1_prep_ms"),
                    t2_fal_api_ms=t2_fal_ms,
                    t2_fal_mode=t2_fal_mode or "webhook_submit",
                    extra={"path": "webhook_pending"},
                )
                merge_job_trace(
                    db,
                    job_id,
                    {
                        "fal_request_id": str(fal_req) if fal_req else None,
                        "T2_fal_api_ms": t2_fal_ms,
                        "T2_fal_mode": t2_fal_mode or "webhook_submit",
                    },
                )
            return

        from uuid import uuid4

        # Subscribe path: fal call finished — stamp before local logo/storage I/O
        timing["fal_result_received"] = datetime.now(timezone.utc).isoformat()
        post_t0 = time.perf_counter() if latency_trace_enabled() else None
        image_bytes = result.image_bytes
        logo_mode = packet.logo_mode
        logo_url = packet.logo_url
        image_bytes = apply_logo_compose_if_needed(
            image_bytes, logo_mode=logo_mode, logo_url=logo_url, storage=storage
        )

        filename = f"generated_{uuid4().hex}.png"
        output_url = storage.save_bytes(image_bytes, filename=filename)
        extra_urls: list[str] = []
        extra_bytes = (result.metadata or {}).get("all_image_bytes") or []
        for idx, blob in enumerate(extra_bytes, start=2):
            composed_blob = apply_logo_compose_if_needed(
                blob, logo_mode=logo_mode, logo_url=logo_url, storage=storage
            )
            extra_urls.append(storage.save_bytes(composed_blob, filename=f"generated_{uuid4().hex}.png"))

        # Re-check cancel before committing success (download can race with cancel).
        db.refresh(job)
        if job.status in _TERMINAL_JOB_STATUSES:
            return

        timing["storage_saved"] = datetime.now(timezone.utc).isoformat()
        timing["completed"] = timing["storage_saved"]
        merged = {
            **meta,
            **packet.to_meta(),
            "promptDebug": final.debug,
            "providerChain": chain,
            "usage": result.usage,
            "timing": timing,
            "progressStage": "completed",
            "statusHint": None,
            "logoApplied": logo_mode if logo_url else "none",
        }
        # Sync path: fal returned inline — capture inference_time / request_id / latencyTrace
        from app.services.job_timing import (
            attach_duration_splits,
            extract_fal_inference_seconds,
            record_job_eta_sample,
        )

        sync_payload = result.metadata or {}
        if sync_payload.get("latencyTrace"):
            merged["latencyTrace"] = {
                **dict(merged.get("latencyTrace") or {}),
                **dict(sync_payload["latencyTrace"]),
            }
        inference = (
            sync_payload.get("fal_inference_time")
            or extract_fal_inference_seconds(sync_payload)
            or extract_fal_inference_seconds(
                {"metrics": sync_payload.get("metrics"), "payload": sync_payload}
            )
        )
        if inference is not None:
            merged["fal_inference_time"] = inference
        if sync_payload.get("fal_request_id"):
            merged["fal_request_id"] = sync_payload["fal_request_id"]
        elif (result.usage or {}).get("request_id"):
            merged["fal_request_id"] = result.usage["request_id"]
        merged = attach_duration_splits(merged)
        job = (
            db.query(GenerationJob)
            .filter(GenerationJob.id == job_id)
            .with_for_update()
            .first()
        )
        if not job or job.status != "PROCESSING":
            return
        job.status = "COMPLETED"
        job.output_url = output_url
        job.output_urls = extra_urls if extra_urls else None
        job.final_prompt = prompt
        job.provider_used = result.provider
        job.provider_model = result.model
        job.cost = result.cost
        job.provider_metadata = merged
        db.commit()

        t3_post_ms = None
        if latency_trace_enabled() and post_t0 is not None:
            t3_post_ms = int(round((time.perf_counter() - post_t0) * 1000))
            trace = dict(merged.get("latencyTrace") or {})
            emit_summary(
                job_id=job_id,
                fal_request_id=str(fal_req_id) if fal_req_id else None,
                t0_api_ms=trace.get("T0_api_ms"),
                celery_queue_ms=trace.get("celery_queue_ms"),
                t1_prep_ms=t1_prep_ms or trace.get("T1_prep_ms"),
                t2_fal_api_ms=t2_fal_ms,
                t2_fal_mode=t2_fal_mode,
                t3_post_ms=t3_post_ms,
                extra={"path": "subscribe_sync"},
            )
            merge_job_trace(
                db,
                job_id,
                {
                    "T3_post_ms": t3_post_ms,
                    "fal_request_id": str(fal_req_id) if fal_req_id else None,
                },
            )

        try:
            record_job_eta_sample(job, merged)
        except Exception:
            pass

        if job.batch_id:
            _update_batch(db, job.batch_id)
    except Exception as e:
        logger.error("Job failed", extra={"extra_fields": {"job_id": job_id, "error": str(e)}})
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if job and job.status not in _TERMINAL_JOB_STATUSES:
            job.status = "FAILED"
            raw = str(e)
            if "expected output for this prompt" in raw.lower():
                job.error_message = (
                    "fal.ai rejected the prompt (too long or incompatible). "
                    "Retry — catalog prompts are capped for Nano Banana. "
                    f"Details: {raw[:280]}"
                )
            elif "401" in raw:
                job.error_message = (
                    "fal.ai returned 401 Unauthorized — check FAL_KEY in Admin → Providers. "
                    f"Details: {raw[:200]}"
                )
            else:
                job.error_message = raw[:500]
            if not job.final_prompt and prompt:
                job.final_prompt = prompt
            job.retry_count = (job.retry_count or 0) + 1
            meta = dict(job.provider_metadata or {})
            timing = dict(meta.get("timing") or {})
            timing["failed"] = datetime.now(timezone.utc).isoformat()
            meta["timing"] = timing
            meta["progressStage"] = "failed"
            job.provider_metadata = meta
            db.commit()
            if job.batch_id:
                _update_batch(db, job.batch_id)
    finally:
        db.close()


def _update_batch(db: Session, batch_id: str) -> None:
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


def _mark_batch_started(db: Session, batch_id: str | None) -> None:
    if not batch_id:
        return
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return
    if getattr(batch, "started_at", None) is None:
        batch.started_at = datetime.now(timezone.utc)
        db.commit()


@celery_app.task(
    name="app.tasks.generate.process_image_job",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    rate_limit=None,  # set from settings after import (see celery_app)
)
def process_image_job(self, job_id: str, request_id: str | None = None) -> None:
    """Run generation. Transient failures retry via Celery; permanent failures stay FAILED.

    Stuck PROCESSING jobs are also recovered by sweep_stuck_jobs (Beat).
    After max_retries the job is marked terminal FAILED (poison pill) so it cannot
    loop forever in PENDING/PROCESSING.
    """
    if request_id:
        logger.info(
            "Celery process_image_job start",
            extra={"extra_fields": {"job_id": job_id, "request_id": request_id}},
        )
        try:
            import sentry_sdk

            sentry_sdk.set_tag("request_id", str(request_id))
            sentry_sdk.set_tag("job_id", job_id)
        except Exception:
            pass

    try:
        asyncio.run(_process_job_async(job_id))
    except Exception as exc:
        # Only retry unexpected worker crashes; job-level failures are handled inside _process_job_async
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error(
                "Celery poison job: max_retries exceeded — marking FAILED",
                extra={
                    "extra_fields": {
                        "job_id": job_id,
                        "request_id": request_id,
                        "error": str(exc),
                        "retries": getattr(self.request, "retries", None),
                    }
                },
            )
            _mark_job_failed_terminal(
                job_id,
                f"Worker crashed after max retries: {type(exc).__name__}: {exc}",
            )
            raise


@celery_app.task(name="app.tasks.generate.sweep_stuck_jobs")
def sweep_stuck_jobs() -> int:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        stuck_cutoff = now - timedelta(minutes=_stuck_cutoff_minutes())
        webhook_cutoff = now - timedelta(minutes=_webhook_timeout_minutes())
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
        acted = 0

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
                        f"Timed out waiting for fal webhook after {_webhook_timeout_minutes()} minutes"
                    )
                    meta["webhook_timed_out"] = True
                    job.provider_metadata = meta
                    db.commit()
                    if job.batch_id:
                        _update_batch(db, job.batch_id)
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
                    f"Timed out while fal request was in flight after {_stuck_cutoff_minutes()} minutes "
                    "(not requeued to avoid duplicate provider charges)"
                )
                meta["subscribe_timed_out"] = True
                job.provider_metadata = meta
                db.commit()
                if job.batch_id:
                    _update_batch(db, job.batch_id)
                acted += 1
                continue

            # Never reached fal — safe to requeue with lease.
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
        asyncio.run(_finalize_fal_webhook_async(job_id, envelope))
        return True
    except Exception as exc:
        logger.warning("fal poll finalize failed for %s: %s", job_id, exc)
        return False


def _acquire_requeue_lease(job_id: str, *, ttl_seconds: int = 120) -> bool:
    """Return True if this process won the requeue lease for job_id."""
    try:
        import redis
        from app.config import get_settings

        client = redis.from_url(get_settings().redis_url, socket_connect_timeout=1)
        key = f"jewel:requeue-lease:{job_id}"
        return bool(client.set(key, "1", nx=True, ex=ttl_seconds))
    except Exception:
        # Without Redis, fall back to allowing one requeue (dev).
        return True


def _acquire_webhook_finalize_lease(job_id: str, *, ttl_seconds: int = 300) -> bool:
    """Return True if this process won the webhook finalize lease (prevents double download)."""
    try:
        import redis
        from app.config import get_settings

        client = redis.from_url(get_settings().redis_url, socket_connect_timeout=1)
        key = f"jewel:webhook-finalize:{job_id}"
        return bool(client.set(key, "1", nx=True, ex=ttl_seconds))
    except Exception:
        # Without Redis, allow finalize once (dev); races possible but rare locally.
        return True


def _release_webhook_finalize_lease(job_id: str) -> None:
    try:
        import redis
        from app.config import get_settings

        client = redis.from_url(get_settings().redis_url, socket_connect_timeout=1)
        client.delete(f"jewel:webhook-finalize:{job_id}")
    except Exception:
        pass


@celery_app.task(name="app.tasks.generate.finalize_fal_webhook")
def finalize_fal_webhook(job_id: str, payload: dict) -> None:
    """Durable webhook image download/save (survives API process restart)."""
    asyncio.run(_finalize_fal_webhook_async(job_id, payload))


async def _finalize_fal_webhook_async(job_id: str, payload: dict) -> None:
    from uuid import uuid4

    from app.pipeline.image_packet import apply_logo_compose_if_needed
    from app.providers.fal_response import extract_image_urls
    from app.providers.registry import get_model_definition
    from app.security.url_fetch import safe_fetch_image_bytes
    from app.storage.local import storage

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
                    _update_batch(db, job.batch_id)
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
            _update_batch(db, job.batch_id)
    except Exception as e:
        logger.error("Failed to process webhook image for job %s: %s", job_id, e)
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if job and job.status not in _TERMINAL_JOB_STATUSES:
            job.status = "FAILED"
            job.error_message = f"Webhook image download failed: {str(e)}"
            db.commit()
            if job.batch_id:
                _update_batch(db, job.batch_id)
    finally:
        if lease_held:
            _release_webhook_finalize_lease(job_id)
        db.close()
