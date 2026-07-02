from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.config import get_settings
from app.storage.object_store import get_object_bytes, get_s3_client, parse_upload_path, put_object

settings = get_settings()

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class StorageService:
    def __init__(self) -> None:
        self.backend = settings.storage_backend.lower()
        self.uploads_dir = Path(settings.uploads_dir)
        if self.backend == "local":
            self.uploads_dir.mkdir(parents=True, exist_ok=True)

    @property
    def uses_object_storage(self) -> bool:
        return self.backend in {"r2", "s3", "object"}

    def _s3_client(self):
        if not settings.r2_endpoint_url or not settings.r2_bucket_name:
            raise RuntimeError("Object storage is not configured (R2_ENDPOINT_URL, R2_BUCKET_NAME)")
        return get_s3_client(
            settings.r2_endpoint_url,
            settings.r2_access_key_id,
            settings.r2_secret_access_key,
            region="auto",
        )

    def save_bytes(self, data: bytes, filename: str | None = None, content_type: str = "image/png") -> str:
        name = filename or f"{uuid4().hex}.png"
        if self.uses_object_storage:
            put_object(self._s3_client(), settings.r2_bucket_name, name, data, content_type)
            return f"/uploads/{name}"
        path = self.uploads_dir / name
        path.write_bytes(data)
        return f"/uploads/{name}"

    def save_upload(self, file: BinaryIO, filename: str, content_type: str) -> str:
        return self.save_bytes(file.read(), filename=filename, content_type=content_type)

    def resolve_path(self, url: str) -> Path | None:
        if self.uses_object_storage:
            return None
        if not url.startswith("/uploads/"):
            return None
        path = self.uploads_dir / url.replace("/uploads/", "", 1)
        if path.exists():
            return path
        return None

    def read_upload(self, filename: str) -> tuple[bytes, str]:
        ext = Path(filename).suffix.lower()
        content_type = _CONTENT_TYPES.get(ext, "application/octet-stream")
        if self.uses_object_storage:
            try:
                data = get_object_bytes(self._s3_client(), settings.r2_bucket_name, filename)
            except Exception as exc:
                raise FileNotFoundError(filename) from exc
            return data, content_type
        path = self.uploads_dir / filename
        if not path.exists():
            raise FileNotFoundError(filename)
        return path.read_bytes(), content_type

    def public_url(self, url: str) -> str:
        """Absolute URL for external services (fal worker fetch)."""
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if url.startswith("/uploads/"):
            base = settings.api_public_url.rstrip("/")
            return f"{base}{url}"
        return url

    def read_bytes_by_url(self, url: str) -> bytes | None:
        filename = parse_upload_path(url)
        if not filename:
            return None
        try:
            data, _ = self.read_upload(filename)
            return data
        except FileNotFoundError:
            return None


storage = StorageService()
