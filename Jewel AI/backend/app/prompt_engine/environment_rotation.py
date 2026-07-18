"""Backend environment rotation for Modern Dynamic Catalog (no model-side random)."""

from __future__ import annotations

import logging
import random
from collections import defaultdict, deque
from typing import Deque

from app.config import get_settings
from app.prompt_engine.execution_mode import ENVIRONMENT_POOL

logger = logging.getLogger(__name__)

# In-process fallback when Redis is unavailable (dev / single-worker).
_memory_recent: dict[str, Deque[str]] = defaultdict(lambda: deque(maxlen=20))


def _lookback() -> int:
    try:
        return max(1, int(get_settings().env_rotation_lookback or 5))
    except Exception:
        return 5


def _redis_client():
    try:
        import redis

        client = redis.from_url(get_settings().redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
        client.ping()
        return client
    except Exception:
        return None


def _key(user_id: str) -> str:
    return f"jewel:env-rotate:{user_id or 'default'}"


def get_recent_environments(user_id: str, lookback: int | None = None) -> list[str]:
    n = lookback if lookback is not None else _lookback()
    client = _redis_client()
    if client is not None:
        try:
            items = client.lrange(_key(user_id), 0, n - 1)
            return [i.decode("utf-8") if isinstance(i, bytes) else str(i) for i in items]
        except Exception as exc:
            logger.debug("env rotation redis read failed: %s", exc)
    mem = _memory_recent[user_id or "default"]
    return list(mem)[:n]


def record_environment_used(user_id: str, job_id: str | None, choice: str) -> None:
    uid = user_id or "default"
    client = _redis_client()
    if client is not None:
        try:
            k = _key(uid)
            client.lpush(k, choice)
            client.ltrim(k, 0, max(19, _lookback() * 4 - 1))
            client.expire(k, 60 * 60 * 24 * 30)  # 30 days
            return
        except Exception as exc:
            logger.debug("env rotation redis write failed: %s", exc)
    _memory_recent[uid].appendleft(choice)


def choose_environment(user_id: str | None, job_id: str | None = None) -> str:
    """Pick a concrete environment sentence, avoiding recent choices for this user."""
    uid = user_id or "default"
    recent = get_recent_environments(uid)
    available = [e for e in ENVIRONMENT_POOL if e not in recent] or list(ENVIRONMENT_POOL)
    choice = random.choice(available)
    record_environment_used(uid, job_id, choice)
    return choice


def clear_memory_rotation_for_tests() -> None:
    """Test helper — reset in-process rotation state."""
    _memory_recent.clear()
