from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GenerationJob, ShareLink

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/share/{token}")
def public_share(token: str, db: Session = Depends(get_db)):
    link = db.query(ShareLink).filter(ShareLink.token == token).first()
    if not link:
        raise HTTPException(status_code=404, detail="Share link not found")
    if link.expires_at and link.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Share link expired")
    job = db.query(GenerationJob).filter(GenerationJob.id == link.job_id).first()
    if not job:
        raise HTTPException(status_code=404)
    link.views += 1
    db.commit()
    return {
        "workflow": job.workflow,
        "output_url": job.output_url,
        "jewelry_type": job.jewelry_type,
        "created_at": job.created_at,
    }
