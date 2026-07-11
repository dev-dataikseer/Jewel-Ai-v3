"""HMAC-signed upload URLs so <img> tags work without Bearer headers."""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from app.config import get_settings

DEFAULT_TTL_SECONDS = 60 * 60 * 24  # 24h


def _secret() -> bytes:
    return (get_settings().jwt_secret or "dev").encode("utf-8")


def sign_upload_path(file_path: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Return `/uploads/{path}?exp=...&sig=...` for a storage object key or /uploads path."""
    path = file_path.lstrip("/")
    if path.startswith("uploads/"):
        path = path[len("uploads/") :]
    exp = int(time.time()) + max(60, ttl_seconds)
    msg = f"{path}:{exp}".encode("utf-8")
    sig = hmac.new(_secret(), msg, hashlib.sha256).hexdigest()
    return f"/uploads/{path}?{urlencode({'exp': exp, 'sig': sig})}"


def verify_upload_signature(file_path: str, exp: str | None, sig: str | None) -> bool:
    if not exp or not sig:
        return False
    try:
        exp_i = int(exp)
    except ValueError:
        return False
    if exp_i < int(time.time()):
        return False
    path = file_path.lstrip("/")
    if path.startswith("uploads/"):
        path = path[len("uploads/") :]
    msg = f"{path}:{exp_i}".encode("utf-8")
    expected = hmac.new(_secret(), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def sign_media_url(url: str | None, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str | None:
    """Sign relative /uploads URLs; leave absolute non-upload URLs unchanged."""
    if not url:
        return url
    if url.startswith("http://") or url.startswith("https://"):
        parsed = urlparse(url)
        if not (parsed.path or "").startswith("/uploads/"):
            return url
        signed_path = sign_upload_path(parsed.path, ttl_seconds=ttl_seconds)
        # Preserve host; replace path+query
        signed = urlparse(signed_path)
        return urlunparse(
            (parsed.scheme, parsed.netloc, signed.path, "", signed.query, "")
        )
    if url.startswith("/uploads/"):
        # Strip existing query before resigning
        path = url.split("?", 1)[0]
        return sign_upload_path(path, ttl_seconds=ttl_seconds)
    return url
