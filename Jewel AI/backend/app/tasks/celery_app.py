from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "jewel_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.generate",
        "app.tasks.billing",
    ],
)

# Force-import so worker process always registers finalize_fal_webhook + billing.
# (Variable-only redeploys have left workers on stale images missing these tasks.)
from app.tasks import billing as _billing_tasks  # noqa: E402,F401
from app.tasks import generate as _generate_tasks  # noqa: E402,F401

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=settings.celery_worker_concurrency,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    imports=("app.tasks.generate", "app.tasks.billing"),
    beat_schedule={
        "sweep-stuck-jobs": {
            "task": "app.tasks.generate.sweep_stuck_jobs",
            "schedule": crontab(minute="*/2"),
        },
        "refresh-fal-credits": {
            "task": "app.tasks.billing.refresh_fal_credits",
            "schedule": crontab(minute=f"*/{max(5, min(10, int(settings.fal_billing_refresh_minutes or 7)))}"),
        },
    },
)


def _init_sentry() -> None:
    dsn = (settings.sentry_dsn or "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=settings.node_env,
            release="jewel-ai-worker",
            traces_sample_rate=0.05 if settings.is_production else 0.0,
            integrations=[CeleryIntegration()],
        )
    except Exception:
        import logging

        logging.getLogger(__name__).exception("Sentry init failed (Celery)")


_init_sentry()

# Apply fal job rate limit from settings (token bucket across workers sharing Redis).
try:
    _rl = (settings.fal_celery_rate_limit or "10/s").strip() or "10/s"
    _generate_tasks.process_image_job.rate_limit = _rl
except Exception:
    pass
