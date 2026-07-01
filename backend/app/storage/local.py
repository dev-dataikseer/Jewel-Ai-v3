from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.config import get_settings

settings = get_settings()


class StorageService:
  def __init__(self) -> None:
    self.backend = settings.storage_backend
    self.uploads_dir = Path(settings.uploads_dir)
    if self.backend == "local":
      self.uploads_dir.mkdir(parents=True, exist_ok=True)

  def save_bytes(self, data: bytes, filename: str | None = None, content_type: str = "image/png") -> str:
    name = filename or f"{uuid4().hex}.png"
    if self.backend == "local":
      path = self.uploads_dir / name
      path.write_bytes(data)
      return f"/uploads/{name}"
    return self._save_r2(data, name, content_type)

  def save_upload(self, file: BinaryIO, filename: str, content_type: str) -> str:
    return self.save_bytes(file.read(), filename=filename, content_type=content_type)

  def resolve_path(self, url: str) -> Path | None:
    if not url.startswith("/uploads/"):
      return None
    return self.uploads_dir / url.replace("/uploads/", "")

  def _save_r2(self, data: bytes, name: str, content_type: str) -> str:
    import boto3
    from botocore.config import Config

    client = boto3.client(
      "s3",
      endpoint_url=settings.r2_endpoint_url,
      aws_access_key_id=settings.r2_access_key_id,
      aws_secret_access_key=settings.r2_secret_access_key,
      config=Config(signature_version="s3v4"),
    )
    key = f"uploads/{name}"
    client.put_object(Bucket=settings.r2_bucket_name, Key=key, Body=data, ContentType=content_type)
    if settings.r2_public_url:
      return f"{settings.r2_public_url.rstrip('/')}/{key}"
    return client.generate_presigned_url(
      "get_object",
      Params={"Bucket": settings.r2_bucket_name, "Key": key},
      ExpiresIn=3600,
    )


storage = StorageService()
