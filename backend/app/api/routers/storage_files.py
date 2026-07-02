from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.storage.local import storage

router = APIRouter(tags=["storage"])


@router.get("/uploads/{file_path:path}")
def serve_upload(file_path: str):
    if ".." in file_path or file_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")
    try:
        data, content_type = storage.read_upload(file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found") from None
    return Response(content=data, media_type=content_type)
