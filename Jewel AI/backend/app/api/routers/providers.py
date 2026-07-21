from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.auth.deps import RequireAdmin
from app.auth.security import decode_webhook_token, encrypt_secret
from app.database import get_db
from app.logging_config import get_logger
from app.models import GenerationJob, Provider
from app.providers.registry import build_adapter
from app.providers.router import check_all_provider_health
from app.schemas.common import ProviderOut, ProviderUpdate

logger = get_logger(__name__)

router = APIRouter(prefix="/providers", tags=["providers"])


def extract_fal_webhook_request_id(payload: dict) -> str | None:
    """Pull fal request id from common webhook payload shapes."""
    if not isinstance(payload, dict):
        return None
    for key in ("request_id", "requestId", "gateway_request_id"):
        val = payload.get(key)
        if val:
            return str(val)
    nested = payload.get("payload")
    if isinstance(nested, dict):
        for key in ("request_id", "requestId"):
            val = nested.get(key)
            if val:
                return str(val)
    return None


def _expected_fal_request_id(job: GenerationJob) -> str | None:
    meta = job.provider_metadata or {}
    return meta.get("fal_request_id") or (meta.get("usage") or {}).get("request_id")


def _provider_out(p: Provider) -> ProviderOut:
    return ProviderOut(
        id=p.id,
        name=p.name,
        display_name=p.display_name,
        model_name=p.model_name,
        priority=p.priority,
        is_active=p.is_active,
        health_status=p.health_status,
        has_api_key=bool(p.encrypted_api_key),
        has_admin_api_key=bool(getattr(p, "encrypted_admin_api_key", None)),
        capabilities=p.capabilities or {},
    )


@router.get("", response_model=list[ProviderOut])
def list_providers(user: RequireAdmin, db: Session = Depends(get_db)):
    return [_provider_out(p) for p in db.query(Provider).filter(Provider.name == "FAL").order_by(Provider.priority).all()]


@router.patch("/{name}")
def update_provider(
    name: str,
    body: ProviderUpdate,
    user: RequireAdmin,
    request: Request,
    db: Session = Depends(get_db),
):
    if name.upper() != "FAL":
        raise HTTPException(status_code=404, detail="Provider not found")
    prov = db.query(Provider).filter(Provider.name == name.upper()).first()
    if not prov:
        raise HTTPException(status_code=404, detail="Provider not found")
    before = {"model_name": prov.model_name, "is_active": prov.is_active, "priority": prov.priority}
    if body.model_name is not None:
        prov.model_name = body.model_name
    if body.api_key:
        prov.encrypted_api_key = encrypt_secret(body.api_key)
    if body.admin_api_key:
        prov.encrypted_admin_api_key = encrypt_secret(body.admin_api_key)
    if body.is_active is not None:
        prov.is_active = body.is_active
    if body.priority is not None:
        prov.priority = body.priority
    if body.base_url is not None:
        prov.base_url = body.base_url
    from app.services.audit import write_audit

    write_audit(
        db,
        actor_user_id=user.id,
        action="provider.update",
        entity_type="provider",
        entity_id=prov.name,
        before=before,
        after={
            "model_name": prov.model_name,
            "is_active": prov.is_active,
            "priority": prov.priority,
            "api_key_rotated": bool(body.api_key),
            "admin_key_rotated": bool(body.admin_api_key),
        },
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    return _provider_out(prov)


@router.post("/{name}/test")
async def test_provider(name: str, user: RequireAdmin, db: Session = Depends(get_db)):
    if name.upper() != "FAL":
        raise HTTPException(status_code=404)
    prov = db.query(Provider).filter(Provider.name == name.upper()).first()
    if not prov:
        raise HTTPException(status_code=404)
    adapter = build_adapter(prov)
    status = await adapter.health_check()
    return {"healthy": status.healthy, "message": status.message}


@router.get("/health")
async def provider_health(user: RequireAdmin, db: Session = Depends(get_db)):
    return await check_all_provider_health(db)


def _fal_webhook_sync(db: Session, job_id: str, payload: dict) -> dict:
    """Sync DB + accept path for fal webhooks (runs in threadpool from async route)."""
    # Row lock so concurrent fal retries cannot double-accept finalize.
    job = (
        db.query(GenerationJob)
        .filter(GenerationJob.id == job_id)
        .with_for_update()
        .first()
    )
    if not job:
        return {"status": "ignored"}
    if job.status == "COMPLETED":
        return {"status": "already_processed", "reason": "already_completed"}
    if job.status != "PROCESSING":
        return {"status": "ignored", "reason": "not_processing"}

    expected_req = _expected_fal_request_id(job)
    if not expected_req:
        logger.warning(
            "webhook_not_ready_missing_fal_request_id",
            extra={"extra_fields": {"job_id": job_id}},
        )
        raise HTTPException(status_code=409, detail="Job not ready for webhook")

    payload_req = extract_fal_webhook_request_id(payload)
    if not payload_req or payload_req != str(expected_req):
        logger.warning(
            "webhook_request_id_mismatch",
            extra={
                "extra_fields": {
                    "job_id": job_id,
                    "expected": expected_req,
                    "got": payload_req,
                }
            },
        )
        raise HTTPException(status_code=403, detail="request_id mismatch")

    status = payload.get("status")
    if status == "OK":
        if (job.provider_metadata or {}).get("webhook_completed"):
            return {"status": "already_processed", "reason": "already_processed"}

        # Mark accepted so stuck sweep won't re-queue while finalize runs.
        meta = dict(job.provider_metadata or {})
        meta["webhook_accepted"] = True
        job.provider_metadata = meta
        db.commit()

        import asyncio
        import threading

        from app.tasks.generate import _finalize_fal_webhook_async, finalize_fal_webhook

        # Always finalize on the API process first. Celery workers have historically
        # discarded unregistered finalize_fal_webhook tasks, which left jobs stuck
        # on "Waiting on fal.ai" forever after fal already finished.
        def _run() -> None:
            try:
                asyncio.run(_finalize_fal_webhook_async(job_id, payload))
            except Exception as exc:
                logger.error("Webhook finalize thread failed for %s: %s", job_id, exc)

        threading.Thread(target=_run, daemon=True, name=f"webhook-{job_id[:8]}").start()

        # Best-effort durable enqueue (ignore if worker hasn't registered the task).
        try:
            from app.services.queue_dispatch import celery_worker_available

            if celery_worker_available():
                finalize_fal_webhook.delay(job_id, payload)
        except Exception as exc:
            logger.debug("Celery finalize enqueue skipped for %s: %s", job_id, exc)

        return {"status": "processing_image"}

    if status == "ERROR":
        if job.status != "COMPLETED":
            error = payload.get("error", "Unknown webhook error")
            job.status = "FAILED"
            job.error_message = str(error)
            db.commit()
            if job.batch_id:
                try:
                    from app.tasks.generate import _update_batch

                    _update_batch(db, job.batch_id)
                except Exception as exc:
                    logger.error("Batch update after webhook ERROR failed for %s: %s", job_id, exc)

    return {"status": "ok"}


@router.post("/fal/webhook/{job_id}")
async def fal_webhook(
    job_id: str,
    request: Request,
    token: str = Query(..., alias="token"),
    db: Session = Depends(get_db),
):
    if not decode_webhook_token(token, job_id):
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    return await run_in_threadpool(_fal_webhook_sync, db, job_id, payload)
