"""Admin TOTP MFA helpers."""

from __future__ import annotations

import hashlib
import secrets
from typing import Iterable

import pyotp
from sqlalchemy.orm import Session

from app.auth.security import decrypt_secret, encrypt_secret
from app.models import User


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
