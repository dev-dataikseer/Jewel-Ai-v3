import base64
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User

settings = get_settings()


def _fernet() -> Fernet:
    key = settings.fernet_key
    if not key:
        # Stable dev key derived from JWT secret so encrypted provider keys survive restarts
        import base64
        import hashlib

        digest = hashlib.sha256(settings.jwt_secret.encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def encrypt_secret(value: str) -> bytes:
    return _fernet().encrypt(value.encode())


def decrypt_secret(data: bytes) -> str:
    try:
        return _fernet().decrypt(data).decode()
    except InvalidToken:
        return ""


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": user_id, "role": role, "type": "access", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": user_id, "type": "refresh", "exp": expire, "jti": secrets.token_hex(16)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def create_job_stream_token(user_id: str, job_ids: list[str]) -> str:
    """Short-lived token for EventSource job streaming (cannot send Bearer header)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    payload = {
        "sub": user_id,
        "type": "job_stream",
        "job_ids": job_ids,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_job_stream_token(token: str) -> Optional[dict]:
    payload = decode_token(token)
    if not payload or payload.get("type") != "job_stream":
        return None
    return payload


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    email = email.strip()
    user = db.query(User).filter(User.email == email).first()
    if not user and "@" in email:
        # Legacy rows may have trailing spaces in stored email
        user = db.query(User).filter(User.email == email + " ").first()
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def constant_time_compare(a: str, b: str) -> bool:
    return secrets.compare_digest(a.encode(), b.encode())
