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
    return str(meta.get("modelEndpointId") or meta.get("modelName") or job.provider_model or job.workflow or "default")


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
    out = dict(meta or {})
    if job.status not in ("PENDING", "PROCESSING"):
        out.pop("etaSeconds", None)
        return out

    avg = average_duration_seconds(_endpoint_key(job))
    if avg is None:
        # Catalog / Nano Banana typically lands ~30–60s end-to-end once fal is warm.
        avg = 45.0 if (out.get("progressStage") == "waiting_on_fal" or out.get("webhook_pending")) else 25.0
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
    completed = timing.get("completed")
    if not started or not completed:
        return None
    try:
        t0 = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(str(completed).replace("Z", "+00:00"))
        return max(0.0, (t1 - t0).total_seconds())
    except Exception:
        return None
