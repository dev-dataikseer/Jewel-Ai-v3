

from app.logging_config import get_logger

logger = get_logger(__name__)

# Fallback defaults — settings values take precedence at runtime via the helpers below.

from app.tasks.job_runner import process_image_job
from app.tasks.webhook_finalize import finalize_fal_webhook
from app.tasks.job_sweep import sweep_stuck_jobs

# Ensure Celery finds these tasks under the original app.tasks.generate namespace.
__all__ = [
    'process_image_job',
    'finalize_fal_webhook',
    'sweep_stuck_jobs',
]
