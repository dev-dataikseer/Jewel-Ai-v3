"""One-off: dump recent production job timing (run via railway run)."""
from __future__ import annotations

import json
import traceback
from pathlib import Path

OUT = Path(__file__).resolve().parent / "_latency_baseline.json"


def main() -> None:
    try:
        from app.config import get_settings
        from app.database import SessionLocal
        from app.models import GenerationJob
        from app.services.job_timing import compute_duration_splits
        from sqlalchemy import desc

        s = get_settings()
        db = SessionLocal()
        jobs = db.query(GenerationJob).order_by(desc(GenerationJob.created_at)).limit(20).all()
        rows = []
        for j in jobs:
            meta = j.provider_metadata or {}
            timing = meta.get("timing") or {}
            splits = compute_duration_splits(meta)
            created = j.created_at
            started = j.processing_started_at
            queue_ms = None
            if created and started:
                c = created if created.tzinfo else created
                st = started if started.tzinfo else started
                try:
                    queue_ms = max(0, int((st - c).total_seconds() * 1000))
                except Exception:
                    queue_ms = None
            rows.append(
                {
                    "id": j.id,
                    "status": j.status,
                    "workflow": j.workflow,
                    "jewelry_type": j.jewelry_type,
                    "provider_model": j.provider_model,
                    "modelEndpointId": meta.get("modelEndpointId"),
                    "created_at": created.isoformat() if created else None,
                    "processing_started_at": started.isoformat() if started else None,
                    "updated_at": j.updated_at.isoformat() if j.updated_at else None,
                    "pre_worker_queue_ms": queue_ms,
                    "fal_request_id": meta.get("fal_request_id"),
                    "fal_inference_time": meta.get("fal_inference_time"),
                    "durationSplits": splits,
                    "timing": timing,
                    "progressStage": meta.get("progressStage"),
                    "webhook_pending": meta.get("webhook_pending"),
                    "latencyTrace": meta.get("latencyTrace"),
                }
            )
        db.close()
        payload = {
            "database_url_host": (s.database_url or "").split("@")[-1][:80] if s.database_url else None,
            "fal_use_webhooks": bool(getattr(s, "fal_use_webhooks", False)),
            "latency_trace": bool(getattr(s, "latency_trace", False)),
            "fal_celery_rate_limit": getattr(s, "fal_celery_rate_limit", None),
            "celery_worker_concurrency": getattr(s, "celery_worker_concurrency", None),
            "storage_backend": getattr(s, "storage_backend", None),
            "node_env": getattr(s, "node_env", None),
            "jobs": rows,
        }
        OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"wrote {OUT} jobs={len(rows)}", flush=True)
    except Exception:
        OUT.write_text(traceback.format_exc(), encoding="utf-8")
        print("FAILED — see output file", flush=True)
        raise


if __name__ == "__main__":
    main()
