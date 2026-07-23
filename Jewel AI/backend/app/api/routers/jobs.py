import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.auth.deps import RequireUser
from app.auth.security import create_job_stream_token, decode_job_stream_token
from app.config import get_settings
from app.constants import BULK_SUPPORTED_WORKFLOWS
from app.database import SessionLocal, get_db
from app.models import Asset, Batch, Favorite, GenerationJob, Project, User
from app.pipeline.validator import validate_job_create, whitelist_job_fields
from app.providers.model_validate import validate_generation_request, validate_model_params
from app.providers.registry import get_model_definition, resolve_default_endpoint
from app.providers.types import GenerationRequest
from app.schemas.common import BatchOut, BulkJobCreate, JobCreate, JobOut
from app.services.queue_dispatch import enqueue_image_job, enqueue_image_jobs


router = APIRouter(prefix="/jobs", tags=["jobs"])


def _request_id(request: Request | None) -> str | None:
    if request is None:
        return None
    return getattr(getattr(request, "state", None), "request_id", None)


def _enforce_daily_job_limit(db: Session, user: User, additional: int = 1) -> None:
    limit = int(get_settings().daily_job_limit or 0)
    if limit <= 0:
        return
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    used = (
        db.query(GenerationJob)
        .filter(GenerationJob.user_id == user.id, GenerationJob.created_at >= start)
        .count()
    )
    if used + additional > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily generation limit reached ({limit}). Try again tomorrow or contact admin.",
        )


def _asset_input_url(asset: Asset | None) -> str | None:
    if not asset:
        return None
    return asset.processed_url or asset.original_url


def _asset_storage_url(asset: Asset | None) -> str | None:
    """Prefer durable /uploads path (needed for logo compose from object storage)."""
    if not asset:
        return None
    return asset.original_url or asset.processed_url


def _job_to_out(job: GenerationJob, *, lean: bool = False) -> JobOut:
    from app.security.media_signing import sign_media_url
    from app.services.job_timing import attach_eta_fields

    out = JobOut.model_validate(job)
    data = out.model_dump()
    data["input_url"] = sign_media_url(data.get("input_url"))
    data["reference_url"] = sign_media_url(data.get("reference_url"))
    data["model_url"] = sign_media_url(data.get("model_url"))
    data["output_url"] = sign_media_url(data.get("output_url"))
    if data.get("output_urls"):
        data["output_urls"] = [sign_media_url(u) for u in data["output_urls"]]

    meta = dict(data.get("provider_metadata") or {})
    meta = attach_eta_fields(job, meta)
    if lean:
        # Strip heavy debug payloads from list/stream to reduce bandwidth
        meta.pop("promptDebug", None)
        meta.pop("composedPrompt", None)
        data["final_prompt"] = None
    data["provider_metadata"] = meta
    return JobOut.model_validate(data)


def _get_user_job(db: Session, job_id: str, user: User) -> GenerationJob | None:
    return (
        db.query(GenerationJob)
        .filter(GenerationJob.id == job_id, GenerationJob.user_id == user.id)
        .first()
    )


def _provider_meta(body: dict) -> dict:
    endpoint = body.get("model_endpoint_id") or body.get("model_name")
    return _stamp_timing(
        {
            "aspectRatio": body.get("aspect_ratio", "1:1"),
            "personGeneration": body.get("person_generation", "ALLOW_ADULT"),
            "numberOfImages": body.get("number_of_images", 1),
            "modelEndpointId": endpoint,
            "modelParams": body.get("model_params") or {},
            "modelName": endpoint,
        },
        "queued",
    )


def _resolve_bulk_workflow(workflow: str, *, try_on_mode: str | None = None) -> str:
    """Map UI aliases to concrete generation workflows."""
    from app.prompt_engine.workflow_resolve import resolve_workflow

    resolved = resolve_workflow(workflow, try_on_mode=try_on_mode)
    return resolved.workflow


def _stamp_timing(meta: dict | None, stage: str) -> dict:
    out = dict(meta or {})
    timing = dict(out.get("timing") or {})
    timing[stage] = datetime.now(timezone.utc).isoformat()
    out["timing"] = timing
    out["progressStage"] = stage
    return out


