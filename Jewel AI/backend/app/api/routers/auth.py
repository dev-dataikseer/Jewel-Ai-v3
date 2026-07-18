from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.security import create_access_token, create_refresh_token, decode_token
from app.auth.token_denylist import deny_refresh_jti, is_refresh_jti_denied
from app.database import get_db
from app.models import User
from app.schemas.common import LoginRequest, RefreshRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    from app.auth.security import authenticate_user

    user = authenticate_user(db, body.email.strip(), body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    body: RefreshRequest,
    db: Session = Depends(get_db),
):
    token = body.refresh_token
    if not token:
        raise HTTPException(status_code=400, detail="refresh_token required")
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    jti = payload.get("jti")
    if is_refresh_jti_denied(jti):
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    # Rotate: deny old jti, issue new refresh
    deny_refresh_jti(jti, exp=payload.get("exp"))
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.post("/logout")
def logout(body: LogoutRequest | None = None, user: User | None = Depends(get_current_user)):
    """Revoke the presented refresh token (best-effort). Access token expires naturally."""
    token = (body.refresh_token if body else None) or None
    if token:
        payload = decode_token(token)
        if payload and payload.get("type") == "refresh":
            if user is None or payload.get("sub") == user.id:
                deny_refresh_jti(payload.get("jti"), exp=payload.get("exp"))
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
