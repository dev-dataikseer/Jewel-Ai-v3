"""Fal billing service — fetch/cache credits independently of generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.logging_config import get_logger
from app.providers.fal_billing.cache import get_cached_billing, set_cached_billing
from app.providers.fal_billing.client import FalBillingError, fetch_account_billing

logger = get_logger(__name__)


def resolve_fal_api_key(db: Session | None = None) -> str | None:
    """Prefer Admin-configured FAL provider key, then env FAL_KEY."""
    settings = get_settings()
    if db is not None:
        try:
            from app.models import Provider
            from app.providers.registry import _resolve_api_key

            provider = (
                db.query(Provider)
                .filter(Provider.name == "FAL", Provider.is_active == True)  # noqa: E712
                .order_by(Provider.priority.asc())
                .first()
            )
            if provider:
                key = _resolve_api_key(provider)
                if key:
                    return key
        except Exception as exc:
            logger.debug("Could not resolve FAL key from DB: %s", exc)
    return settings.fal_key or None


def resolve_fal_billing_key(db: Session | None = None) -> str | None:
    """
    Platform Billing APIs require an Admin-scoped fal key.

    Priority:
    1. Provider.encrypted_admin_api_key (Admin UI)
    2. FAL_ADMIN_KEY env / .env (re-read on each call so .env edits apply after restart
       and after settings cache clear)
    3. Generation key fallback (only works if that key already has Admin scope)
    """
    import os

    if db is not None:
        try:
            from app.models import Provider
            from app.auth.security import decrypt_secret

            provider = (
                db.query(Provider)
                .filter(Provider.name == "FAL")
                .order_by(Provider.priority.asc())
                .first()
            )
            if provider and getattr(provider, "encrypted_admin_api_key", None):
                key = decrypt_secret(provider.encrypted_admin_api_key)
                if key:
                    return key
        except Exception as exc:
            logger.debug("Could not resolve FAL admin key from DB: %s", exc)

    # Live process env first, then settings (.env). Clear settings cache if env was added later.
    admin = (os.environ.get("FAL_ADMIN_KEY") or "").strip()
    if not admin:
        from app.config import get_settings

        admin = (get_settings().fal_admin_key or "").strip()
    if admin:
        return admin
    return resolve_fal_api_key(db)


def get_credits_view(db: Session | None = None, *, refresh: bool = False) -> dict[str, Any]:
    """
    Return cached credits for the UI.

    Never raises for transient fal failures — returns last cache or Unavailable.
    """
    import os

    from app.config import get_settings

    settings = get_settings()
    threshold = float(settings.fal_credits_low_threshold or 5.0)
    cached = get_cached_billing()

    if refresh or cached is None:
        # Pick up FAL_ADMIN_KEY added to .env after the API process started
        if not (os.environ.get("FAL_ADMIN_KEY") or "").strip() and not (settings.fal_admin_key or "").strip():
            get_settings.cache_clear()
        try:
            cached = refresh_credits_cache(db)
        except FalBillingError as exc:
            logger.warning("fal billing refresh failed: %s", exc)
            if cached is None:
                return {
                    "available": False,
                    "current_balance": None,
                    "currency": "USD",
                    "username": None,
                    "updated_at": None,
                    "low_balance": False,
                    "low_threshold": threshold,
                    "stale": False,
                    "error": str(exc),
                    "error_type": exc.error_type,
                }
            # Keep serving last good cache
            return _view_from_cache(cached, threshold, stale=True, error=str(exc), error_type=exc.error_type)
        except Exception as exc:
            logger.warning("fal billing unexpected error: %s", exc)
            if cached is None:
                return {
                    "available": False,
                    "current_balance": None,
                    "currency": "USD",
                    "username": None,
                    "updated_at": None,
                    "low_balance": False,
                    "low_threshold": threshold,
                    "stale": False,
                    "error": "Unavailable",
                    "error_type": "server_error",
                }
            return _view_from_cache(cached, threshold, stale=True, error="Unavailable", error_type="server_error")

    return _view_from_cache(cached, threshold, stale=False)


def refresh_credits_cache(db: Session | None = None) -> dict[str, Any]:
    """Force a live fal.ai billing fetch and update cache. Raises FalBillingError on failure."""
    api_key = resolve_fal_billing_key(db)
    if not api_key:
        raise FalBillingError(
            "FAL billing key not configured — set FAL_ADMIN_KEY (Admin scope) in env",
            error_type="authorization_error",
        )
    try:
        snapshot = fetch_account_billing(api_key)
    except FalBillingError as exc:
        if exc.status_code == 403:
            raise FalBillingError(
                "fal.ai billing requires an Admin-scoped API key — set FAL_ADMIN_KEY "
                "(dashboard → Keys → Admin scope). API-scope keys return 403.",
                status_code=403,
                error_type="authorization_error",
            ) from exc
        raise
    payload = {
        "available": True,
        "username": snapshot.username,
        "current_balance": snapshot.current_balance,
        "currency": snapshot.currency,
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "source": "fal.ai",
    }
    return set_cached_billing(payload)


def _view_from_cache(
    cached: dict[str, Any],
    threshold: float,
    *,
    stale: bool,
    error: str | None = None,
    error_type: str | None = None,
) -> dict[str, Any]:
    balance = cached.get("current_balance")
    try:
        balance_f = float(balance) if balance is not None else None
    except (TypeError, ValueError):
        balance_f = None
    currency = str(cached.get("currency") or "USD")
    return {
        "available": balance_f is not None,
        "current_balance": balance_f,
        "currency": currency,
        "username": cached.get("username"),
        "updated_at": cached.get("updated_at") or cached.get("cached_at"),
        "low_balance": balance_f is not None and balance_f < threshold,
        "low_threshold": threshold,
        "stale": stale,
        "error": error,
        "error_type": error_type,
    }
