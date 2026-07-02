import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.auth.deps import RequireAdmin, RequireUser
from app.auth.security import create_job_stream_token, decode_job_stream_token
from app.database import SessionLocal, get_db
from app.models import Asset, Batch, Favorite, GenerationJob, Project, ShareLink, User
from app.pipeline.validator import validate_job_create, whitelist_job_fields
from app.providers.model_validate import validate_generation_request, validate_model_params
from app.providers.registry import get_model_definition, resolve_default_endpoint
from app.providers.types import GenerationRequest
from app.schemas.common import BulkJobCreate, JobCreate, JobOut, ShareLinkCreate
from app.services.credits import check_sufficient_credits
from app.services.queue_dispatch import enqueue_image_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_to_out(job: GenerationJob) -> JobOut:
    return JobOut.model_validate(job)


def _get_user_job(db: Session, job_id: str, user: User) -> GenerationJob | None:
    return (
        db.query(GenerationJob)
        .filter(GenerationJob.id == job_id, GenerationJob.user_id == user.id)
        .first()
    )


def _provider_meta(body: dict) -> dict:
    endpoint = body.get("model_endpoint_id") or body.get("model_name")
    return {
        "aspectRatio": body.get("aspect_ratio", "1:1"),
        "personGeneration": body.get("person_generation", "ALLOW_ADULT"),
        "numberOfImages": body.get("number_of_images", 1),
        "modelEndpointId": endpoint,
        "modelParams": body.get("model_params") or {},
        "modelName": endpoint,
    }


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
    data = body.model_dump()
    validate_job_create(data)
    if not check_sufficient_credits(db, user.id):
        raise HTTPException(status_code=402, detail="Insufficient credits")

    asset = (
        db.query(Asset)
        .filter(Asset.id == body.asset_id, Asset.user_id == user.id)
        .first()
        if body.asset_id
        else None
    )
    if body.asset_id and not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    image_count = 1
    if body.reference_url or body.model_url:
        image_count = 2
    data = _validate_job_model(db, data, body.workflow, image_count)

    project = Project(
        name=f"Project {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        workflow=body.workflow,
        user_id=user.id,
    )
    db.add(project)
    db.flush()

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
        input_url=asset.original_url if asset else None,
        provider_metadata=_provider_meta(data),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    enqueue_image_job(job.id)
    return job


@router.post("/bulk", response_model=dict)
def create_bulk_jobs(
    body: BulkJobCreate,
    user: RequireUser,
    db: Session = Depends(get_db),
):
    data = body.model_dump()
    data["workflow"] = "CATALOG_IMAGE"
    data["asset_ids"] = body.asset_ids
    validate_job_create(data)
    data = _validate_job_model(db, data, "CATALOG_IMAGE", 1)

    assets = db.query(Asset).filter(Asset.id.in_(body.asset_ids), Asset.user_id == user.id).all()
    if len(assets) != len(body.asset_ids):
        raise HTTPException(status_code=404, detail="One or more assets not found")

    batch = Batch(
        name=body.batch_name or f"Bulk {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        workflow="CATALOG_IMAGE",
        jewelry_type=body.jewelry_type,
        preset_id=body.style_preset_id,
        status="PROCESSING",
        total_jobs=len(assets),
    )
    db.add(batch)
    db.flush()

    project = Project(name=batch.name or "Bulk Project", workflow="BULK_GENERATION", user_id=user.id)
    db.add(project)
    db.flush()

    meta = _provider_meta(body.model_dump())
    job_ids = []
    for asset in assets:
        job = GenerationJob(
            user_id=user.id,
            project_id=project.id,
            batch_id=batch.id,
            asset_id=asset.id,
            workflow="CATALOG_IMAGE",
            status="PENDING",
            jewelry_type=body.jewelry_type,
            style_preset_id=body.style_preset_id,
            input_url=asset.original_url,
            provider_metadata=meta,
        )
        db.add(job)
        db.flush()
        job_ids.append(job.id)

    db.commit()
    for jid in job_ids:
        enqueue_image_job(jid)
    return {"batchId": batch.id, "jobIds": job_ids, "total": len(job_ids)}


@router.get("", response_model=dict)
def list_jobs(
    user: RequireUser,
    cursor: Optional[str] = None,
    limit: int = Query(20, le=100),
    status: Optional[str] = None,
    workflow: Optional[str] = None,
    favorites_only: bool = False,
    db: Session = Depends(get_db),
):
    q = db.query(GenerationJob).filter(GenerationJob.user_id == user.id).order_by(GenerationJob.created_at.desc())
    if status:
        q = q.filter(GenerationJob.status == status)
    if workflow:
        q = q.filter(GenerationJob.workflow == workflow)
    if favorites_only:
        q = q.join(Favorite, Favorite.job_id == GenerationJob.id).filter(Favorite.user_id == user.id)
    if cursor:
        q = q.filter(GenerationJob.id < cursor)
    rows = q.limit(limit + 1).all()
    has_more = len(rows) > limit
    items = rows[:limit]
    return {
        "items": [_job_to_out(j) for j in items],
        "next_cursor": items[-1].id if has_more and items else None,
    }


@router.post("/stream-token")
def create_stream_token(body: dict, user: RequireUser, db: Session = Depends(get_db)):
    job_ids = [str(j).strip() for j in body.get("job_ids", []) if str(j).strip()]
    if not job_ids:
        raise HTTPException(status_code=400, detail="job_ids required")
    for jid in job_ids:
        if not _get_user_job(db, jid, user):
            raise HTTPException(status_code=404, detail=f"Job not found: {jid}")
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
                    if job.status not in ("COMPLETED", "FAILED"):
                        terminal = False
                    key = f"{job.status}:{job.output_url}"
                    if seen.get(jid) != key:
                        seen[jid] = key
                        yield {
                            "event": "job_update",
                            "data": json.dumps(_job_to_out(job).model_dump(mode="json")),
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
    return job


@router.post("/{job_id}/regenerate", response_model=JobOut)
def regenerate_job(job_id: str, user: RequireUser, db: Session = Depends(get_db)):
    original = _get_user_job(db, job_id, user)
    if not original:
        raise HTTPException(status_code=404, detail="Job not found")

    job = GenerationJob(
        user_id=user.id,
        project_id=original.project_id,
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
        provider_metadata=original.provider_metadata,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    enqueue_image_job(job.id)
    return job


@router.delete("/{job_id}")
def delete_job(job_id: str, user: RequireAdmin, db: Session = Depends(get_db)):
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return {"success": True}
