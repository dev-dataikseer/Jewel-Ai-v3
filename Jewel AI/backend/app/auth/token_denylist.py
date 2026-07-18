"""Redis-backed refresh-token jti denylist and rotation helpers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.config import get_settings

logger = logging.getLogger(__name__)

_DENY_PREFIX = "jewel:refresh-deny:"
_LOCAL_DENY: set[str] = set()


def _redis_client():
    import redis

    return redis.from_url(get_settings().redis_url, socket_connect_timeout=1)


def deny_refresh_jti(jti: str | None, *, exp: int | float | None = None) -> None:
    """Mark a refresh jti as revoked until its original expiry (or 7 days)."""
    if not jti:
        return
    ttl = 7 * 24 * 3600
    if exp is not None:
        try:
            remaining = int(exp) - int(datetime.now(timezone.utc).timestamp())
            ttl = max(60, remaining)
        except (TypeError, ValueError):
            pass
    try:
        client = _redis_client()
        client.setex(f"{_DENY_PREFIX}{jti}", ttl, "1")
        return
    except Exception as exc:
        logger.debug("refresh denylist redis unavailable: %s", exc)
        _LOCAL_DENY.add(jti)


def is_refresh_jti_denied(jti: str | None) -> bool:
    if not jti:
        return False
    if jti in _LOCAL_DENY:
        return True
    try:
        client = _redis_client()
        return bool(client.exists(f"{_DENY_PREFIX}{jti}"))
    except Exception:
        return False