_PROVIDER_RUN_KEYS = frozenset(
    {
        "fal_request_id",
        "usage",
        "webhook_pending",
        "webhook_accepted",
        "webhook_completed",
        "webhook_timed_out",
        "recovered_via_fal_poll",
        "statusHint",
        "poison_max_retries",
        "composedPrompt",
        "providerChain",
        "fal_inference_time",
        "latencyTrace",
    }
)


def _scrub_provider_run_state(meta: dict | None) -> dict:
    """Drop fal/webhook run state so retry/regenerate cannot finalize the wrong request."""
    out = {k: v for k, v in dict(meta or {}).items() if k not in _PROVIDER_RUN_KEYS}
    timing = dict(out.get("timing") or {})
    for key in ("fal_queued", "fal_result_received", "storage_saved", "completed", "failed", "cancelled"):
        timing.pop(key, None)
    if timing:
        out["timing"] = timing
    else:
        out.pop("timing", None)
    return out


def _batch_status_counts(db: Session, batch_id: str) -> dict[str, int]:
    rows = (
        db.query(GenerationJob.status, func.count(GenerationJob.id))
        .filter(GenerationJob.batch_id == batch_id)
        .group_by(GenerationJob.status)
        .all()
    )
    return {status: int(n) for status, n in rows}


def _batch_to_out(db: Session, batch: Batch, *, include_jobs: bool = True) -> BatchOut:
    jobs_out: list = []
    if include_jobs:
        jobs = (
            db.query(GenerationJob)
            .filter(GenerationJob.batch_id == batch.id)
            .order_by(GenerationJob.created_at.asc())
            .all()
        )
        counts = {
            "PENDING": sum(1 for j in jobs if j.status == "PENDING"),
            "PROCESSING": sum(1 for j in jobs if j.status == "PROCESSING"),
            "FAILED": sum(1 for j in jobs if j.status == "FAILED"),
            "CANCELLED": sum(1 for j in jobs if j.status == "CANCELLED"),
        }
        jobs_out = [_job_to_out(j, lean=True) for j in jobs]
    else:
        counts = _batch_status_counts(db, batch.id)
    return BatchOut(
        id=batch.id,
        name=batch.name,
        workflow=batch.workflow,
        jewelry_type=batch.jewelry_type,
        status=batch.status,
        total_jobs=batch.total_jobs,
        completed_jobs=batch.completed_jobs,
        pending_jobs=counts.get("PENDING", 0),
        processing_jobs=counts.get("PROCESSING", 0),
        failed_jobs=counts.get("FAILED", 0),
        cancelled_jobs=counts.get("CANCELLED", 0),
        started_at=getattr(batch, "started_at", None),
        completed_at=getattr(batch, "completed_at", None),
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        jobs=jobs_out,
    )


def _validate_job_model(db: Session, data: dict, workflow: str, image_count: int) -> dict:
    has_input = image_count > 0
    endpoint = data.get("model_endpoint_id") or data.get("model_name") or resolve_default_endpoint(
        db, workflow, has_input
    )
    model_def = get_model_definition(db, endpoint) if endpoint else None
    if endpoint and not model_def:
        raise HTTPException(status_code=400, detail=f"Unknown model: {endpoint}")
    if not model_def:
        return data

    raw_params = data.get("model_params") or {}
    data["model_params"] = validate_model_params(model_def, raw_params)
    data["model_endpoint_id"] = endpoint

    validate_generation_request(
        model_def,
        GenerationRequest(
            prompt=data.get("prompt_text") or "preview",
            image_urls=["placeholder"] * image_count if image_count else [],
            workflow=workflow,
            model_endpoint_id=endpoint,
            model_params=data["model_params"],
            number_of_images=data.get("number_of_images", 1),
        ),
    )
    return data


