import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.auth.deps import RequireAdmin, RequireUser
from app.auth.security import create_job_stream_token, decode_job_stream_token
from app.config import get_settings
from app.database import SessionLocal, get_db
from app.models import Asset, Batch, Favorite, GenerationJob, Project, ShareLink, User
from app.pipeline.validator import validate_job_create, whitelist_job_fields
from app.providers.model_validate import validate_generation_request, validate_model_params
from app.providers.registry import get_model_definition, resolve_default_endpoint
from app.providers.types import GenerationRequest
from app.schemas.common import BatchOut, BulkJobCreate, JobCreate, JobOut, ShareLinkCreate
from app.services.queue_dispatch import enqueue_image_job, enqueue_image_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


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


def _resolve_bulk_workflow(workflow: str) -> str:
    """Map UI aliases to concrete generation workflows."""
    if workflow in ("BULK_GENERATION", ""):
        return "CATALOG_IMAGE"
    if workflow == "VIRTUAL_TRY_ON":
        return "JEWELRY_ON_MODEL"
    return workflow


def _stamp_timing(meta: dict | None, stage: str) -> dict:
    out = dict(meta or {})
    timing = dict(out.get("timing") or {})
    timing[stage] = datetime.now(timezone.utc).isoformat()
    out["timing"] = timing
    out["progressStage"] = stage
    return out


