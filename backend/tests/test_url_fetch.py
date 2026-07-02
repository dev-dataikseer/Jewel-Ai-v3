"""Tests for SSRF-safe URL validation."""

import pytest

from app.security.url_fetch import validate_image_url


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
