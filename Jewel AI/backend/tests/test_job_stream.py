"""Tests for job stream token auth and SSE scoping."""

from app.auth.security import create_job_stream_token, decode_job_stream_token


def test_stream_token_roundtrip():
    token = create_job_stream_token("user-1", ["job-a", "job-b"])
    payload = decode_job_stream_token(token)
    assert payload is not None
    assert payload["sub"] == "user-1"
    assert payload["type"] == "job_stream"
    assert set(payload["job_ids"]) == {"job-a", "job-b"}


def test_access_token_rejected_for_stream():
    from app.auth.security import create_access_token

    access = create_access_token("user-1", "user")
    assert decode_job_stream_token(access) is None
