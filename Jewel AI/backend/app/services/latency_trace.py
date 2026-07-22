"""Temporary granular latency tracing for image generation (grep: LATENCY_TRACE).

Enable with LATENCY_TRACE=true. Does not change business logic — logs + metadata only.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from app.logging_config import get_logger

logger = get_logger(__name__)


def enabled() -> bool:
    try:
        from app.config import get_settings

        return bool(get_settings().latency_trace)
    except Exception:
        return False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(
    event: str,
    *,
    job_id: str | None = None,
    fal_request_id: str | None = None,
    **fields: Any,
) -> None:
    if not enabled():
        return
    payload: dict[str, Any] = {
        "latency_trace": True,
        "event": event,
        "ts": _now_iso(),
    }
    if job_id:
        payload["job_id"] = job_id
    if fal_request_id:
        payload["fal_request_id"] = fal_request_id
    payload.update(fields)
    logger.info("LATENCY_TRACE %s", event, extra={"extra_fields": payload})


def merge_job_trace(db, job_id: str, patch: dict[str, Any]) -> None:
    """Persist trace fields on job.provider_metadata.latencyTrace (best-effort)."""
    if not enabled() or not patch:
        return
    try:
        from app.models import GenerationJob

        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            return
        meta = dict(job.provider_metadata or {})
        trace = dict(meta.get("latencyTrace") or {})
        trace.update(patch)
        meta["latencyTrace"] = trace
        job.provider_metadata = meta
        db.commit()
    except Exception as exc:
        logger.debug("latency trace merge failed for %s: %s", job_id, exc)


class PhaseTimer:
    """Monotonic timer for a single worker/fal span."""

    __slots__ = ("_t0", "marks")

    def __init__(self) -> None:
        self._t0 = time.perf_counter()
        self.marks: dict[str, float] = {"start": self._t0}

    def mark(self, name: str) -> None:
        self.marks[name] = time.perf_counter()

    def ms(self, start: str, end: str) -> int:
        a = self.marks.get(start)
        b = self.marks.get(end)
        if a is None or b is None:
            return 0
        return max(0, int(round((b - a) * 1000)))

    def ms_since_start(self, end: str = "end") -> int:
        return self.ms("start", end)


def emit_summary(
    *,
    job_id: str,
    fal_request_id: str | None = None,
    t0_api_ms: int | None = None,
    celery_queue_ms: int | None = None,
    t1_prep_ms: int | None = None,
    t2_fal_api_ms: int | None = None,
    t2_fal_mode: str | None = None,
    t3_post_ms: int | None = None,
    fal_image_prep_ms: int | None = None,
    fal_build_args_ms: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit T0–T3 summary line for log grep / fal dashboard cross-reference."""
    if not enabled():
        return
    fields: dict[str, Any] = {
        "T0_api_ms": t0_api_ms,
        "celery_queue_ms": celery_queue_ms,
        "T1_prep_ms": t1_prep_ms,
        "T2_fal_api_ms": t2_fal_api_ms,
        "T2_fal_mode": t2_fal_mode,
        "T3_post_ms": t3_post_ms,
        "fal_image_prep_ms": fal_image_prep_ms,
        "fal_build_args_ms": fal_build_args_ms,
    }
    if extra:
        fields.update(extra)
    # Remove Nones for cleaner logs
    fields = {k: v for k, v in fields.items() if v is not None}
    log_event(
        "SUMMARY",
        job_id=job_id,
        fal_request_id=fal_request_id,
        **fields,
    )