def _batch_to_out(db: Session, batch: Batch, *, include_jobs: bool = True) -> BatchOut:
    jobs = (
        db.query(GenerationJob)
        .filter(GenerationJob.batch_id == batch.id)
        .order_by(GenerationJob.created_at.asc())
        .all()
    )
    pending = sum(1 for j in jobs if j.status == "PENDING")
    processing = sum(1 for j in jobs if j.status == "PROCESSING")
    failed = sum(1 for j in jobs if j.status == "FAILED")
    cancelled = sum(1 for j in jobs if j.status == "CANCELLED")
    return BatchOut(
        id=batch.id,
        name=batch.name,
        workflow=batch.workflow,
        jewelry_type=batch.jewelry_type,
        status=batch.status,
        total_jobs=batch.total_jobs,
        completed_jobs=batch.completed_jobs,
        pending_jobs=pending,
        processing_jobs=processing,
        failed_jobs=failed,
        cancelled_jobs=cancelled,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        jobs=[_job_to_out(j, lean=True) for j in jobs] if include_jobs else [],
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
    db: Session = Depends(get_db),
):
    data = whitelist_job_fields(body.model_dump())
    validate_job_create(data)
    try:
        from app.security.url_fetch import validate_user_image_url

        validate_user_image_url(body.reference_url)
        validate_user_image_url(body.model_url)
        validate_user_image_url(getattr(body, "logo_url", None))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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

    image_count = 1
    if body.reference_url or body.model_url:
        image_count = 2
    data = _validate_job_model(db, data, body.workflow, image_count)

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
        workflow=body.workflow,
        user_id=user.id,
    )
    db.add(project)
    db.flush()

    meta = _provider_meta(data)
    if logo_url:
        meta["logoUrl"] = logo_url
    if logo_asset_id:
        meta["logoAssetId"] = logo_asset_id

    job = GenerationJob(
        user_id=user.id,
        project_id=project.id,
        asset_id=body.asset_id,
        workflow=body.workflow,
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
        reference_url=body.reference_url,
        model_url=body.model_url,
        input_url=_asset_input_url(asset),
        provider_metadata=meta,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    enqueue_image_job(job.id)
    return _job_to_out(job)


@router.post("/bulk", response_model=dict)
def create_bulk_jobs(
    body: BulkJobCreate,
    user: RequireUser,
    db: Session = Depends(get_db),
):
    workflow = _resolve_bulk_workflow(body.workflow)
    if workflow not in (
        "CATALOG_IMAGE",
        "JEWELRY_ON_MODEL",
        "CUSTOMER_TRY_ON",
        "REFERENCE_STYLE_MATCH",
        "GEMSTONE_COLOR_CHANGE",
        "BACKGROUND_REPLACEMENT",
        "LUXURY_ENHANCEMENT",
        "CUSTOM_PROMPT",
    ):
        raise HTTPException(status_code=400, detail=f"Bulk not supported for workflow: {workflow}")

    data = whitelist_job_fields(body.model_dump())
    data["workflow"] = workflow
    data["asset_ids"] = body.asset_ids
    validate_job_create(data)
    try:
        from app.security.url_fetch import validate_user_image_url

        validate_user_image_url(body.reference_url)
        validate_user_image_url(body.model_url)
        validate_user_image_url(body.logo_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if workflow in ("JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON") and not (body.model_url or body.reference_url):
        raise HTTPException(
            status_code=400,
            detail="Bulk try-on requires a shared model/customer portrait (model_url or reference_url)",
        )
    if workflow == "REFERENCE_STYLE_MATCH" and not body.reference_url:
        raise HTTPException(status_code=400, detail="Bulk style match requires reference_url")

    image_count = 1
    if body.reference_url or body.model_url:
        image_count = 2
    data = _validate_job_model(db, data, workflow, image_count)

    # Preserve request order of asset_ids
    assets_by_id = {
        a.id: a
        for a in db.query(Asset).filter(Asset.id.in_(body.asset_ids), Asset.user_id == user.id).all()
    }
    if len(assets_by_id) != len(set(body.asset_ids)):
        raise HTTPException(status_code=404, detail="One or more assets not found")
    assets = [assets_by_id[aid] for aid in body.asset_ids if aid in assets_by_id]
    if not assets:
        raise HTTPException(status_code=400, detail="asset_ids required")

    _enforce_daily_job_limit(db, user, len(assets))

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
    if workflow in ("JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"):
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
    enqueue_image_jobs([j.id for j in jobs], stagger_ms=250)
    return {
        "batchId": batch.id,
        "jobIds": [j.id for j in jobs],
        "total": len(jobs),
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


@router.get("/batches/{batch_id}", response_model=BatchOut)
def get_batch(batch_id: str, user: RequireUser, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.id == batch_id, Batch.user_id == user.id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return _batch_to_out(db, batch)


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


@router.post("/{job_id}/regenerate", response_model=JobOut)
def regenerate_job(job_id: str, user: RequireUser, db: Session = Depends(get_db)):
    original = _get_user_job(db, job_id, user)
    if not original:
        raise HTTPException(status_code=404, detail="Job not found")

    _enforce_daily_job_limit(db, user, 1)

    meta = _stamp_timing(dict(original.provider_metadata or {}), "queued")
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
    db.commit()
    db.refresh(job)
    enqueue_image_job(job.id)
    return _job_to_out(job)


@router.post("/{job_id}/retry", response_model=JobOut)
def retry_job(job_id: str, user: RequireUser, db: Session = Depends(get_db)):
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
    job.retry_count = (job.retry_count or 0) + 1
    job.provider_metadata = _stamp_timing(dict(job.provider_metadata or {}), "queued")
    db.commit()
    db.refresh(job)
    enqueue_image_job(job.id)
    return _job_to_out(job)


@router.post("/{job_id}/cancel", response_model=JobOut)
def cancel_job(job_id: str, user: RequireUser, db: Session = Depends(get_db)):
    job = _get_user_job(db, job_id, user)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("PENDING", "PROCESSING"):
        raise HTTPException(status_code=400, detail="Only pending or processing jobs can be cancelled")

    celery_task_id = job.celery_task_id
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

    return _job_to_out(job)


@router.delete("/{job_id}")
def delete_job(job_id: str, user: RequireUser, db: Session = Depends(get_db)):
    job = _get_user_job(db, job_id, user)
    if not job and user.role == "admin":
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return {"success": True}
