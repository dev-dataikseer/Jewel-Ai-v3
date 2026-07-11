from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.auth.deps import get_current_user
from app.models import User
from app.security.media_signing import verify_upload_signature
from app.storage.local import storage

router = APIRouter(tags=["storage"])


@router.get("/uploads/{file_path:path}")
def serve_upload(
    file_path: str,
    exp: str | None = Query(None),
    sig: str | None = Query(None),
    user: User | None = Depends(get_current_user),
):
    if ".." in file_path or file_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")
    signed_ok = verify_upload_signature(file_path, exp, sig)
    if not signed_ok and user is None:
        raise HTTPException(status_code=401, detail="Authentication or signed URL required")
    try:
        data, content_type = storage.read_upload(file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found") from None
    return Response(content=data, media_type=content_type)
