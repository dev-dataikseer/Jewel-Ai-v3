"""Shared lazy Redis client singleton.

All modules that need a Redis connection (rate limiting, ETA samples,
job leases, etc.) should import from here to avoid each owning its own
connection state and retry logic.
"""

from __future__ import annotations

import time
from typing import Any

_redis_client: Any = None
_redis_checked_at: float = 0.0
_RETRY_SECONDS: float = 5.0


def get_redis_client() -> Any:
    """Return a connected Redis client, or None if unavailable.

    Retries connection after ``_RETRY_SECONDS`` so a transient Redis
    blip does not permanently latch the client to None.
    """
    global _redis_client, _redis_checked_at
    now = time.time()

    if _redis_client is not None:
        return _redis_client

    if _redis_checked_at and (now - _redis_checked_at) < _RETRY_SECONDS:
        return None

    _redis_checked_at = now
    try:
        import redis

        from app.config import get_settings

        client = redis.from_url(
            get_settings().redis_url,
            socket_connect_timeout=1,
        )
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception:
        _redis_client = None
        return None


def invalidate_redis_client() -> None:
    """Drop the cached client so the next call reconnects.

    Call this when a Redis operation raises an exception, so the singleton
    does not stay latched to a dead connection.
    """
    global _redis_client
    _redis_client = None


def redis_available() -> bool:
    """Return True if Redis is reachable right now."""
    return get_redis_client() is not None
