"""Cache layer for fal.ai billing snapshots (Redis preferred, memory fallback)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

CACHE_KEY = "jewel:fal-billing:v1"
_MEMORY: dict[str, Any] = {}
_REDIS = None
_REDIS_CHECKED = False


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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_cached_billing() -> dict[str, Any] | None:
    client = _redis()
    if client is not None:
        try:
            raw = client.get(CACHE_KEY)
            if raw:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return data
        except Exception as exc:
            logger.debug("billing cache redis get failed: %s", exc)
    data = _MEMORY.get(CACHE_KEY)
    return dict(data) if isinstance(data, dict) else None


def set_cached_billing(payload: dict[str, Any], *, ttl_seconds: int | None = None) -> dict[str, Any]:
    settings = get_settings()
    ttl = ttl_seconds if ttl_seconds is not None else int(settings.fal_billing_cache_ttl_seconds or 900)
    stored = {
        **payload,
        "cached_at": payload.get("cached_at") or _now_iso(),
        "updated_at": _now_iso(),
    }
    _MEMORY[CACHE_KEY] = stored
    client = _redis()
    if client is not None:
        try:
            client.setex(CACHE_KEY, max(60, ttl), json.dumps(stored))
        except Exception as exc:
            logger.debug("billing cache redis set failed: %s", exc)
    return stored
