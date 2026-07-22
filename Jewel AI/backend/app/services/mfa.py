"""Admin TOTP MFA helpers."""

from __future__ import annotations

import hashlib
import logging
import secrets
from typing import Iterable

import pyotp
from sqlalchemy.orm import Session

from app.auth.security import decrypt_secret, encrypt_secret
from app.config import get_settings
from app.models import User

logger = logging.getLogger(__name__)

_MFA_PENDING_PREFIX = "jewel:mfa-pending:"
_MFA_PENDING_TTL_SECONDS = 15 * 60


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def totp_provisioning_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="Jewel AI")


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)


def hash_backup_code(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode()).hexdigest()


def generate_backup_codes(n: int = 8) -> list[str]:
    return [secrets.token_hex(4).upper() for _ in range(n)]


def set_user_totp(db: Session, user: User, secret: str, backup_codes: Iterable[str]) -> None:
    user.encrypted_totp_secret = encrypt_secret(secret)
    user.totp_enabled = True
    user.totp_backup_hashes = [hash_backup_code(c) for c in backup_codes]
    db.add(user)


def clear_user_totp(db: Session, user: User) -> None:
    user.encrypted_totp_secret = None
    user.totp_enabled = False
    user.totp_backup_hashes = None
    db.add(user)


def get_user_totp_secret(user: User) -> str | None:
    raw = getattr(user, "encrypted_totp_secret", None)
    if not raw:
        return None
    return decrypt_secret(raw) or None


def consume_backup_code(db: Session, user: User, code: str) -> bool:
    hashes = list(user.totp_backup_hashes or [])
    target = hash_backup_code(code)
    if target not in hashes:
        return False
    hashes.remove(target)
    user.totp_backup_hashes = hashes
    db.add(user)
    return True


def admin_requires_mfa(user: User) -> bool:
    return (user.role or "").lower() == "admin" and bool(getattr(user, "totp_enabled", False))


def _redis_client():
    import redis

    return redis.from_url(get_settings().redis_url, socket_connect_timeout=1)


def store_pending_totp_secret(user_id: str, secret: str) -> None:
    """Store a re-enroll pending TOTP secret in Redis (TTL 15 minutes)."""
    try:
        client = _redis_client()
        client.setex(f"{_MFA_PENDING_PREFIX}{user_id}", _MFA_PENDING_TTL_SECONDS, secret)
    except Exception as exc:
        logger.debug("mfa pending redis unavailable: %s", exc)
        raise RuntimeError("MFA enroll requires Redis") from exc


def get_pending_totp_secret(user_id: str) -> str | None:
    try:
        client = _redis_client()
        raw = client.get(f"{_MFA_PENDING_PREFIX}{user_id}")
        if raw is None:
            return None
        if isinstance(raw, bytes):
            return raw.decode()
        return str(raw)
    except Exception as exc:
        logger.debug("mfa pending redis read failed: %s", exc)
        return None


def clear_pending_totp_secret(user_id: str) -> None:
    try:
        client = _redis_client()
        client.delete(f"{_MFA_PENDING_PREFIX}{user_id}")
    except Exception as exc:
        logger.debug("mfa pending redis delete failed: %s", exc)
