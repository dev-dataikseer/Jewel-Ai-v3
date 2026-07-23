import asyncio
import time
from datetime import datetime, timezone


from app.constants import TERMINAL_JOB_STATUSES as _TERMINAL_JOB_STATUSES
from app.database import SessionLocal
from app.logging_config import get_logger
from app.models import GenerationJob, StylePreset
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
from app.services.latency_trace import (
    emit_summary,
    enabled as latency_trace_enabled,
    log_event,
    merge_job_trace,
)

logger = get_logger(__name__)

# Fallback defaults — settings values take precedence at runtime via the helpers below.
from app.tasks.helpers import get_meta, mark_job_failed_terminal, update_batch, mark_batch_started

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

        # Already charged at fal — never resubmit. Recover or wait for Beat timeout.
        existing_fal = (job.provider_metadata or {}).get("fal_request_id") or (
            (job.provider_metadata or {}).get("usage") or {}
        ).get("request_id")
        if existing_fal and not (job.provider_metadata or {}).get("webhook_completed"):
            logger.info(
                "Skip fal resubmit — request already queued",
                extra={"extra_fields": {"job_id": job_id, "fal_request_id": existing_fal}},
            )
            # Removed unused variable 'recovered'
            try:
                from app.tasks.job_sweep import _recover_fal_result
                _recover_fal_result(job_id)
            except Exception:
                logger.exception("recover after existing fal_request_id failed for %s", job_id)
            return

        meta = dict(get_meta(job))
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
        mark_batch_started(db, job.batch_id)

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
                    update_batch(db, job.batch_id)
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
            update_batch(db, job.batch_id)
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
                update_batch(db, job.batch_id)
    finally:
        db.close()

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
            mark_job_failed_terminal(
                job_id,
                f"Worker crashed after max retries: {type(exc).__name__}: {exc}",
            )
            raise

