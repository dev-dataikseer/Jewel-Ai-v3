"""Cached fal.ai billing / credits endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import RequireAdmin, RequireUser
from app.database import get_db
from app.providers.fal_billing.service import get_credits_view

router = APIRouter(prefix="/billing", tags=["billing"])


class FalCreditsOut(BaseModel):
    available: bool
    current_balance: float | None = None
    currency: str = "USD"
    username: str | None = None
    updated_at: str | None = None
    low_balance: bool = False
    low_threshold: float = 5.0
    stale: bool = False
    error: str | None = None
    error_type: str | None = None


@router.get("/fal-credits", response_model=FalCreditsOut)
def get_fal_credits(user: RequireUser, db: Session = Depends(get_db)):
    """Return cached fal.ai credit balance (instant). Does not call fal on every request."""
    return FalCreditsOut(**get_credits_view(db, refresh=False))


@router.post("/fal-credits/refresh", response_model=FalCreditsOut)
def refresh_fal_credits(user: RequireAdmin, db: Session = Depends(get_db)):
    """Manual refresh — admin only (hits fal.ai Platform Billing API)."""
    # Pick up FAL_ADMIN_KEY added to .env after process start
    from app.config import get_settings

    get_settings.cache_clear()
    return FalCreditsOut(**get_credits_view(db, refresh=True))
