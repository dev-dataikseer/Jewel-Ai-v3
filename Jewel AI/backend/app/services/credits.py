"""Atomic user credit debit for job creation."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import CreditLedger, User


def debit_credits(
    db: Session,
    user_id: str,
    amount: int,
    *,
    job_id: str | None = None,
    description: str = "job_create",
) -> None:
    """Debit credits with row lock. No-op when ENFORCE_USER_CREDITS is false."""
    if amount <= 0:
        return
    settings = get_settings()
    if not settings.enforce_user_credits:
        return

    user = db.query(User).filter(User.id == user_id).with_for_update().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if (user.credits or 0) < amount:
        raise HTTPException(status_code=402, detail="Insufficient credits")
    user.credits = int(user.credits) - amount
    db.add(
        CreditLedger(
            user_id=user_id,
            amount=-amount,
            type="debit",
            description=description,
            job_id=job_id,
        )
    )


def credit_top_up(
    db: Session,
    user_id: str,
    amount: int,
    *,
    description: str = "admin_top_up",
) -> User:
    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be positive")
    user = db.query(User).filter(User.id == user_id).with_for_update().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.credits = int(user.credits or 0) + amount
    db.add(
        CreditLedger(
            user_id=user_id,
            amount=amount,
            type="credit",
            description=description,
            job_id=None,
        )
    )
    return user
