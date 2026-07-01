"""Tests for fal.ai API response normalization."""

from app.providers.fal_response import extract_image_urls


def test_extract_images_array():
    result = {"images": [{"url": "https://fal.media/a.png"}, {"url": "https://fal.media/b.png"}]}
    urls = extract_image_urls(result, {"output_paths": ["images", "image"]})
    assert urls == ["https://fal.media/a.png", "https://fal.media/b.png"]


def test_extract_single_image_object():
    result = {"image": {"url": "https://fal.media/single.png"}}
    urls = extract_image_urls(result, {"output_paths": ["images", "image"]})
    assert urls == ["https://fal.media/single.png"]


def test_extract_webhook_payload():
    result = {"payload": {"images": [{"url": "https://fal.media/hook.png"}]}}
    urls = extract_image_urls(result, {"output_paths": ["images", "image"]})
    assert urls == ["https://fal.media/hook.png"]


def test_extract_empty():
    assert extract_image_urls({}, {}) == []
