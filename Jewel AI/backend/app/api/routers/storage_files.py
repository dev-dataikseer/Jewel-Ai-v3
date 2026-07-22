from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import get_db
from app.models import User
from app.security.media_signing import verify_upload_signature
from app.security.url_fetch import user_owns_upload_key
from app.storage.local import storage

router = APIRouter(tags=["storage"])


def _user_owns_upload(db: Session, user: User, file_path: str) -> bool:
    """True if the upload key exactly matches an asset or job URL owned by the user."""
    return user_owns_upload_key(db, user, file_path)


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
