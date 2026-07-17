"""Background refresh of fal.ai billing credits."""

from __future__ import annotations

from app.database import SessionLocal
from app.logging_config import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.tasks.billing.refresh_fal_credits")
def refresh_fal_credits() -> dict:
    """Periodic/manual Celery task — never blocks image generation."""
    db = SessionLocal()
    try:
        from app.providers.fal_billing.client import FalBillingError
        from app.providers.fal_billing.service import refresh_credits_cache

        snap = refresh_credits_cache(db)
        logger.info(
            "fal credits refreshed",
            extra={
                "extra_fields": {
                    "balance": snap.get("current_balance"),
                    "currency": snap.get("currency"),
                }
            },
        )
        return {
            "ok": True,
            "current_balance": snap.get("current_balance"),
            "currency": snap.get("currency"),
            "updated_at": snap.get("updated_at"),
        }
    except FalBillingError as exc:
        logger.warning("fal credits refresh failed: %s", exc)
        return {"ok": False, "error": str(exc), "error_type": exc.error_type}
    except Exception as exc:
        logger.warning("fal credits refresh unexpected error: %s", exc)
        return {"ok": False, "error": str(exc)}
    finally:
        db.close()
