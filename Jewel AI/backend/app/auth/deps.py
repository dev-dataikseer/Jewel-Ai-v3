from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.auth.security import decode_token
from app.database import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)

# Only two effective levels: user (1) and admin (2).
# "operator" and "viewer" are intentional aliases for "user" — they exist
# so that future granular RBAC can be introduced without changing call sites.
ROLE_HIERARCHY = {"user": 1, "operator": 1, "viewer": 1, "admin": 2}


def _lookup_active_user(db: Session, user_id: str) -> User | None:
    user = db.query(User).filter(User.id == user_id).first()
    if user and not user.is_active:
        return None
    return user


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        return None
    return await run_in_threadpool(_lookup_active_user, db, payload["sub"])


async def require_user(user: Annotated[User | None, Depends(get_current_user)]) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def require_role(min_role: str) -> Callable:
    async def checker(user: Annotated[User, Depends(require_user)]) -> User:
        if ROLE_HIERARCHY.get(user.role, 0) < ROLE_HIERARCHY.get(min_role, 99):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker


RequireAdmin = Annotated[User, Depends(require_role("admin"))]
RequireUser = Annotated[User, Depends(require_user)]
# Explicit aliases — currently equivalent to RequireUser; named for future RBAC granularity.
RequireOperator = RequireUser
RequireViewer = RequireUser

