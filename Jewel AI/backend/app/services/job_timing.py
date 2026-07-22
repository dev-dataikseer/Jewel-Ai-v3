"""Job timing samples + ETA estimates for UI transparency."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models import GenerationJob

_MEMORY_AVG: dict[str, list[float]] = {}
_MAX_SAMPLES = 40
_redis_client = None


def _endpoint_key(job: GenerationJob) -> str:
    meta = job.provider_metadata or {}
    return str(
        meta.get("modelEndpointId")
        or meta.get("modelName")
        or job.provider_model
        or job.workflow
        or "default"
    )


def _get_redis():
    """Reuse a single Redis client for ETA sample reads/writes."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        from app.config import get_settings

        _redis_client = redis.from_url(
            get_settings().redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
        )
        return _redis_client
    except Exception:
        return None


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _ms_between(start: Any, end: Any) -> int | None:
    t0 = _parse_iso(start)
    t1 = _parse_iso(end)
    if not t0 or not t1:
        return None
    return max(0, int((t1 - t0).total_seconds() * 1000))


def extract_fal_inference_seconds(data: Any) -> float | None:
    """Defensively extract GPU inference_time (seconds) from fal payload shapes."""
    if not isinstance(data, dict):
        return None

    candidate_paths = [
        ("metrics", "inference_time"),
        ("payload", "metrics", "inference_time"),
        ("data", "metrics", "inference_time"),
        ("inference_time",),
        ("payload", "inference_time"),
    ]

    for path in candidate_paths:
        current: Any = data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                current = None
                break
        if current is None:
            continue
        try:
            val = float(current)
            if val > 0:
                return val
        except (ValueError, TypeError):
            continue
    return None


def compute_duration_splits(meta: dict[str, Any] | None) -> dict[str, int | None]:
    """Derive prep / fal / finalize ms from timing + fal_inference_time.

    Webhook path: fal_queued → fal_webhook_received (+ inference from metrics).
    Subscribe path: fal_submit → fal_result_received (wall = queue+GPU); finalize after.
    """
    meta = meta or {}
    timing = dict(meta.get("timing") or {})

    worker_started = (
        timing.get("worker_started")
        or timing.get("processing_started")
        or timing.get("started")
        or timing.get("queued")
    )
    prompt_ready = timing.get("prompt_ready")
    fal_queued = timing.get("fal_queued") or timing.get("fal_submit")
    fal_webhook_received = timing.get("fal_webhook_received")
    fal_result_received = timing.get("fal_result_received")
    storage_saved = timing.get("storage_saved")
    completed = timing.get("completed") or storage_saved

    prep_ms = _ms_between(worker_started, prompt_ready)
    worker_total_ms = _ms_between(worker_started, completed)

    fal_inference_ms: int | None = None
    raw_inf = meta.get("fal_inference_time")
    if raw_inf is not None:
        try:
            sec = float(raw_inf)
            if sec > 0:
                fal_inference_ms = int(round(sec * 1000))
        except (ValueError, TypeError):
            pass

    # Prefer latencyTrace.T2_fal_api_ms (subscribe wall clock) when present
    lt = meta.get("latencyTrace") or {}
    t2_ms = lt.get("T2_fal_api_ms")
    if isinstance(t2_ms, (int, float)) and t2_ms > 0 and fal_inference_ms is None:
        # Not pure GPU — wall including queue; still useful as fal_wall proxy
        pass

    finalize_end = storage_saved or completed
    finalize_ms: int | None = None
    fal_queue_wait_ms: int | None = None
    fal_wall_ms: int | None = None

    if fal_webhook_received:
        finalize_ms = _ms_between(fal_webhook_received, finalize_end)
        span = _ms_between(fal_queued, fal_webhook_received)
        fal_wall_ms = span
        if span is not None:
            if fal_inference_ms is not None:
                fal_queue_wait_ms = max(0, span - fal_inference_ms)
            else:
                fal_queue_wait_ms = span
    elif fal_result_received:
        # Subscribe / in-process path
        finalize_ms = _ms_between(fal_result_received, finalize_end)
        fal_wall_ms = _ms_between(fal_queued, fal_result_received)
        if isinstance(t2_ms, (int, float)) and t2_ms > 0:
            fal_wall_ms = int(t2_ms)
        if fal_wall_ms is not None and fal_inference_ms is not None:
            fal_queue_wait_ms = max(0, fal_wall_ms - fal_inference_ms)
        elif fal_wall_ms is not None:
            # Without GPU metric, entire subscribe wall is "fal wait" (queue+GPU)
            fal_queue_wait_ms = fal_wall_ms
    else:
        # Legacy subscribe jobs: no fal_result_received — attribute
        # fal_submit → storage_saved as fal wall (blended with finalize).
        fal_wall_ms = _ms_between(fal_queued, finalize_end)
        if fal_wall_ms is not None and fal_inference_ms is None:
            fal_queue_wait_ms = fal_wall_ms

    return {
        "prep_ms": prep_ms,
        "fal_inference_ms": fal_inference_ms,
        "fal_queue_wait_ms": fal_queue_wait_ms,
        "fal_wall_ms": fal_wall_ms,
        "finalize_ms": finalize_ms,
        "worker_total_ms": worker_total_ms,
    }


