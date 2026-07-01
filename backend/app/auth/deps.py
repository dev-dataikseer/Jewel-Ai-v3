from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.database import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)

ROLE_HIERARCHY = {"user": 1, "admin": 2, "operator": 1, "viewer": 1}


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        return None
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if user and not user.is_active:
        return None
    return user


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
RequireOperator = Annotated[User, Depends(require_role("user"))]
RequireViewer = Annotated[User, Depends(require_role("user"))]
