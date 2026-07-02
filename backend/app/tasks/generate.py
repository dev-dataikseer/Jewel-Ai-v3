import asyncio
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.logging_config import get_logger
from app.models import Batch, GenerationJob, StylePreset
from app.pipeline.composer import ComposeInput, compose_prompt
from app.providers.prompt_augment import augment_prompt_for_workflow
from app.providers.router import route_generation
from app.providers.types import GenerationRequest
from app.services.credits import deduct_credits_for_job
from app.storage.local import storage
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)
STUCK_MINUTES = 15


def _get_meta(job: GenerationJob) -> dict:
    return job.provider_metadata or {}


async def _process_job_async(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            return

        job.status = "PROCESSING"
        job.processing_started_at = datetime.now(timezone.utc)
        job.error_message = None
        db.commit()

        preset_addon = None
        if job.style_preset_id:
            preset = db.query(StylePreset).filter(StylePreset.id == job.style_preset_id).first()
            preset_addon = preset.prompt_addon if preset else None

        composed = compose_prompt(
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
            ),
        )

        job.master_version_id = composed.master_version_id
        job.subject_version_id = composed.subject_version_id
        job.variant_version_id = composed.variant_version_id

        prompt = augment_prompt_for_workflow(job.workflow, composed.text)
        meta = _get_meta(job)
        aspect = meta.get("aspectRatio", "1:1")
        model_endpoint = meta.get("modelEndpointId") or meta.get("modelName")
        model_params = meta.get("modelParams") or {}

        image_urls = [
            u
            for u in [job.input_url, job.model_url or job.reference_url]
            if u
        ]
        request = GenerationRequest(
            prompt=prompt,
            negative_prompt=composed.negative_prompt,
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
        
        if result.is_webhook_pending:
            merged = {**meta, "promptDebug": composed.debug, "providerChain": chain, "usage": result.usage, "webhook_pending": True}
            job.provider_used = result.provider
            job.provider_model = result.model
            job.provider_metadata = merged
            db.commit()
            return
            
        filename = f"generated_{job_id}.png"
        output_url = storage.save_bytes(result.image_bytes, filename=filename)
        extra_urls: list[str] = []
        extra_bytes = (result.metadata or {}).get("all_image_bytes") or []
        for idx, blob in enumerate(extra_bytes, start=2):
            extra_urls.append(storage.save_bytes(blob, filename=f"generated_{job_id}_{idx}.png"))

        merged = {**meta, "promptDebug": composed.debug, "providerChain": chain, "usage": result.usage}
        job.status = "COMPLETED"
        job.output_url = output_url
        job.output_urls = extra_urls if extra_urls else None
        job.final_prompt = prompt
        job.provider_used = result.provider
        job.provider_model = result.model
        job.cost = result.cost
        job.provider_metadata = merged
        job.credits_used = max(1, int(result.cost * 100))
        db.commit()

        if job.user_id:
            deduct_credits_for_job(db, job.user_id, job.credits_used, job.id)

        if job.batch_id:
            _update_batch(db, job.batch_id)
    except Exception as e:
        logger.error("Job failed", extra={"extra_fields": {"job_id": job_id, "error": str(e)}})
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if job:
            job.status = "FAILED"
            job.error_message = str(e)
            job.retry_count = (job.retry_count or 0) + 1
            db.commit()
            if job.batch_id:
                _update_batch(db, job.batch_id)
    finally:
        db.close()


def _update_batch(db: Session, batch_id: str) -> None:
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return
    completed = db.query(GenerationJob).filter(GenerationJob.batch_id == batch_id, GenerationJob.status == "COMPLETED").count()
    failed = db.query(GenerationJob).filter(GenerationJob.batch_id == batch_id, GenerationJob.status == "FAILED").count()
    batch.completed_jobs = completed
    if completed + failed >= batch.total_jobs:
        batch.status = "COMPLETED" if failed == 0 else "COMPLETED_WITH_ERRORS"
    db.commit()


@celery_app.task(name="app.tasks.generate.process_image_job", bind=True, max_retries=2)
def process_image_job(self, job_id: str) -> None:
    asyncio.run(_process_job_async(job_id))


@celery_app.task(name="app.tasks.generate.sweep_stuck_jobs")
def sweep_stuck_jobs() -> int:
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=STUCK_MINUTES)
        stuck = (
            db.query(GenerationJob)
            .filter(GenerationJob.status == "PROCESSING", GenerationJob.processing_started_at < cutoff)
            .all()
        )
        for job in stuck:
            meta = job.provider_metadata or {}
            if meta.get("webhook_pending") and meta.get("usage", {}).get("request_id"):
                continue
            job.status = "PENDING"
            job.error_message = None
            db.commit()
            from app.services.queue_dispatch import enqueue_image_job

            enqueue_image_job(job.id)
        return len(stuck)
    finally:
        db.close()
