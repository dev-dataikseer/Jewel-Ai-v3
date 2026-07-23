from typing import Optional, Tuple
from app.database import SessionLocal
from app.models import GenerationJob, ShareLink
from app.security.media_signing import sign_media_url
from app.config import get_settings


def get_share_og_metadata(token: str) -> Tuple[str, str, Optional[str]]:
    """
    Returns (title, description, image_url) for a given share token.
    If the token is invalid or the job is missing, returns default fallbacks.
    """
    title = "Jewel AI Studio"
    description = "Jewelry design AI generation"
    image = None
    settings = get_settings()

    db = SessionLocal()
    try:
        link = db.query(ShareLink).filter(ShareLink.token == token).first()
        if link:
            job = db.query(GenerationJob).filter(GenerationJob.id == link.job_id).first()
            if job:
                title = f"Jewel AI — {job.workflow}"
                if job.jewelry_type:
                    description = f"{job.jewelry_type} · {job.workflow}"
                raw = job.output_url or ((job.output_urls or [None])[0])
                if raw:
                    signed = sign_media_url(raw) or raw
                    if signed.startswith("http"):
                        image = signed
                    else:
                        image = f"{settings.api_public_url.rstrip('/')}{signed}"
    finally:
        db.close()

    return title, description, image
