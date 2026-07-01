"""Normalize fal.ai API responses to image URL lists."""

from __future__ import annotations

from typing import Any


def _extract_from_path(data: Any, path: str) -> list[Any]:
    if data is None:
        return []
    if path == "images":
        if isinstance(data, list):
            return data
        return []
    if path == "image":
        if isinstance(data, dict):
            return [data]
        if data:
            return [data]
        return []
    return []


def extract_image_urls(result: dict[str, Any] | Any, config: dict[str, Any] | None = None) -> list[str]:
    """Extract image URLs from fal subscribe/submit result using config.output_paths."""
    if not isinstance(result, dict):
        return []

    paths = (config or {}).get("output_paths") or ["images", "image"]
    urls: list[str] = []

    for path in paths:
        for item in _extract_from_path(result.get(path), path):
            if isinstance(item, dict):
                url = item.get("url")
                if url:
                    urls.append(str(url))
            elif item:
                urls.append(str(item))
        if urls:
            break

    # Webhook nested payload
    if not urls and isinstance(result.get("payload"), dict):
        nested = result["payload"]
        for path in paths:
            for item in _extract_from_path(nested.get(path), path):
                if isinstance(item, dict) and item.get("url"):
                    urls.append(str(item["url"]))
                elif item:
                    urls.append(str(item))
            if urls:
                break

    return urls
