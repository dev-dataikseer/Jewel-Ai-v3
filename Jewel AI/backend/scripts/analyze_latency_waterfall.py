"""Analyze latency baseline dump → waterfall decision-tree labels."""
from __future__ import annotations

import json
from pathlib import Path
from statistics import median

SRC = Path(__file__).resolve().parent / "_latency_baseline.json"
OUT = Path(__file__).resolve().parents[2] / "docs" / "architecture" / "_latency_waterfall.json"


def label_job(j: dict) -> str:
    splits = j.get("durationSplits") or {}
    worker = splits.get("worker_total_ms") or 0
    prep = splits.get("prep_ms") or 0
    fal_inf = splits.get("fal_inference_ms")
    finalize = splits.get("finalize_ms")
    queue = j.get("pre_worker_queue_ms") or 0
    # Legacy subscribe: fal_submit→storage ≈ worker - prep
    fal_blended = max(0, worker - prep)

    if worker <= 0:
        return "unknown"
    if fal_inf is not None and fal_inf > 0.6 * worker:
        return "H2_fal_gpu"
    if prep > 0.3 * worker:
        return "H3_app_prep"
    if finalize is not None and finalize > 0.2 * worker:
        return "H4_app_post"
    if queue > max(5000, 0.3 * (worker + queue)):
        return "H5_celery_queue"
    if fal_blended > 0.6 * worker:
        return "H1_or_H2_fal_wall_blended_subscribe"
    return "mixed"


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    jobs = [j for j in data["jobs"] if j["status"] == "COMPLETED"]
    rows = []
    for j in jobs:
        splits = j["durationSplits"]
        worker = splits.get("worker_total_ms") or 0
        prep = splits.get("prep_ms") or 0
        fal_blended = max(0, worker - prep)
        rows.append(
            {
                "id": j["id"],
                "workflow": j["workflow"],
                "model": j["provider_model"],
                "jewelry_type": j["jewelry_type"],
                "pre_worker_queue_ms": j["pre_worker_queue_ms"],
                "prep_ms": prep,
                "fal_blended_ms": fal_blended,
                "fal_blended_pct": round(100 * fal_blended / worker, 1) if worker else None,
                "prep_pct": round(100 * prep / worker, 1) if worker else None,
                "worker_total_ms": worker,
                "fal_request_id": j["fal_request_id"],
                "fal_inference_time": j["fal_inference_time"],
                "label": label_job(j),
                "created_at": j["created_at"],
            }
        )

    by_label: dict[str, int] = {}
    for r in rows:
        by_label[r["label"]] = by_label.get(r["label"], 0) + 1

    workers = [r["worker_total_ms"] for r in rows]
    preps = [r["prep_ms"] for r in rows]
    falbs = [r["fal_blended_ms"] for r in rows]
    queues = [r["pre_worker_queue_ms"] for r in rows if r["pre_worker_queue_ms"] is not None]

    summary = {
        "n_completed": len(rows),
        "labels": by_label,
        "worker_total_ms": {"p50": int(median(workers)), "min": min(workers), "max": max(workers)},
        "prep_ms": {"p50": int(median(preps)), "min": min(preps), "max": max(preps)},
        "fal_blended_ms": {"p50": int(median(falbs)), "min": min(falbs), "max": max(falbs)},
        "pre_worker_queue_ms": {
            "p50": int(median(queues)),
            "min": min(queues),
            "max": max(queues),
        },
        "observability_gaps": {
            "fal_request_id_null_pct": 100.0,
            "fal_inference_null_pct": 100.0,
            "fal_queued_stamp_pct": 0.0,
            "path": "subscribe (FAL_USE_WEBHOOKS unset/false)",
        },
        "jobs": rows,
    }
    OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in summary if k != "jobs"}, indent=2))


if __name__ == "__main__":
    main()
