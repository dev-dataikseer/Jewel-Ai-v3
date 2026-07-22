"""SSRF-safe image URL fetching for webhooks, provider callbacks, and job inputs."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Asset, GenerationJob, User

# Only dotted suffixes (or exact apex hosts listed separately).
# Never use bare "fal.ai" with endswith — that would allow evilfal.ai.
ALLOWED_HOST_SUFFIXES = (
    ".fal.media",
    ".fal.run",
    ".fal.ai",
    ".amazonaws.com",
    ".cloudfront.net",
    ".r2.dev",
)

ALLOWED_EXACT_HOSTS = frozenset(
    {
        "fal.media",
        "fal.run",
        "fal.ai",
    }
)


def _host_allowed(hostname: str) -> bool:
    host = hostname.lower().rstrip(".")
    if host in ALLOWED_EXACT_HOSTS:
        return True
    for suffix in ALLOWED_HOST_SUFFIXES:
        if host.endswith(suffix):
            return True
    return False


def _is_private_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    )


def _app_public_host() -> str | None:
    base = (get_settings().api_public_url or "").strip()
    if not base:
        return None
    if not base.startswith("http"):
        base = f"https://{base}"
    host = urlparse(base).hostname
    return host.lower() if host else None


def is_app_upload_url(url: str) -> bool:
    """True for relative /uploads paths or absolute URLs on our public API host."""
    raw = (url or "").strip()
    if not raw:
        return False
    if raw.startswith("/uploads/"):
        return True
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        return False
    path = parsed.path or ""
    if not path.startswith("/uploads/"):
        return False
    app_host = _app_public_host()
    host = (parsed.hostname or "").lower()
    if app_host and host == app_host:
        return True
    # Local/dev absolute uploads
    if host in ("localhost", "127.0.0.1") and "localhost" in (get_settings().api_public_url or ""):
        return True
    return False


def validate_image_url(url: str) -> None:
    """Raise ValueError if URL is not a safe HTTPS allowlisted image source."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Only HTTPS image URLs are allowed")
    host = parsed.hostname
    if not host:
        raise ValueError("Invalid image URL")
    if host in ("localhost", "127.0.0.1", "0.0.0.0") or host.endswith(".local"):
        raise ValueError("Localhost URLs are not allowed")
    if not _host_allowed(host):
        raise ValueError(f"Image host not allowlisted: {host}")
    try:
        for info in socket.getaddrinfo(host, None):
            if _is_private_ip(info[4][0]):
                raise ValueError("Image URL resolves to a private address")
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve image host: {host}") from exc


def validate_user_image_url(url: str | None) -> None:
    """Validate user-supplied reference/model/input URLs at job create time."""
    if not url or not str(url).strip():
        return
    raw = str(url).strip()
    if is_app_upload_url(raw):
        return
    validate_image_url(raw)


def extract_upload_key(url: str | None) -> str | None:
    """Normalize an upload URL to its storage key.

    `/uploads/foo.png` or `https://host/uploads/foo.png?sig=...` → `foo.png`
    """
    if not url or not str(url).strip():
        return None
    raw = str(url).strip()
    path = urlparse(raw).path if "://" in raw else raw.split("?", 1)[0]
    path = (path or "").split("?", 1)[0]
    marker = "/uploads/"
    idx = path.find(marker)
    if idx < 0:
        return None
    key = path[idx + len(marker) :].lstrip("/")
    return key or None


def user_owns_upload_key(db: Session, user: User, file_path: str) -> bool:
    """True if upload key equals a URL key on an asset/job owned by the user (or admin)."""
    if getattr(user, "role", None) == "admin":
        return True
    key = (file_path or "").lstrip("/")
    if not key or ".." in key:
        return False

    assets = (
        db.query(Asset.original_url, Asset.processed_url)
        .filter(
            Asset.user_id == user.id,
            or_(
                Asset.original_url.contains(key),
                Asset.processed_url.contains(key),
            ),
        )
        .all()
    )
    for original_url, processed_url in assets:
        if extract_upload_key(original_url) == key or extract_upload_key(processed_url) == key:
            return True

    jobs = (
        db.query(
            GenerationJob.input_url,
            GenerationJob.output_url,
            GenerationJob.reference_url,
            GenerationJob.model_url,
            GenerationJob.provider_metadata,
        )
        .filter(
            GenerationJob.user_id == user.id,
            or_(
                GenerationJob.input_url.contains(key),
                GenerationJob.output_url.contains(key),
                GenerationJob.reference_url.contains(key),
                GenerationJob.model_url.contains(key),
                cast(GenerationJob.provider_metadata, String).contains(key),
            ),
        )
        .limit(100)
        .all()
    )
    for input_url, output_url, reference_url, model_url, provider_metadata in jobs:
        for candidate in (input_url, output_url, reference_url, model_url):
            if extract_upload_key(candidate) == key:
                return True
        meta = provider_metadata or {}
        if isinstance(meta, dict) and extract_upload_key(meta.get("logoUrl")) == key:
            return True
    return False


def assert_user_owns_upload_url(db: Session, user: User, url: str | None) -> None:
    """For app upload URLs, require the user owns the exact upload key."""
    if not url or not str(url).strip():
        return
    raw = str(url).strip()
    if not is_app_upload_url(raw):
        return
    key = extract_upload_key(raw)
    if not key:
        raise ValueError("Invalid upload URL")
    if not user_owns_upload_key(db, user, key):
        raise ValueError("Upload URL is not owned by the current user")


def validate_user_owned_image_url(db: Session, user: User, url: str | None) -> None:
    """SSRF allowlist plus ownership check for app upload URLs."""
    validate_user_image_url(url)
    assert_user_owns_upload_url(db, user, url)


async def safe_fetch_image_bytes(url: str, timeout: float = 120.0) -> bytes:
    validate_image_url(url)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as http:
        resp = await http.get(url)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("text/"):
            raise ValueError("Refusing to fetch non-image content")
        return resp.content


def safe_fetch_image_bytes_sync(url: str, timeout: float = 120.0) -> bytes:
    """Synchronous SSRF-safe fetch (no redirects) for sync callers like logo compose."""
    validate_image_url(url)
    with httpx.Client(timeout=timeout, follow_redirects=False) as http:
        resp = http.get(url)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("text/"):
            raise ValueError("Refusing to fetch non-image content")
        return resp.content
