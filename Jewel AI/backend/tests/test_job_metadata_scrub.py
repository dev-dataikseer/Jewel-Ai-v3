"""Provider run-state scrubbing and cancel/regenerate guards."""

from types import SimpleNamespace

from app.api.routers.jobs import _job_has_fal_request, _scrub_provider_run_state


def test_scrub_removes_fal_and_webhook_keys():
    meta = {
        "modelEndpointId": "fal-ai/flux",
        "aspectRatio": "1:1",
        "fal_request_id": "req_old",
        "usage": {"request_id": "req_old"},
        "webhook_pending": True,
        "webhook_accepted": True,
        "webhook_completed": True,
        "webhook_timed_out": False,
        "composedPrompt": "secret prompt",
        "timing": {
            "queued": "2026-01-01T00:00:00+00:00",
            "fal_queued": "2026-01-01T00:01:00+00:00",
            "completed": "2026-01-01T00:02:00+00:00",
        },
        "catalogMode": "modern",
    }
    scrubbed = _scrub_provider_run_state(meta)
    assert scrubbed["modelEndpointId"] == "fal-ai/flux"
    assert scrubbed["aspectRatio"] == "1:1"
    assert scrubbed["catalogMode"] == "modern"
    assert "fal_request_id" not in scrubbed
    assert "usage" not in scrubbed
    assert "webhook_pending" not in scrubbed
    assert "webhook_completed" not in scrubbed
    assert "composedPrompt" not in scrubbed
    assert scrubbed["timing"] == {"queued": "2026-01-01T00:00:00+00:00"}


def test_scrub_empty_meta():
    assert _scrub_provider_run_state(None) == {}
    assert _scrub_provider_run_state({}) == {}


def test_job_has_fal_request_detects_ids():
    assert _job_has_fal_request(SimpleNamespace(provider_metadata={"fal_request_id": "abc"}))
    assert _job_has_fal_request(SimpleNamespace(provider_metadata={"usage": {"request_id": "abc"}}))
    assert not _job_has_fal_request(SimpleNamespace(provider_metadata={}))
    assert not _job_has_fal_request(SimpleNamespace(provider_metadata=None))
