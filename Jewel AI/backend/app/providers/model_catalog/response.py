"""Response parsing using ModelSpec output_paths."""

from __future__ import annotations

from typing import Any

from app.providers.fal_response import extract_image_urls
from app.providers.model_catalog.spec import ModelSpec


def parse_image_urls(result: dict[str, Any] | Any, spec: ModelSpec | None, config: dict | None = None) -> list[str]:
    cfg = dict(config or {})
    if spec:
        cfg = {**spec.to_seed_dict().get("config", {}), **cfg}
    return extract_image_urls(result if isinstance(result, dict) else {}, cfg)
