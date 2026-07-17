"""Unified image preprocessing for fal model requests."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from app.providers.fal_upload import fetch_and_upload_to_fal, upload_bytes_to_fal, upload_file_to_fal
from app.providers.fal_url_cache import (
    clear_fal_url_cache,
    content_digest,
    get_cached_fal_url,
    set_cached_fal_url,
    url_digest,
)
from app.providers.model_catalog.spec import ImageContract, ModelSpec
from app.storage.local import storage

# Back-compat alias for tests
clear_upload_cache = clear_fal_url_cache


@dataclass
class PreparedImages:
    fal_urls: list[str]
    roles: list[str]
    skipped: list[str]


def _is_fal_cdn_url(url: str) -> bool:
    return url.startswith("https://") and ("fal.media" in url or "fal-cdn" in url or "fal.ai" in url)


async def ensure_fal_url(url: str, api_key: str) -> str:
    """Resolve a local/app/remote image URL to a fal CDN URL with durable caching."""
    if _is_fal_cdn_url(url):
        return url

    # Cache by source URL string for remote/shared references (bulk reuse)
    url_key = url_digest(url)
    cached = get_cached_fal_url(url_key)
    if cached:
        return cached

    blob = storage.read_bytes_by_url(url)
    if blob is not None:
        digest = content_digest(blob)
        hit = get_cached_fal_url(digest)
        if hit:
            set_cached_fal_url(url_key, hit)
            return hit
        ext = Path(url).suffix.lower()
        content_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }.get(ext, "image/jpeg")
        fal_url = await asyncio.to_thread(upload_bytes_to_fal, blob, content_type, api_key)
        set_cached_fal_url(digest, fal_url)
        set_cached_fal_url(url_key, fal_url)
        return fal_url

    local = storage.resolve_path(url)
    if local and local.exists():
        data = local.read_bytes()
        digest = content_digest(data)
        hit = get_cached_fal_url(digest)
        if hit:
            set_cached_fal_url(url_key, hit)
            return hit
        fal_url = await asyncio.to_thread(upload_file_to_fal, local, api_key)
        set_cached_fal_url(digest, fal_url)
        set_cached_fal_url(url_key, fal_url)
        return fal_url

    if url.startswith("http://") or url.startswith("https://"):
        fal_url = await fetch_and_upload_to_fal(url, api_key)
        set_cached_fal_url(url_key, fal_url)
        return fal_url

    public_url = storage.public_url(url)
    if public_url != url:
        fal_url = await fetch_and_upload_to_fal(public_url, api_key)
        set_cached_fal_url(url_key, fal_url)
        return fal_url

    raise ValueError(f"Cannot resolve input image: {url}")


def validate_image_count(contract: ImageContract, count: int) -> None:
    if contract.mode == "none":
        return
    if count < contract.min_images:
        raise ValueError(
            f"This model requires at least {contract.min_images} image(s); received {count}."
        )
    if contract.max_images and count > contract.max_images:
        raise ValueError(
            f"This model accepts at most {contract.max_images} image(s); received {count}."
        )


async def prepare_images(
    spec: ModelSpec,
    image_urls: list[str],
    api_key: str,
    *,
    enforce_limits: bool = True,
) -> PreparedImages:
    """Upload/resolve images and enforce the model's ImageContract limits."""
    contract = spec.image
    urls = list(image_urls or [])
    if enforce_limits:
        validate_image_count(contract, len(urls))
    if contract.max_images and len(urls) > contract.max_images:
        urls = urls[: contract.max_images]

    fal_urls: list[str] = []
    for url in urls:
        fal_urls.append(await ensure_fal_url(url, api_key))

    roles = list(contract.roles)
    return PreparedImages(fal_urls=fal_urls, roles=roles, skipped=[])


def prepared_to_request_urls(prepared: PreparedImages) -> list[str]:
    return list(prepared.fal_urls)
