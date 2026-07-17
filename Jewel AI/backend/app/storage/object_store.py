"""S3-compatible object storage (Railway Buckets, Cloudflare R2, etc.)."""

from __future__ import annotations

import functools

import boto3
from botocore.config import Config

OBJECT_KEY_PREFIX = "uploads/"


@functools.lru_cache(maxsize=1)
def get_s3_client(endpoint_url: str, access_key: str, secret_key: str, region: str = "auto"):
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region or "auto",
        config=Config(signature_version="s3v4"),
    )


def object_key(filename: str) -> str:
    return f"{OBJECT_KEY_PREFIX}{filename}"


def parse_upload_path(url: str) -> str | None:
    """Return filename for /uploads/<name> paths."""
    if not url.startswith("/uploads/"):
        return None
    name = url.removeprefix("/uploads/").lstrip("/")
    return name or None


def put_object(
    client,
    bucket: str,
    filename: str,
    data: bytes,
    content_type: str,
) -> None:
    client.put_object(
        Bucket=bucket,
        Key=object_key(filename),
        Body=data,
        ContentType=content_type,
    )


def get_object_bytes(client, bucket: str, filename: str) -> bytes:
    resp = client.get_object(Bucket=bucket, Key=object_key(filename))
    return resp["Body"].read()
