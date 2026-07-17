"""Durable fal CDN URL cache (Redis when available, process memory fallback)."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

_MEMORY: dict[str, str] = {}
_REDIS: Any = None
_REDIS_CHECKED = False
CACHE_PREFIX = "jewel:fal-url:"
# 14 days — fal CDN URLs are long-lived for reused product/reference assets
CACHE_TTL_SECONDS = 14 * 24 * 3600


def _redis():
    global _REDIS, _REDIS_CHECKED
    if _REDIS_CHECKED:
        return _REDIS
    _REDIS_CHECKED = True
    try:
        import redis

        client = redis.from_url(get_settings().redis_url, socket_connect_timeout=1, decode_responses=True)
        client.ping()
        _REDIS = client
    except Exception:
        _REDIS = None
    return _REDIS


def content_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def url_digest(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def get_cached_fal_url(digest: str) -> str | None:
    key = f"{CACHE_PREFIX}{digest}"
    client = _redis()
    if client is not None:
        try:
            val = client.get(key)
            if val:
                return str(val)
        except Exception as exc:
            logger.debug("fal url cache redis get failed: %s", exc)
    return _MEMORY.get(digest)


def set_cached_fal_url(digest: str, fal_url: str) -> None:
    if not fal_url:
        return
    _MEMORY[digest] = fal_url
    # Bound memory map in long-lived workers
    if len(_MEMORY) > 5000:
        for k in list(_MEMORY.keys())[:1000]:
            _MEMORY.pop(k, None)
    client = _redis()
    if client is not None:
        try:
            client.setex(f"{CACHE_PREFIX}{digest}", CACHE_TTL_SECONDS, fal_url)
        except Exception as exc:
            logger.debug("fal url cache redis set failed: %s", exc)


def clear_fal_url_cache() -> None:
    _MEMORY.clear()
    client = _redis()
    if client is None:
        return
    try:
        keys = list(client.scan_iter(f"{CACHE_PREFIX}*", count=200))
        if keys:
            client.delete(*keys)
    except Exception:
        pass
