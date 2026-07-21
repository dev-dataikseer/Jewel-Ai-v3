from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import get_db
from app.models import Asset, GenerationJob, User
from app.security.media_signing import verify_upload_signature
from app.storage.local import storage

router = APIRouter(tags=["storage"])


def _user_owns_upload(db: Session, user: User, file_path: str) -> bool:
    """True if the path appears on an asset or job owned by the user (or user is admin)."""
    if user.role == "admin":
        return True
    asset_hit = (
        db.query(Asset.id)
        .filter(
            Asset.user_id == user.id,
            (Asset.original_url.contains(file_path)) | (Asset.processed_url.contains(file_path)),
        )
        .first()
    )
    if asset_hit:
        return True
    job_hit = (
        db.query(GenerationJob.id)
        .filter(
            GenerationJob.user_id == user.id,
            (
                (GenerationJob.input_url.contains(file_path))
                | (GenerationJob.output_url.contains(file_path))
                | (GenerationJob.reference_url.contains(file_path))
                | (GenerationJob.model_url.contains(file_path))
            ),
        )
        .first()
    )
    return job_hit is not None


def authorize_upload_path(
    file_path: str,
    exp: str | None,
    sig: str | None,
    user: User | None,
    db: Session,
) -> None:
    if ".." in file_path or file_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")
    signed_ok = verify_upload_signature(file_path, exp, sig)
    if signed_ok:
        return
    if user is not None:
        if not _user_owns_upload(db, user, file_path):
            raise HTTPException(status_code=403, detail="Not allowed to access this file")
        return
    raise HTTPException(status_code=401, detail="Authentication or signed URL required")


@router.get("/uploads/{file_path:path}")
def serve_upload(
    file_path: str,
    exp: str | None = Query(None),
    sig: str | None = Query(None),
    user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorize_upload_path(file_path, exp, sig, user, db)
    try:
        data, content_type = storage.read_upload(file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found") from None
    return Response(content=data, media_type=content_type)