@router.post("", response_model=JobOut)
def create_job(
    body: JobCreate,
    user: RequireUser,
    request: Request,
    db: Session = Depends(get_db),
):
    from app.services.latency_trace import enabled as latency_trace_enabled
    from app.services.latency_trace import log_event, merge_job_trace

    t0_api = time.perf_counter() if latency_trace_enabled() else None
    data = whitelist_job_fields(body.model_dump())
    validate_job_create(data)
    try:
        from app.security.url_fetch import validate_user_owned_image_url

        validate_user_owned_image_url(db, user, body.reference_url)
        validate_user_owned_image_url(db, user, body.model_url)
        validate_user_owned_image_url(db, user, getattr(body, "logo_url", None))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    from app.prompt_engine.workflow_resolve import resolve_workflow

    resolved = resolve_workflow(
        body.workflow,
        catalog_mode=getattr(body, "catalog_mode", None),
        try_on_mode=getattr(body, "try_on_mode", None),
        has_reference=bool(body.reference_url),
    )
    workflow = resolved.workflow

    asset = (
        db.query(Asset)
        .filter(Asset.id == body.asset_id, Asset.user_id == user.id)
        .first()
        if body.asset_id
        else None
    )
    if not asset:
        raise HTTPException(status_code=400, detail="asset_id is required and must belong to you")

    _enforce_daily_job_limit(db, user, 1)

    if workflow == "VIRTUAL_TRY_ON" and not (body.model_url or body.reference_url):
        raise HTTPException(
            status_code=400,
            detail="Virtual Try-On requires a model or customer portrait (model_url or reference_url)",
        )
    if resolved.catalog_mode == "style_mood" and not body.reference_url:
        raise HTTPException(status_code=400, detail="Style mood catalog mode requires reference_url")

    image_count = 1
    if body.reference_url or body.model_url:
        image_count = 2
    data = _validate_job_model(db, data, workflow, image_count)

    logo_url = getattr(body, "logo_url", None)
    logo_asset_id = getattr(body, "logo_asset_id", None)
    if logo_asset_id:
        logo_asset = (
            db.query(Asset).filter(Asset.id == logo_asset_id, Asset.user_id == user.id).first()
        )
        if not logo_asset:
            raise HTTPException(status_code=404, detail="Logo asset not found")
        # Must use storage path (/uploads/...), not fal CDN processed_url —
        # logo compose reads bytes from object storage / local uploads.
        logo_url = _asset_storage_url(logo_asset)

    project = Project(
        name=f"Project {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        workflow=workflow,
        user_id=user.id,
    )
    db.add(project)
    db.flush()

    meta = _provider_meta(data)
    if logo_url:
        meta["logoUrl"] = logo_url
    if logo_asset_id:
        meta["logoAssetId"] = logo_asset_id
    if resolved.catalog_mode:
        meta["catalogMode"] = resolved.catalog_mode
    if resolved.try_on_mode:
        meta["tryOnMode"] = resolved.try_on_mode
    if resolved.legacy_workflow:
        meta["legacyWorkflow"] = resolved.legacy_workflow

    model_url = body.model_url
    reference_url = body.reference_url
    if workflow == "VIRTUAL_TRY_ON":
        model_url = body.model_url or body.reference_url
        reference_url = None

    job = GenerationJob(
        user_id=user.id,
        project_id=project.id,
        asset_id=body.asset_id,
        workflow=workflow,
        status="PENDING",
        prompt_text=body.prompt_text,
        jewelry_type=body.jewelry_type,
        metal_type=body.metal_type,
        gemstone_type=body.gemstone_type,
        gemstone_cut=body.gemstone_cut,
        gemstone_target_color=body.gemstone_target_color,
        setting_type=body.setting_type,
        background_style=body.background_style,
        lighting_style=body.lighting_style,
        style_preset_id=body.style_preset_id,
        reference_url=reference_url,
        model_url=model_url,
        input_url=_asset_input_url(asset),
        provider_metadata=meta,
    )
    db.add(job)
    db.flush()
    from app.services.credits import debit_credits

    debit_credits(db, user.id, amount=1, job_id=job.id, description="job_create")
    db.commit()
    db.refresh(job)
    if latency_trace_enabled() and t0_api is not None:
        t0_api_ms = int(round((time.perf_counter() - t0_api) * 1000))
        enqueued_at = datetime.now(timezone.utc).isoformat()
        merge_job_trace(
            db,
            job.id,
            {
                "T0_api_ms": t0_api_ms,
                "t0_api_enqueued_at": enqueued_at,
            },
        )
        log_event(
            "T0_api_received",
            job_id=job.id,
            T0_api_ms=t0_api_ms,
            workflow=workflow,
            request_id=_request_id(request),
        )
    enqueue_image_job(job.id, request_id=_request_id(request))
    return _job_to_out(job)


