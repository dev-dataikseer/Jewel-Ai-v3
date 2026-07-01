"""Rate limiting middleware for job creation and uploads."""
import time
from collections import defaultdict

from fastapi import HTTPException, Request
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

_buckets: dict[str, list[float]] = defaultdict(list)
LIMIT = 30
WINDOW = 60
settings = get_settings()


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


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and (
            request.url.path.endswith("/jobs") or "/assets/upload" in request.url.path
        ):
            key = _rate_limit_key(request)
            now = time.time()
            _buckets[key] = [t for t in _buckets[key] if now - t < WINDOW]
            if len(_buckets[key]) >= LIMIT:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            _buckets[key].append(now)
        return await call_next(request)
