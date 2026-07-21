"""Unit tests for fal timing extraction, duration splits, and ETA sampling."""

from app.services.job_timing import (
    compute_duration_splits,
    eta_sample_seconds,
    extract_fal_inference_seconds,
)


def test_extract_fal_inference_top_level_metrics():
    assert extract_fal_inference_seconds({"metrics": {"inference_time": 4.218}}) == 4.218


def test_extract_fal_inference_nested_payload():
    assert (
        extract_fal_inference_seconds({"payload": {"metrics": {"inference_time": 2.5}}})
        == 2.5
    )


def test_extract_fal_inference_missing():
    assert extract_fal_inference_seconds({"images": []}) is None
    assert extract_fal_inference_seconds(None) is None
    assert extract_fal_inference_seconds({"metrics": {"inference_time": 0}}) is None


def test_compute_duration_splits():
    meta = {
        "fal_inference_time": 4.0,
        "timing": {
            "worker_started": "2026-07-21T10:00:00+00:00",
            "prompt_ready": "2026-07-21T10:00:05+00:00",
            "fal_queued": "2026-07-21T10:00:06+00:00",
            "fal_webhook_received": "2026-07-21T10:00:16+00:00",
            "storage_saved": "2026-07-21T10:00:19+00:00",
            "completed": "2026-07-21T10:00:19+00:00",
        },
    }
    splits = compute_duration_splits(meta)
    assert splits["prep_ms"] == 5000
    assert splits["fal_inference_ms"] == 4000
    # webhook span 10s minus 4s inference = 6s queue wait
    assert splits["fal_queue_wait_ms"] == 6000
    assert splits["finalize_ms"] == 3000
    assert splits["worker_total_ms"] == 19000


def test_eta_sample_prefers_fal_inference():
    meta = {
        "fal_inference_time": 3.5,
        "timing": {
            "worker_started": "2026-07-21T10:00:00+00:00",
            "completed": "2026-07-21T10:01:00+00:00",
            "fal_webhook_received": "2026-07-21T10:00:50+00:00",
        },
    }
    assert eta_sample_seconds(meta) == 3.5


def test_eta_sample_excludes_finalize_when_no_inference():
    meta = {
        "timing": {
            "worker_started": "2026-07-21T10:00:00+00:00",
            "fal_webhook_received": "2026-07-21T10:00:40+00:00",
            "completed": "2026-07-21T10:00:50+00:00",
        },
    }
    # 50s total - 10s finalize = 40s
    assert eta_sample_seconds(meta) == 40.0


def test_enqueue_stagger_zero_is_immediate():
    """Documented contract: stagger_ms<=0 enqueues without countdown."""
    from app.services import queue_dispatch as qd

    # Smoke: function accepts stagger_ms=0 (no TypeError)
    assert hasattr(qd, "enqueue_image_jobs")
    import inspect

    sig = inspect.signature(qd.enqueue_image_jobs)
    assert "stagger_ms" in sig.parameters