@router.post("/bulk", response_model=dict)
def create_bulk_jobs(
    body: BulkJobCreate,
    user: RequireUser,
    request: Request,
    db: Session = Depends(get_db),
):
    workflow = _resolve_bulk_workflow(body.workflow, try_on_mode=getattr(body, "try_on_mode", None))
    from app.prompt_engine.workflow_resolve import resolve_workflow

    resolved = resolve_workflow(
        body.workflow,
        catalog_mode=getattr(body, "catalog_mode", None),
        try_on_mode=getattr(body, "try_on_mode", None),
        has_reference=bool(body.reference_url),
    )
    workflow = resolved.workflow
    if workflow not in BULK_SUPPORTED_WORKFLOWS:
        raise HTTPException(status_code=400, detail=f"Bulk not supported for workflow: {workflow}")


    data = whitelist_job_fields(body.model_dump())
    data["workflow"] = workflow
    data["asset_ids"] = body.asset_ids
    validate_job_create(data)
    try:
        from app.security.url_fetch import validate_user_owned_image_url

        validate_user_owned_image_url(db, user, body.reference_url)
        validate_user_owned_image_url(db, user, body.model_url)
        validate_user_owned_image_url(db, user, body.logo_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if workflow == "VIRTUAL_TRY_ON" and not (body.model_url or body.reference_url):
        raise HTTPException(
            status_code=400,
            detail="Bulk try-on requires a shared model/customer portrait (model_url or reference_url)",
        )
    if resolved.catalog_mode == "style_mood" and not body.reference_url:
        raise HTTPException(status_code=400, detail="Bulk style mood requires reference_url")

    image_count = 1
    if body.reference_url or body.model_url:
        image_count = 2
    data = _validate_job_model(db, data, workflow, image_count)

    # Dedupe asset_ids (preserve first occurrence order)
    seen: set[str] = set()
    ordered_ids: list[str] = []
    for aid in body.asset_ids:
        if aid and aid not in seen:
            seen.add(aid)
            ordered_ids.append(aid)
    if not ordered_ids:
        raise HTTPException(status_code=400, detail="asset_ids required")

    assets_by_id = {
        a.id: a
        for a in db.query(Asset).filter(Asset.id.in_(ordered_ids), Asset.user_id == user.id).all()
    }
    if len(assets_by_id) != len(ordered_ids):
        raise HTTPException(status_code=404, detail="One or more assets not found")
    assets = [assets_by_id[aid] for aid in ordered_ids]

    _enforce_daily_job_limit(db, user, len(assets))
    from app.services.credits import debit_credits

    debit_credits(db, user.id, amount=len(assets), description="bulk_job_create")

    logo_url = body.logo_url
    if body.logo_asset_id:
        logo_asset = (
            db.query(Asset).filter(Asset.id == body.logo_asset_id, Asset.user_id == user.id).first()
        )
        if not logo_asset:
            raise HTTPException(status_code=404, detail="Logo asset not found")
        logo_url = _asset_storage_url(logo_asset)

    # Shared secondary image: try-on uses model_url; others use reference_url
    shared_model_url = body.model_url
    shared_reference_url = body.reference_url
    if workflow == "VIRTUAL_TRY_ON":
        shared_model_url = body.model_url or body.reference_url
        shared_reference_url = None

    batch = Batch(
        name=body.batch_name or f"Bulk {workflow} {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        workflow=workflow,
        jewelry_type=body.jewelry_type,
        preset_id=body.style_preset_id,
        status="PROCESSING",
        total_jobs=len(assets),
        user_id=user.id,
    )
    db.add(batch)
    db.flush()

    project = Project(name=batch.name or "Bulk Project", workflow=workflow, user_id=user.id)
    db.add(project)
    db.flush()

    meta = _provider_meta(data)
    if logo_url:
        meta["logoUrl"] = logo_url
    if body.logo_asset_id:
        meta["logoAssetId"] = body.logo_asset_id
    meta["batchShared"] = True
    if resolved.catalog_mode:
        meta["catalogMode"] = resolved.catalog_mode
    if resolved.try_on_mode:
        meta["tryOnMode"] = resolved.try_on_mode
    if resolved.legacy_workflow:
        meta["legacyWorkflow"] = resolved.legacy_workflow

    jobs: list[GenerationJob] = []
    for asset in assets:
        job = GenerationJob(
            user_id=user.id,
            project_id=project.id,
            batch_id=batch.id,
            asset_id=asset.id,
            workflow=workflow,
            status="PENDING",
            jewelry_type=body.jewelry_type,
            prompt_text=body.prompt_text,
            metal_type=body.metal_type,
            gemstone_type=body.gemstone_type,
            gemstone_cut=body.gemstone_cut,
            gemstone_target_color=body.gemstone_target_color,
            setting_type=body.setting_type,
            background_style=body.background_style,
            lighting_style=body.lighting_style,
            style_preset_id=body.style_preset_id,
            reference_url=shared_reference_url,
            model_url=shared_model_url,
            input_url=_asset_input_url(asset),
            provider_metadata=dict(meta),
        )
        db.add(job)
        db.flush()
        jobs.append(job)

    db.commit()
    from app.services.queue_dispatch import celery_worker_available

    queue_mode = "celery" if celery_worker_available() else "inline"
    enqueue_image_jobs([j.id for j in jobs], stagger_ms=0, request_id=_request_id(request))
    return {
        "batchId": batch.id,
        "jobIds": [j.id for j in jobs],
        "total": len(jobs),
        "queueMode": queue_mode,
        "jobs": [_job_to_out(j, lean=True) for j in jobs],
        "batch": _batch_to_out(db, batch, include_jobs=False).model_dump(mode="json"),
    }


@router.get("", response_model=dict)
def list_jobs(
    user: RequireUser,
    cursor: Optional[str] = None,
    limit: int = Query(20, le=100),
    status: Optional[str] = None,
    workflow: Optional[str] = None,
    batch_id: Optional[str] = None,
    ids: Optional[str] = None,
    favorites_only: bool = False,
    db: Session = Depends(get_db),
):
    q = db.query(GenerationJob).filter(GenerationJob.user_id == user.id).order_by(
        GenerationJob.created_at.desc(), GenerationJob.id.desc()
    )
    if ids:
        id_list = [i.strip() for i in ids.split(",") if i.strip()]
        if id_list:
            q = q.filter(GenerationJob.id.in_(id_list[:50]))
            rows = q.all()
            by_id = {j.id: j for j in rows}
            # Preserve requested order
            ordered = [by_id[i] for i in id_list if i in by_id]
            return {"items": [_job_to_out(j, lean=True) for j in ordered], "next_cursor": None}
    if batch_id:
        q = q.filter(GenerationJob.batch_id == batch_id)
    if status:
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        if len(statuses) == 1:
            q = q.filter(GenerationJob.status == statuses[0])
        elif statuses:
            q = q.filter(GenerationJob.status.in_(statuses))
    if workflow:
        q = q.filter(GenerationJob.workflow == workflow)
    if favorites_only:
        q = q.join(Favorite, Favorite.job_id == GenerationJob.id).filter(Favorite.user_id == user.id)
    if cursor:
        # Keyset pagination: cursor is "created_at_iso|id"
        try:
            if "|" in cursor:
                created_raw, cursor_id = cursor.split("|", 1)
                cursor_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                q = q.filter(
                    (GenerationJob.created_at < cursor_dt)
                    | (
                        (GenerationJob.created_at == cursor_dt)
                        & (GenerationJob.id < cursor_id)
                    )
                )
            else:
                # Legacy: treat as job id — find that job's created_at
                anchor = (
                    db.query(GenerationJob)
                    .filter(GenerationJob.id == cursor, GenerationJob.user_id == user.id)
                    .first()
                )
                if anchor:
                    q = q.filter(
                        (GenerationJob.created_at < anchor.created_at)
                        | (
                            (GenerationJob.created_at == anchor.created_at)
                            & (GenerationJob.id < anchor.id)
                        )
                    )
        except ValueError:
            pass
    rows = q.limit(limit + 1).all()
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = None
    if has_more and items:
        last = items[-1]
        created = last.created_at.isoformat() if last.created_at else ""
        next_cursor = f"{created}|{last.id}"
    return {
        "items": [_job_to_out(j, lean=True) for j in items],
        "next_cursor": next_cursor,
    }


@router.get("/batches", response_model=dict)
def list_batches(
    user: RequireUser,
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=40),
):
    rows = (
        db.query(Batch)
        .filter(Batch.user_id == user.id)
        .order_by(Batch.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "items": [_batch_to_out(db, b, include_jobs=False).model_dump(mode="json") for b in rows],
    }


@router.get("/batches/{batch_id}", response_model=BatchOut)
def get_batch(batch_id: str, user: RequireUser, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.id == batch_id, Batch.user_id == user.id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return _batch_to_out(db, batch)


@router.post("/batches/{batch_id}/cancel", response_model=BatchOut)
def cancel_batch(batch_id: str, user: RequireUser, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.id == batch_id, Batch.user_id == user.id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    active = (
        db.query(GenerationJob)
        .filter(
            GenerationJob.batch_id == batch.id,
            GenerationJob.user_id == user.id,
            GenerationJob.status.in_(("PENDING", "PROCESSING")),
        )
        .all()
    )
    for job in active:
        celery_task_id = job.celery_task_id
        _maybe_refund_cancel(db, job)
        job.status = "CANCELLED"
        job.error_message = "Cancelled by user (batch)"
        job.provider_metadata = _stamp_timing(dict(job.provider_metadata or {}), "cancelled")
        if celery_task_id:
            try:
                from app.tasks.celery_app import celery_app

                celery_app.control.revoke(celery_task_id, terminate=True)
            except Exception:
                pass
        meta = job.provider_metadata or {}
        req_id = meta.get("fal_request_id") or (meta.get("usage") or {}).get("request_id")
        endpoint = meta.get("modelEndpointId") or meta.get("modelName") or job.provider_model
        if req_id and endpoint:
            try:
                from app.providers.adapters.fal import cancel_fal_request

                cancel_fal_request(str(endpoint), str(req_id))
            except Exception:
                pass
    db.commit()

    from app.tasks.generate import _update_batch

    _update_batch(db, batch.id)
    db.refresh(batch)
    return _batch_to_out(db, batch)


@router.get("/batches/{batch_id}/zip")
def download_batch_zip(batch_id: str, user: RequireUser, db: Session = Depends(get_db)):
    """Stream a ZIP of completed batch output images."""
    import io
    import logging
    import zipfile
    from urllib.parse import urlparse

    from fastapi.responses import StreamingResponse

    from app.storage.local import StorageService
    from app.storage.object_store import parse_upload_path

    log = logging.getLogger(__name__)

    batch = db.query(Batch).filter(Batch.id == batch_id, Batch.user_id == user.id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    if batch.status not in ("COMPLETED", "COMPLETED_WITH_ERRORS", "PROCESSING", "CANCELLED"):
        raise HTTPException(status_code=400, detail=f"Batch not ready for ZIP ({batch.status})")

    jobs = (
        db.query(GenerationJob)
        .filter(
            GenerationJob.batch_id == batch.id,
            GenerationJob.user_id == user.id,
            GenerationJob.status == "COMPLETED",
        )
        .order_by(GenerationJob.created_at.asc())
        .all()
    )
    if not jobs:
        raise HTTPException(status_code=404, detail="No completed outputs in this batch")

    storage = StorageService()
    buf = io.BytesIO()
    written = 0

    def _read_image(url: str | None) -> bytes | None:
        if not url:
            return None
        path = str(url).split("?", 1)[0]
        try:
            upload_name = parse_upload_path(path)
            if upload_name:
                data, _ = storage.read_upload(upload_name)
                return data
            if path.startswith("/uploads/"):
                name = path.replace("/uploads/", "", 1)
                data, _ = storage.read_upload(name)
                return data
            if path.startswith("http://") or path.startswith("https://"):
                from app.security.url_fetch import safe_fetch_image_bytes_sync

                return safe_fetch_image_bytes_sync(path, timeout=60.0)
        except Exception as exc:
            log.warning("ZIP skip unreadable image %s: %s", path[:80], exc)
            return None
        return None

    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, job in enumerate(jobs, start=1):
            urls: list[str] = []
            if job.output_urls:
                urls.extend([u for u in job.output_urls if u])
            elif job.output_url:
                urls.append(job.output_url)

            for j, url in enumerate(urls):
                data = _read_image(url)
                if not data:
                    continue
                parsed = urlparse(str(url).split("?", 1)[0])
                ext = Path(parsed.path).suffix.lower() or ".png"
                if ext not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                    ext = ".png"
                suffix = "" if j == 0 else f"-{j + 1}"
                zf.writestr(f"{idx:03d}-{job.id[:8]}{suffix}{ext}", data)
                written += 1

    if written == 0:
        raise HTTPException(status_code=404, detail="No readable output files in this batch")

    buf.seek(0)
    filename = f"batch-{batch.id[:8]}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/stream-token")
def create_stream_token(body: dict, user: RequireUser, db: Session = Depends(get_db)):
    job_ids = [str(j).strip() for j in body.get("job_ids", []) if str(j).strip()]
    if not job_ids:
        raise HTTPException(status_code=400, detail="job_ids required")
    owned = (
        db.query(GenerationJob.id)
        .filter(GenerationJob.id.in_(job_ids), GenerationJob.user_id == user.id)
        .all()
    )
    owned_ids = {row[0] for row in owned}
    missing = [jid for jid in job_ids if jid not in owned_ids]
    if missing:
        raise HTTPException(status_code=404, detail=f"Job not found: {missing[0]}")
    token = create_job_stream_token(user.id, job_ids)
    return {"token": token, "expires_in": 600}


@router.get("/stream")
async def stream_jobs(job_ids: str, stream_token: str):
    payload = decode_job_stream_token(stream_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid stream token")

    stream_user_id = payload.get("sub")
    allowed_ids = set(payload.get("job_ids") or [])
    ids = [i.strip() for i in job_ids.split(",") if i.strip() and i.strip() in allowed_ids]
    if not ids:
        raise HTTPException(status_code=400, detail="No valid job ids for stream token")

    async def event_generator():
        import asyncio

        seen: dict[str, str] = {}
        sleep_s = 1.0
        for _ in range(300):
            db_local = SessionLocal()
            try:
                jobs = (
                    db_local.query(GenerationJob)
                    .filter(
                        GenerationJob.id.in_(ids),
                        GenerationJob.user_id == stream_user_id,
                    )
                    .all()
                )
                jobs_by_id = {j.id: j for j in jobs}
                terminal = True
                for jid in ids:
                    job = jobs_by_id.get(jid)
                    if not job:
                        continue
                    if job.status not in ("COMPLETED", "FAILED", "CANCELLED"):
                        terminal = False
                    key = f"{job.status}:{job.output_url}"
                    if seen.get(jid) != key:
                        seen[jid] = key
                        yield {
                            "event": "job_update",
                            "data": json.dumps(_job_to_out(job, lean=True).model_dump(mode="json")),
                        }
                if terminal:
                    break
            finally:
                db_local.close()
            await asyncio.sleep(sleep_s)
            sleep_s = min(sleep_s * 1.5, 5.0)
        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(event_generator())


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, user: RequireUser, db: Session = Depends(get_db)):
    job = _get_user_job(db, job_id, user)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_out(job)


def _job_has_fal_request(job: GenerationJob) -> bool:
    meta = job.provider_metadata or {}
    return bool(meta.get("fal_request_id") or (meta.get("usage") or {}).get("request_id"))


def _maybe_refund_cancel(db: Session, job: GenerationJob) -> None:
    """Refund user credits when cancelling before fal accepted the request."""
    if _job_has_fal_request(job):
        return
    try:
        from app.services.credits import refund_credits

        refund_credits(
            db,
            job.user_id,
            amount=1,
            job_id=job.id,
            description="job_cancel_refund",
        )
    except Exception:
        pass


@router.post("/{job_id}/regenerate", response_model=JobOut)
def regenerate_job(job_id: str, user: RequireUser, request: Request, db: Session = Depends(get_db)):
    original = _get_user_job(db, job_id, user)
    if not original:
        raise HTTPException(status_code=404, detail="Job not found")
    if original.status in ("PENDING", "PROCESSING"):
        raise HTTPException(
            status_code=400,
            detail="Cancel or wait for the job to finish before regenerating",
        )

    _enforce_daily_job_limit(db, user, 1)

    meta = _stamp_timing(_scrub_provider_run_state(original.provider_metadata), "queued")
    meta["regeneratedFrom"] = original.id

    job = GenerationJob(
        user_id=user.id,
        project_id=original.project_id,
        batch_id=original.batch_id,
        asset_id=original.asset_id,
        workflow=original.workflow,
        status="PENDING",
        prompt_text=original.prompt_text,
        jewelry_type=original.jewelry_type,
        metal_type=original.metal_type,
        gemstone_type=original.gemstone_type,
        gemstone_cut=original.gemstone_cut,
        gemstone_target_color=original.gemstone_target_color,
        setting_type=original.setting_type,
        background_style=original.background_style,
        lighting_style=original.lighting_style,
        style_preset_id=original.style_preset_id,
        reference_url=original.reference_url,
        model_url=original.model_url,
        input_url=original.input_url,
        provider_metadata=meta,
    )
    db.add(job)
    db.flush()
    from app.services.credits import debit_credits

    debit_credits(db, user.id, amount=1, job_id=job.id, description="job_regenerate")
    db.commit()
    db.refresh(job)
    enqueue_image_job(job.id, request_id=_request_id(request))
    return _job_to_out(job)


@router.post("/{job_id}/retry", response_model=JobOut)
def retry_job(job_id: str, user: RequireUser, request: Request, db: Session = Depends(get_db)):
    """Re-queue a FAILED/CANCELLED job in place (same id, same settings)."""
    job = _get_user_job(db, job_id, user)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("FAILED", "CANCELLED"):
        raise HTTPException(status_code=400, detail="Only failed or cancelled jobs can be retried")

    _enforce_daily_job_limit(db, user, 1)

    job.status = "PENDING"
    job.error_message = None
    job.output_url = None
    job.output_urls = None
    job.final_prompt = None
    job.processing_started_at = None
    job.celery_task_id = None
    job.retry_count = (job.retry_count or 0) + 1
    job.provider_metadata = _stamp_timing(_scrub_provider_run_state(job.provider_metadata), "queued")
    from app.services.credits import debit_credits

    # Debit each retry attempt so enqueue-fail refunds cannot unlock free generations.
    debit_credits(db, user.id, amount=1, job_id=job.id, description="job_retry")
    db.commit()
    db.refresh(job)
    enqueue_image_job(job.id, request_id=_request_id(request))
    return _job_to_out(job)


@router.post("/{job_id}/cancel", response_model=JobOut)
def cancel_job(job_id: str, user: RequireUser, db: Session = Depends(get_db)):
    job = _get_user_job(db, job_id, user)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("PENDING", "PROCESSING"):
        raise HTTPException(status_code=400, detail="Only pending or processing jobs can be cancelled")

    celery_task_id = job.celery_task_id
    _maybe_refund_cancel(db, job)
    job.status = "CANCELLED"
    job.error_message = "Cancelled by user"
    job.provider_metadata = _stamp_timing(dict(job.provider_metadata or {}), "cancelled")
    db.commit()
    db.refresh(job)

    if celery_task_id:
        try:
            from app.tasks.celery_app import celery_app

            celery_app.control.revoke(celery_task_id, terminate=True)
        except Exception:
            pass

    # Best-effort fal queue cancel when we have a request id
    meta = job.provider_metadata or {}
    req_id = meta.get("fal_request_id") or (meta.get("usage") or {}).get("request_id")
    endpoint = meta.get("modelEndpointId") or meta.get("modelName") or job.provider_model
    if req_id and endpoint:
        try:
            from app.providers.adapters.fal import cancel_fal_request

            cancel_fal_request(str(endpoint), str(req_id))
        except Exception:
            pass

    if job.batch_id:
        from app.tasks.generate import _update_batch

        _update_batch(db, job.batch_id)
        db.refresh(job)

    return _job_to_out(job)


@router.delete("/{job_id}")
def delete_job(job_id: str, user: RequireUser, db: Session = Depends(get_db)):
    job = _get_user_job(db, job_id, user)
    if not job and user.role == "admin":
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in ("PENDING", "PROCESSING"):
        raise HTTPException(
            status_code=400,
            detail="Cancel the job before deleting while it is still pending or processing",
        )
    db.delete(job)
    db.commit()
    return {"success": True}
