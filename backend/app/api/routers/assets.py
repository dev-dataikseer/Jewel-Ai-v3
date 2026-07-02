import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.deps import RequireUser
from app.config import get_settings
from app.database import get_db
from app.models import Asset
from app.pipeline.validator import validate_upload
from app.providers.fal_upload import upload_bytes_to_fal
from app.schemas.common import AssetOut
from app.storage.local import storage

settings = get_settings()


def _mirror_to_fal_cdn(content: bytes, content_type: str, filename: str) -> str | None:
    if not settings.fal_key:
        return None
    try:
        return upload_bytes_to_fal(content, content_type, settings.fal_key, file_name=filename)
    except Exception:
        return None

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("/upload", response_model=AssetOut)
async def upload_asset(
    user: RequireUser,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    validate_upload(file.content_type or "image/jpeg", len(content), content)
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(file.content_type or "", ".jpg")
    filename = f"asset-{uuid.uuid4().hex}{ext}"
    url = storage.save_bytes(content, filename=filename, content_type=file.content_type or "image/jpeg")
    fal_url = _mirror_to_fal_cdn(content, file.content_type or "image/jpeg", filename)
    asset = Asset(
        user_id=user.id,
        original_url=url,
        processed_url=fal_url,
        type="PRODUCT",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/bulk-upload", response_model=list[AssetOut])
async def bulk_upload(
    user: RequireUser,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    if len(files) > 30:
        raise HTTPException(status_code=400, detail="Maximum 30 files")
    assets = []
    for file in files:
        content = await file.read()
        validate_upload(file.content_type or "image/jpeg", len(content), content)
        ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(file.content_type or "", ".jpg")
        filename = f"asset-{uuid.uuid4().hex}{ext}"
        url = storage.save_bytes(content, filename=filename, content_type=file.content_type or "image/jpeg")
        fal_url = _mirror_to_fal_cdn(content, file.content_type or "image/jpeg", filename)
        asset = Asset(user_id=user.id, original_url=url, processed_url=fal_url, type="PRODUCT")
        db.add(asset)
        assets.append(asset)
    db.commit()
    for a in assets:
        db.refresh(a)
    return assets
