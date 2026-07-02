"""Upload local or remote images to fal CDN for provider jobs."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import httpx
from fal_client import SyncClient

from app.config import get_settings

FETCH_TIMEOUT = 120.0


def discover_public_app_base() -> str | None:
    """Resolve the public web URL (web tier) from env — works on worker services too."""
    cfg = get_settings()
    candidates: list[str] = [cfg.api_public_url]
    for key in ("RAILWAY_PUBLIC_DOMAIN", "RAILWAY_STATIC_URL"):
        val = os.environ.get(key, "")
        if val:
            candidates.append(val)
    for key, val in os.environ.items():
        if key.startswith("RAILWAY_SERVICE_") and key.endswith("_URL") and val:
            candidates.append(val)

    for raw in candidates:
        base = (raw or "").strip().rstrip("/")
        if not base:
            continue
        if not base.startswith("http"):
            base = f"https://{base.removeprefix('https://').removeprefix('http://')}"
        if "localhost" in base or "127.0.0.1" in base:
            continue
        return base
    return None


def _client(api_key: str) -> SyncClient:
    return SyncClient(key=api_key, default_timeout=120.0)


def upload_bytes_to_fal(data: bytes, content_type: str, api_key: str, file_name: str | None = None) -> str:
    client = _client(api_key)
    return client.upload(data, content_type, file_name=file_name)


def upload_file_to_fal(path: Path, api_key: str) -> str:
    client = _client(api_key)
    return client.upload_file(str(path))


async def fetch_and_upload_to_fal(url: str, api_key: str) -> str:
    async with httpx.AsyncClient(timeout=FETCH_TIMEOUT, follow_redirects=True) as http:
        resp = await http.get(url)
        resp.raise_for_status()
        data = resp.content
        content_type = (resp.headers.get("content-type") or "image/jpeg").split(";")[0].strip()
    return await asyncio.to_thread(upload_bytes_to_fal, data, content_type, api_key)
