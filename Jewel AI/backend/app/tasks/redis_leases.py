from app.logging_config import get_logger
from app.redis_client import get_redis_client

logger = get_logger(__name__)


def _acquire_requeue_lease(job_id: str, *, ttl_seconds: int = 120) -> bool:
    """Return True if this process won the requeue lease for job_id."""
    try:
        client = get_redis_client()
        if not client:
            return True
        key = f"jewel:requeue-lease:{job_id}"
        return bool(client.set(key, "1", nx=True, ex=ttl_seconds))
    except Exception as exc:
        logger.warning(f"Redis lease error for {job_id}: {exc}")
        # Without Redis, fall back to allowing one requeue (dev).
        return True


def _acquire_webhook_finalize_lease(job_id: str, *, ttl_seconds: int = 300) -> bool:
    """Return True if this process won the webhook finalize lease (prevents double download)."""
    try:
        client = get_redis_client()
        if not client:
            return True
        key = f"jewel:webhook-finalize:{job_id}"
        return bool(client.set(key, "1", nx=True, ex=ttl_seconds))
    except Exception as exc:
        logger.warning(f"Redis webhook lease error for {job_id}: {exc}")
        # Without Redis, allow finalize once (dev); races possible but rare locally.
        return True


def _release_webhook_finalize_lease(job_id: str) -> None:
    try:
        client = get_redis_client()
        if client:
            client.delete(f"jewel:webhook-finalize:{job_id}")
    except Exception as exc:
        logger.warning(f"Redis webhook release error for {job_id}: {exc}")
