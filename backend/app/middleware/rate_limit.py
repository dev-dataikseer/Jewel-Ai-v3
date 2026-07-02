"""Rate limiting middleware for job creation, uploads, and webhooks."""
import time
from collections import defaultdict

from fastapi import HTTPException, Request
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

_buckets: dict[str, list[float]] = defaultdict(list)
LIMIT = 30
WINDOW = 60
WEBHOOK_LIMIT = 60
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


def _redis_allow(key: str, limit: int, window: int) -> bool:
    client = _get_redis()
    if not client:
        return True
    now = int(time.time())
    bucket = f"rl:{key}:{now // window}"
    try:
        count = client.incr(bucket)
        if count == 1:
            client.expire(bucket, window + 1)
        return count <= limit
    except Exception:
        return True


def _memory_allow(key: str, limit: int, window: int) -> bool:
    now = time.time()
    _buckets[key] = [t for t in _buckets[key] if now - t < window]
    if len(_buckets[key]) >= limit:
        return False
    _buckets[key].append(now)
    return True


def _allow(key: str, limit: int, window: int = WINDOW) -> bool:
    if _get_redis():
        return _redis_allow(key, limit, window)
    return _memory_allow(key, limit, window)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "POST":
            if path.endswith("/jobs") or "/assets/upload" in path:
                key = f"{_rate_limit_key(request)}:jobs"
                if not _allow(key, LIMIT):
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
            elif "/providers/fal/webhook/" in path:
                key = f"webhook:{request.client.host if request.client else 'unknown'}"
                if not _allow(key, WEBHOOK_LIMIT):
                    raise HTTPException(status_code=429, detail="Webhook rate limit exceeded")
        return await call_next(request)
