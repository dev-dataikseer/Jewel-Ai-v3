import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.deps import RequireUser
from app.database import get_db
from app.models import Asset
from app.pipeline.validator import validate_upload
from app.schemas.common import AssetOut
from app.storage.local import storage

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("/upload", response_model=AssetOut)
async def upload_asset(
    user: RequireUser,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    validate_upload(file.content_type or "image/jpeg", len(content))
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(file.content_type or "", ".jpg")
    filename = f"asset-{uuid.uuid4().hex}{ext}"
    url = storage.save_bytes(content, filename=filename, content_type=file.content_type or "image/jpeg")
    asset = Asset(
        user_id=user.id,
        original_url=url,
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
        validate_upload(file.content_type or "image/jpeg", len(content))
        ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(file.content_type or "", ".jpg")
        filename = f"asset-{uuid.uuid4().hex}{ext}"
        url = storage.save_bytes(content, filename=filename, content_type=file.content_type or "image/jpeg")
        asset = Asset(user_id=user.id, original_url=url, type="PRODUCT")
        db.add(asset)
        assets.append(asset)
    db.commit()
    for a in assets:
        db.refresh(a)
    return assets
