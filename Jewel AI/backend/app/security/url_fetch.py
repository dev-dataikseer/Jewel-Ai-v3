"""SSRF-safe image URL fetching for webhooks, provider callbacks, and job inputs."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx

from app.config import get_settings

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
