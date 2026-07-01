from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
import httpx

from app.auth.deps import RequireAdmin
from app.auth.security import encrypt_secret
from app.database import get_db, SessionLocal
from app.models import Provider, GenerationJob
from app.providers.registry import build_adapter
from app.providers.router import check_all_provider_health
from app.schemas.common import ProviderOut, ProviderUpdate
from app.providers.fal_response import extract_image_urls
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/providers", tags=["providers"])


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
        capabilities=p.capabilities or {},
    )


@router.get("", response_model=list[ProviderOut])
def list_providers(user: RequireAdmin, db: Session = Depends(get_db)):
    return [_provider_out(p) for p in db.query(Provider).filter(Provider.name == "FAL").order_by(Provider.priority).all()]


@router.patch("/{name}")
def update_provider(name: str, body: ProviderUpdate, user: RequireAdmin, db: Session = Depends(get_db)):
    if name.upper() != "FAL":
        raise HTTPException(status_code=404, detail="Provider not found")
    prov = db.query(Provider).filter(Provider.name == name.upper()).first()
    if not prov:
        raise HTTPException(status_code=404, detail="Provider not found")
    if body.model_name is not None:
        prov.model_name = body.model_name
    if body.api_key:
        prov.encrypted_api_key = encrypt_secret(body.api_key)
    if body.is_active is not None:
        prov.is_active = body.is_active
    if body.priority is not None:
        prov.priority = body.priority
    if body.base_url is not None:
        prov.base_url = body.base_url
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


@router.post("/fal/webhook/{job_id}")
async def fal_webhook(job_id: str, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    payload = await request.json()
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job or job.status != "PROCESSING":
        return {"status": "ignored"}

    status = payload.get("status")
    if status == "OK":
        payload_data = payload.get("payload") or {}
        from app.providers.registry import get_model_definition

        model_def = get_model_definition(db, job.provider_model) if job.provider_model else None
        config = (model_def.config or {}) if model_def else {}
        img_urls = extract_image_urls(payload, config) or extract_image_urls(payload_data, config)

        if img_urls:
            async def process_image():
                db_local = SessionLocal()
                try:
                    from app.storage.local import storage
                    from app.services.credits import deduct_credits_for_job
                    from app.tasks.generate import _update_batch

                    extra_urls: list[str] = []
                    primary_url = ""
                    async with httpx.AsyncClient(timeout=120.0) as http:
                        for idx, img_url in enumerate(img_urls):
                            resp = await http.get(img_url)
                            resp.raise_for_status()
                            suffix = "" if idx == 0 else f"_{idx + 1}"
                            saved_url = storage.save_bytes(
                                resp.content, filename=f"generated_{job_id}{suffix}.png"
                            )
                            if idx == 0:
                                primary_url = saved_url
                            else:
                                extra_urls.append(saved_url)

                    job_local = db_local.query(GenerationJob).filter(GenerationJob.id == job_id).first()
                    if job_local:
                        meta = job_local.provider_metadata or {}
                        job_local.output_url = primary_url
                        job_local.output_urls = extra_urls if extra_urls else None
                        job_local.status = "COMPLETED"
                        job_local.provider_metadata = {**meta, "webhook_completed": True}
                        job_local.credits_used = max(1, int((job_local.cost or 0.1) * 100))
                        db_local.commit()
                        if job_local.user_id:
                            deduct_credits_for_job(db_local, job_local.user_id, job_local.credits_used, job_local.id)
                        if job_local.batch_id:
                            _update_batch(db_local, job_local.batch_id)
                except Exception as e:
                    logger.error(f"Failed to process webhook image for job {job_id}: {e}")
                    job_local = db_local.query(GenerationJob).filter(GenerationJob.id == job_id).first()
                    if job_local:
                        job_local.status = "FAILED"
                        job_local.error_message = f"Webhook image download failed: {str(e)}"
                        db_local.commit()
                finally:
                    db_local.close()

            background_tasks.add_task(process_image)
            return {"status": "processing_image"}
            
    elif status == "ERROR":
        error = payload.get("error", "Unknown webhook error")
        job.status = "FAILED"
        job.error_message = str(error)
        db.commit()
    
    return {"status": "ok"}
