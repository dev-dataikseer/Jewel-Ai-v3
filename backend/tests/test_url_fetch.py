"""Tests for SSRF-safe URL validation and media signing."""

import pytest

from app.security.media_signing import sign_upload_path, verify_upload_signature
from app.security.url_fetch import is_app_upload_url, validate_image_url, validate_user_image_url


def test_allows_fal_media():
    validate_image_url("https://v3.fal.media/files/abc/output.png")


def test_rejects_http():
    with pytest.raises(ValueError, match="HTTPS"):
        validate_image_url("http://v3.fal.media/files/x.png")


def test_rejects_localhost():
    with pytest.raises(ValueError, match="not allowlisted|Localhost"):
        validate_image_url("https://localhost/image.png")


def test_rejects_unknown_host():
    with pytest.raises(ValueError, match="not allowlisted"):
        validate_image_url("https://evil.example.com/image.png")


def test_rejects_suffix_bypass_host():
    with pytest.raises(ValueError, match="not allowlisted"):
        validate_image_url("https://evilfal.ai/image.png")


def test_allows_relative_app_upload():
    assert is_app_upload_url("/uploads/abc.png")
    validate_user_image_url("/uploads/abc.png")


def test_rejects_private_reference_at_job_create():
    with pytest.raises(ValueError):
        validate_user_image_url("https://127.0.0.1/secret.png")


def test_media_signature_roundtrip():
    signed = sign_upload_path("abc/def.png")
    assert signed.startswith("/uploads/abc/def.png?")
    from urllib.parse import parse_qs, urlparse

    q = parse_qs(urlparse(signed).query)
    assert verify_upload_signature("abc/def.png", q["exp"][0], q["sig"][0])
    assert not verify_upload_signature("abc/def.png", q["exp"][0], "deadbeef")
