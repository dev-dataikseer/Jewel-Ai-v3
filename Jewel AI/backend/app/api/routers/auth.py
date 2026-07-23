from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import RequireAdmin, get_current_user
from app.auth.security import create_access_token, create_refresh_token, decode_token
from app.auth.token_denylist import deny_refresh_jti, is_refresh_jti_denied
from app.config import get_settings
from app.database import get_db
from app.models import AuditLog, User
from app.schemas.common import LoginRequest, TokenResponse, UserOut
from app.services.audit import write_audit
from app.services.mfa import (
    admin_requires_mfa,
    clear_pending_totp_secret,
    clear_user_totp,
    consume_backup_code,
    generate_backup_codes,
    generate_totp_secret,
    get_pending_totp_secret,
    get_user_totp_secret,
    set_user_totp,
    store_pending_totp_secret,
    totp_provisioning_uri,
    verify_totp,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class MfaVerifyLogin(BaseModel):
    email: str
    password: str
    otp: str | None = None
    backup_code: str | None = None


class MfaEnrollIn(BaseModel):
    current_otp: str | None = None


class MfaEnrollOut(BaseModel):
    secret: str
    otpauth_url: str
    backup_codes: list[str]


class MfaDisableIn(BaseModel):
    otp: str | None = None
    backup_code: str | None = None


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/api/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path="/api/auth",
        secure=settings.is_production,
        samesite="strict",
    )


def _set_csrf_cookie(response: Response, csrf: str) -> None:
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf,
        httponly=False,
        secure=settings.is_production,
        samesite="strict",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/",
    )


def _clear_csrf_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        path="/",
        secure=settings.is_production,
        samesite="strict",
    )


def _require_csrf(request: Request) -> None:
    cookie = request.cookies.get(settings.csrf_cookie_name)
    header = request.headers.get("X-CSRF-Token")
    if not cookie or not header or cookie != header:
        raise HTTPException(status_code=403, detail="CSRF validation failed")


def _issue_tokens(response: Response, user: User) -> TokenResponse:
    import secrets

    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id)
    csrf = secrets.token_urlsafe(32)
    _set_refresh_cookie(response, refresh)
    _set_csrf_cookie(response, csrf)
    # Refresh is cookie-only; body field kept empty for schema compatibility.
    return TokenResponse(
        access_token=access,
        refresh_token="",
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    from app.auth.security import authenticate_user

    user = authenticate_user(db, body.email.strip(), body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    otp = getattr(body, "otp", None)
    backup = getattr(body, "backup_code", None)

    if admin_requires_mfa(user):
        secret = get_user_totp_secret(user)
        ok = False
        if otp and secret and verify_totp(secret, otp):
            ok = True
        elif backup and consume_backup_code(db, user, backup):
            db.commit()
            ok = True
        if not ok:
            raise HTTPException(status_code=401, detail="MFA required", headers={"X-MFA-Required": "1"})

    # MFA is optional for admins until they enroll; login requires OTP only when totp_enabled.
    return _issue_tokens(response, user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    _require_csrf(request)
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token and not settings.is_production:
        # Body refresh allowed in non-production for tests / local clients.
        try:
            data = await request.json()
            token = (data or {}).get("refresh_token")
        except Exception:
            token = None
    if not token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    jti = payload.get("jti")
    if is_refresh_jti_denied(jti):
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    deny_refresh_jti(jti, exp=payload.get("exp"))
    return _issue_tokens(response, user)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    body: LogoutRequest | None = None,
    user: User | None = Depends(get_current_user),
):
    cookie_token = request.cookies.get(settings.refresh_cookie_name)
    if cookie_token:
        _require_csrf(request)
    token = cookie_token or (body.refresh_token if body else None)
    if token:
        payload = decode_token(token)
        if payload and payload.get("type") == "refresh":
            if user is None or payload.get("sub") == user.id:
                deny_refresh_jti(payload.get("jti"), exp=payload.get("exp"))
    _clear_refresh_cookie(response)
    _clear_csrf_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.post("/mfa/enroll", response_model=MfaEnrollOut)
def mfa_enroll(
    user: RequireAdmin,
    db: Session = Depends(get_db),
    body: MfaEnrollIn = Body(default_factory=MfaEnrollIn),
):
    secret = generate_totp_secret()
    codes = generate_backup_codes()

    if getattr(user, "totp_enabled", False):
        current = get_user_totp_secret(user)
        if not body.current_otp or not current or not verify_totp(current, body.current_otp):
            raise HTTPException(status_code=400, detail="current_otp required to re-enroll MFA")
        try:
            store_pending_totp_secret(user.id, secret)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        # Keep existing encrypted_totp_secret / totp_enabled / backups until confirm.
        return MfaEnrollOut(
            secret=secret,
            otpauth_url=totp_provisioning_uri(secret, user.email),
            backup_codes=codes,
        )

    # First-time enroll: store pending encrypted secret; leave backups alone if already empty.
    from app.auth.security import encrypt_secret

    user.encrypted_totp_secret = encrypt_secret(secret)
    user.totp_enabled = False
    db.add(user)
    db.commit()
    return MfaEnrollOut(
        secret=secret,
        otpauth_url=totp_provisioning_uri(secret, user.email),
        backup_codes=codes,
    )


class MfaConfirm(BaseModel):
    otp: str
    backup_codes: list[str] = Field(default_factory=list)


@router.post("/mfa/confirm")
def mfa_confirm(body: MfaConfirm, user: RequireAdmin, db: Session = Depends(get_db), request: Request = None):
    pending = get_pending_totp_secret(user.id)
    secret = pending or get_user_totp_secret(user)
    if not secret or not verify_totp(secret, body.otp):
        raise HTTPException(status_code=400, detail="Invalid OTP")
    codes = body.backup_codes or generate_backup_codes()
    set_user_totp(db, user, secret, codes)
    clear_pending_totp_secret(user.id)
    write_audit(
        db,
        actor_user_id=user.id,
        action="mfa.enable",
        entity_type="user",
        entity_id=user.id,
        request_id=getattr(getattr(request, "state", None), "request_id", None) if request else None,
    )
    db.commit()
    return {"ok": True, "backup_codes": codes}


@router.post("/mfa/disable")
def mfa_disable(
    body: MfaDisableIn,
    user: RequireAdmin,
    db: Session = Depends(get_db),
    request: Request = None,
):
    secret = get_user_totp_secret(user)
    ok = False
    if body.otp and secret and verify_totp(secret, body.otp):
        ok = True
    elif body.backup_code and consume_backup_code(db, user, body.backup_code):
        ok = True
    if not ok:
        raise HTTPException(status_code=400, detail="OTP or backup code required to disable MFA")
    clear_user_totp(db, user)
    clear_pending_totp_secret(user.id)
    write_audit(
        db,
        actor_user_id=user.id,
        action="mfa.disable",
        entity_type="user",
        entity_id=user.id,
        request_id=getattr(getattr(request, "state", None), "request_id", None) if request else None,
    )
    db.commit()
    return {"ok": True}


@router.get("/admin/audit")
def list_audit(
    user: RequireAdmin,
    db: Session = Depends(get_db),
    limit: int = 50,
    cursor: str | None = None,
):
    q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    if cursor:
        q = q.filter(AuditLog.created_at < cursor)
    rows = q.limit(min(limit, 100)).all()
    return [
        {
            "id": r.id,
            "actor_user_id": r.actor_user_id,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "before": r.before,
            "after": r.after,
            "request_id": r.request_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
