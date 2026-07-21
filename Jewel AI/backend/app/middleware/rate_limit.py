"""Rate limiting middleware for auth, jobs, uploads, and webhooks."""
import time
from collections import defaultdict

from fastapi import HTTPException, Request
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

_buckets: dict[str, list[float]] = defaultdict(list)
LIMIT = 30
WINDOW = 60
AUTH_LIMIT = 10
AUTH_WINDOW = 60
WEBHOOK_LIMIT = 60
BULK_LIMIT = 10
settings = get_settings()
_redis_client = None
_redis_checked = False


def _get_redis():
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    try:
        import redis

        client = redis.from_url(settings.redis_url, socket_connect_timeout=1)
        client.ping()
        _redis_client = client
    except Exception:
        _redis_client = None
    return _redis_client


def _rate_limit_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except JWTError:
            pass
    return f"ip:{request.client.host if request.client else 'unknown'}"


def _memory_allow(key: str, limit: int, window: int) -> bool:
    now = time.time()
    _buckets[key] = [t for t in _buckets[key] if now - t < window]
    if len(_buckets[key]) >= limit:
        return False
    _buckets[key].append(now)
    return True


def _allow(key: str, limit: int, window: int = WINDOW, *, fail_closed: bool = False) -> bool:
    """Prefer Redis; on Redis unavailable/error use in-process limiter (never fail-open).

    When fail_closed=True (prod auth), Redis must be reachable — otherwise deny.
    """
    client = _get_redis()
    if client:
        now = int(time.time())
        bucket = f"rl:{key}:{now // window}"
        try:
            count = client.incr(bucket)
            if count == 1:
                client.expire(bucket, window + 1)
            return count <= limit
        except Exception:
            if fail_closed:
                return False
    elif fail_closed:
        return False
    return _memory_allow(key, limit, window)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        # Prod: Redis is a hard dependency for all rate buckets (incl. auth).
        # Redis blip → 429 rather than per-instance memory bypass.
        prod_fail_closed = bool(settings.is_production)
        if method == "POST":
            if path.endswith("/auth/login") or path.endswith("/auth/refresh"):
                key = f"{_rate_limit_key(request)}:auth"
                if not _allow(key, AUTH_LIMIT, AUTH_WINDOW, fail_closed=prod_fail_closed):
                    raise HTTPException(status_code=429, detail="Too many auth attempts")
            elif path.endswith("/jobs/bulk") or path.endswith("/assets/bulk-upload"):
                key = f"{_rate_limit_key(request)}:bulk"
                if not _allow(key, BULK_LIMIT, fail_closed=prod_fail_closed):
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
            elif path.endswith("/jobs") or "/assets/upload" in path:
                key = f"{_rate_limit_key(request)}:jobs"
                if not _allow(key, LIMIT, fail_closed=prod_fail_closed):
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
            elif "/providers/fal/webhook/" in path:
                key = f"webhook:{request.client.host if request.client else 'unknown'}"
                if not _allow(key, WEBHOOK_LIMIT, fail_closed=prod_fail_closed):
                    raise HTTPException(status_code=429, detail="Webhook rate limit exceeded")
        return await call_next(request)
