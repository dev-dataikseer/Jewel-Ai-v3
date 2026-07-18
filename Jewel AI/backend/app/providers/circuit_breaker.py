import time
from typing import Dict

import redis

from app.config import get_settings

settings = get_settings()
FAILURE_THRESHOLD = 5
RESET_WINDOW_SECONDS = 300

_memory_state: Dict[str, dict] = {}
_redis_client: redis.Redis | None = None


def init_circuit_breaker() -> None:
    global _redis_client
    try:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        _redis_client.ping()
    except Exception:
        _redis_client = None


def _key(provider: str) -> str:
    return f"circuit:{provider}"


def is_circuit_open(provider: str) -> bool:
    if _redis_client:
        failures = int(_redis_client.get(_key(provider)) or 0)
        return failures >= FAILURE_THRESHOLD
    state = _memory_state.get(provider, {"failures": 0, "opened_at": 0})
    if state["failures"] >= FAILURE_THRESHOLD:
        if time.time() - state["opened_at"] < RESET_WINDOW_SECONDS:
            return True
        state["failures"] = 0
    return False


def record_success(provider: str) -> None:
    if _redis_client:
        _redis_client.delete(_key(provider))
        return
    _memory_state[provider] = {"failures": 0, "opened_at": 0}


def record_failure(provider: str) -> None:
    if _redis_client:
        k = _key(provider)
        failures = _redis_client.incr(k)
        if failures == 1:
            _redis_client.expire(k, RESET_WINDOW_SECONDS)
        return
    state = _memory_state.setdefault(provider, {"failures": 0, "opened_at": 0})
    state["failures"] += 1
    if state["failures"] >= FAILURE_THRESHOLD:
        state["opened_at"] = time.time()
