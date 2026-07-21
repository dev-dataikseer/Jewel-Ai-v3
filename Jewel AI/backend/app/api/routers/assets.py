import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.auth.deps import RequireUser
from app.config import get_settings
from app.database import get_db
from app.models import Asset
from app.pipeline.validator import validate_upload
from app.providers.fal_upload import upload_bytes_to_fal
from app.schemas.common import AssetOut
from app.storage.local import storage

settings = get_settings()


def _asset_out(asset: Asset) -> AssetOut:
    from app.security.media_signing import sign_media_url

    out = AssetOut.model_validate(asset)
    data = out.model_dump()
    data["original_url"] = sign_media_url(data.get("original_url")) or data.get("original_url")
    # processed_url may be fal CDN — leave as-is if absolute non-upload
    data["processed_url"] = sign_media_url(data.get("processed_url")) if data.get("processed_url") else None
    return AssetOut.model_validate(data)


def _mirror_to_fal_cdn(content: bytes, content_type: str, filename: str) -> str | None:
    if not settings.fal_key:
        return None
    try:
        return upload_bytes_to_fal(content, content_type, settings.fal_key, file_name=filename)
    except Exception:
        return None


def _persist_asset(
    db: Session,
    *,
    user_id: str,
    content: bytes,
    content_type: str,
    filename: str,
) -> Asset:
    try:
        url = storage.save_bytes(content, filename=filename, content_type=content_type)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Image storage upload failed — check R2/S3 credentials ({type(exc).__name__})",
        ) from exc
    fal_url = _mirror_to_fal_cdn(content, content_type, filename)
    asset = Asset(
        user_id=user_id,
        original_url=url,
        processed_url=fal_url,
        type="PRODUCT",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("/upload", response_model=AssetOut)
async def upload_asset(
    user: RequireUser,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    content_type = file.content_type or "image/jpeg"
    validate_upload(content_type, len(content), content)
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(content_type, ".jpg")
    filename = f"asset-{uuid.uuid4().hex}{ext}"
    asset = await run_in_threadpool(
        _persist_asset,
        db,
        user_id=user.id,
        content=content,
        content_type=content_type,
        filename=filename,
    )
    return _asset_out(asset)


@router.post("/bulk-upload", response_model=list[AssetOut])
async def bulk_upload(
    user: RequireUser,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    if len(files) > 30:
        raise HTTPException(status_code=400, detail="Maximum 30 files")

    prepared: list[tuple[bytes, str, str]] = []
    for file in files:
        content = await file.read()
        content_type = file.content_type or "image/jpeg"
        validate_upload(content_type, len(content), content)
        ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(content_type, ".jpg")
        filename = f"asset-{uuid.uuid4().hex}{ext}"
        prepared.append((content, content_type, filename))

    def _persist_all() -> list[Asset]:
        assets: list[Asset] = []
        for content, content_type, filename in prepared:
            try:
                url = storage.save_bytes(content, filename=filename, content_type=content_type)
            except Exception as exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"Image storage upload failed — check R2/S3 credentials ({type(exc).__name__})",
                ) from exc
            fal_url = _mirror_to_fal_cdn(content, content_type, filename)
            asset = Asset(
                user_id=user.id,
                original_url=url,
                processed_url=fal_url,
                type="PRODUCT",
            )
            db.add(asset)
            assets.append(asset)
        db.commit()
        for a in assets:
            db.refresh(a)
        return assets

    assets = await run_in_threadpool(_persist_all)
    return [_asset_out(a) for a in assets]
