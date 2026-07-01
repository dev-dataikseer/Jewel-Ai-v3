"""Job payload validation — structured fields only."""

from __future__ import annotations

import re

from fastapi import HTTPException

from seeds.prompts_data import JEWELRY_TYPES, WORKFLOWS

JEWELRY_TYPE_SET = set(JEWELRY_TYPES)

ALLOWED_WORKFLOWS = {w["id"] for w in WORKFLOWS if w["id"] != "RATE_TOOLS"}

ALLOWED_UPLOAD_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB

JOB_FIELD_WHITELIST = {
    "workflow",
    "asset_id",
    "prompt_text",
    "jewelry_type",
    "metal_type",
    "gemstone_type",
    "gemstone_cut",
    "gemstone_target_color",
    "setting_type",
    "background_style",
    "lighting_style",
    "style_preset_id",
    "reference_url",
    "model_url",
    "aspect_ratio",
    "person_generation",
    "number_of_images",
    "model_endpoint_id",
    "model_name",
    "model_params",
}

_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(all\s+)?previous|forget\s+(all\s+)?instructions|disregard\s+(all\s+)?|override\s+(the\s+)?preservation)",
    re.IGNORECASE,
)


def whitelist_job_fields(data: dict) -> dict:
    return {k: v for k, v in data.items() if k in JOB_FIELD_WHITELIST}


def sanitize_user_prompt(text: str | None) -> str | None:
    if text is None:
        return None
    cleaned = str(text).strip()
    if not cleaned:
        return None
    for token in ("{{", "}}", "{%", "%}", "{#", "#}"):
        cleaned = cleaned.replace(token, "")
    cleaned = _INJECTION_PATTERNS.sub("", cleaned).strip()
    return cleaned or None


def parse_jewelry_types(raw: str | None) -> list[str]:
    """Split comma-separated jewelry types; default Ring when empty."""
    if not raw or not str(raw).strip():
        return ["Ring"]
    parts = [p.strip() for p in str(raw).split(",") if p.strip()]
    seen: set[str] = set()
    result: list[str] = []
    for part in parts:
        if part not in seen:
            seen.add(part)
            result.append(part)
    return result or ["Ring"]


def normalize_jewelry_types(types: list[str]) -> list[str]:
    """When specific types are selected, drop the generic 'Multiple Items' subject."""
    if len(types) > 1 and "Multiple Items" in types:
        return [t for t in types if t != "Multiple Items"]
    return types


def validate_job_create(data: dict) -> None:
    workflow = data.get("workflow")
    if workflow not in ALLOWED_WORKFLOWS:
        raise HTTPException(status_code=400, detail=f"Invalid workflow: {workflow}")

    jewelry_type = data.get("jewelry_type")
    if jewelry_type is not None:
        types = normalize_jewelry_types(parse_jewelry_types(jewelry_type))
        if not types:
            raise HTTPException(status_code=400, detail="At least one jewelry_type is required")
        for jt in types:
            if jt not in JEWELRY_TYPE_SET:
                raise HTTPException(status_code=400, detail=f"Invalid jewelry_type: {jt}")

    if "prompt_text" in data:
        data["prompt_text"] = sanitize_user_prompt(data.get("prompt_text"))


def validate_upload(content_type: str, size_bytes: int) -> None:
    if content_type not in ALLOWED_UPLOAD_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported content type: {content_type}")
    if size_bytes > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 20 MB)")