def attach_duration_splits(meta: dict[str, Any]) -> dict[str, Any]:
    out = dict(meta or {})
    splits = compute_duration_splits(out)
    if any(v is not None for v in splits.values()):
        out["durationSplits"] = splits
    return out


def eta_sample_seconds(meta: dict[str, Any] | None) -> float | None:
    """Prefer pure GPU time for ETA samples; avoid R2/finalize poisoning."""
    meta = meta or {}
    raw = meta.get("fal_inference_time")
    if raw is not None:
        try:
            val = float(raw)
            if 0 < val <= 3600:
                return val
        except (ValueError, TypeError):
            pass

    splits = compute_duration_splits(meta)
    if splits.get("fal_inference_ms"):
        return splits["fal_inference_ms"] / 1000.0

    worker = splits.get("worker_total_ms")
    finalize = splits.get("finalize_ms")
    if worker is not None and finalize is not None:
        cleaned = (worker - finalize) / 1000.0
        if 0 < cleaned <= 3600:
            return cleaned

    return duration_from_timing(meta)


def record_duration_sample(job: GenerationJob, duration_seconds: float) -> None:
    if duration_seconds <= 0 or duration_seconds > 3600:
        return
    key = _endpoint_key(job)
    samples = _MEMORY_AVG.setdefault(key, [])
    samples.append(float(duration_seconds))
    if len(samples) > _MAX_SAMPLES:
        del samples[: len(samples) - _MAX_SAMPLES]

    client = _get_redis()
    if client is None:
        return
    try:
        rkey = f"jewel:eta:{key}"
        client.lpush(rkey, f"{duration_seconds:.2f}")
        client.ltrim(rkey, 0, _MAX_SAMPLES - 1)
        client.expire(rkey, 30 * 24 * 3600)
    except Exception:
        pass


def record_job_eta_sample(job: GenerationJob, meta: dict[str, Any] | None = None) -> None:
    """Record ETA sample from job metadata using de-poisoned duration."""
    sample = eta_sample_seconds(meta if meta is not None else (job.provider_metadata or {}))
    if sample is not None:
        record_duration_sample(job, sample)


def average_duration_seconds(endpoint_key: str) -> float | None:
    samples = list(_MEMORY_AVG.get(endpoint_key) or [])
    client = _get_redis()
    if client is not None:
        try:
            remote = client.lrange(f"jewel:eta:{endpoint_key}", 0, _MAX_SAMPLES - 1)
            for raw in remote or []:
                try:
                    samples.append(float(raw))
                except ValueError:
                    pass
        except Exception:
            pass
    if not samples:
        return None
    return sum(samples) / len(samples)


def attach_eta_fields(job: GenerationJob, meta: dict[str, Any]) -> dict[str, Any]:
    out = attach_duration_splits(dict(meta or {}))
    if job.status not in ("PENDING", "PROCESSING"):
        out.pop("etaSeconds", None)
        return out

    avg = average_duration_seconds(_endpoint_key(job))
    if avg is None:
        # Catalog / Nano Banana typically lands ~30–60s end-to-end once fal is warm.
        avg = (
            45.0
            if (out.get("progressStage") == "waiting_on_fal" or out.get("webhook_pending"))
            else 25.0
        )
        out["etaSource"] = "default"
    else:
        out["etaSource"] = "rolling_average"

    started = job.processing_started_at or job.created_at
    elapsed = 0.0
    if started is not None:
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        elapsed = max(0.0, (datetime.now(timezone.utc) - started).total_seconds())

    # Don't clamp to a misleading "~5s" forever after the estimate is exceeded —
    # show a growing "still working" window instead.
    remaining = avg - elapsed
    if remaining <= 0:
        remaining = min(30.0, max(8.0, avg * 0.25))
        out["etaOverdue"] = True
    else:
        out["etaOverdue"] = False

    out["etaSeconds"] = int(round(remaining))
    out["etaAverageSeconds"] = int(round(avg))
    out["etaElapsedSeconds"] = int(round(elapsed))
    return out


def duration_from_timing(meta: dict[str, Any] | None) -> float | None:
    timing = (meta or {}).get("timing") or {}
    started = (
        timing.get("worker_started")
        or timing.get("processing_started")
        or timing.get("started")
        or timing.get("queued")
    )
    completed = timing.get("completed") or timing.get("storage_saved")
    if not started or not completed:
        return None
    try:
        t0 = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(str(completed).replace("Z", "+00:00"))
        return max(0.0, (t1 - t0).total_seconds())
    except Exception:
        return None
