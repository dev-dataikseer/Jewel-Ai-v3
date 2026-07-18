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
    "asset_ids",
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
    "logo_asset_id",
    "logo_url",
    "aspect_ratio",
    "person_generation",
    "number_of_images",
    "model_endpoint_id",
    "model_name",
    "model_params",
    "batch_name",
}

# Workflows that generate images and must include a product asset
GENERATION_WORKFLOWS = ALLOWED_WORKFLOWS - {"BULK_GENERATION"}

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


# Deterministic multi-type order for compose / regression stability.
SUBTYPE_ORDER: list[str] = [
    "Ring",
    "Necklace",
    "Earrings (Studs)",
    "Earrings (Drops)",
    "Earrings (Hoops)",
    "Bracelet",
    "Bangles",
    "Pendant",
    "Kara",
    "Watch",
    "Brooch",
    "Anklet",
    "Cufflinks",
    "Multiple Items",
]
_SUBTYPE_RANK = {name: i for i, name in enumerate(SUBTYPE_ORDER)}


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
    """Drop generic 'Multiple Items' when specifics present; sort by SUBTYPE_ORDER."""
    if len(types) > 1 and "Multiple Items" in types:
        types = [t for t in types if t != "Multiple Items"]
    return sorted(types, key=lambda t: (_SUBTYPE_RANK.get(t, 1000), t))


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

    # Bulk uses asset_ids; single jobs need asset_id for generation workflows
    if workflow == "BULK_GENERATION" or data.get("asset_ids"):
        asset_ids = data.get("asset_ids") or []
        if not asset_ids:
            raise HTTPException(status_code=400, detail="asset_ids required for bulk generation")
    elif workflow in GENERATION_WORKFLOWS or workflow in ALLOWED_WORKFLOWS:
        if not data.get("asset_id"):
            raise HTTPException(status_code=400, detail="asset_id is required for image generation")


def validate_upload(content_type: str, size_bytes: int, content: bytes | None = None) -> None:
    if content_type not in ALLOWED_UPLOAD_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported content type: {content_type}")
    if size_bytes > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 20 MB)")
    if content:
        validate_image_magic_bytes(content, content_type)


def validate_image_magic_bytes(content: bytes, content_type: str) -> None:
    """Verify file header matches declared image type."""
    if len(content) < 12:
        raise HTTPException(status_code=400, detail="File too small to be a valid image")
    if content_type == "image/jpeg" and not content[:3] == b"\xff\xd8\xff":
        raise HTTPException(status_code=400, detail="File content does not match JPEG")
    if content_type == "image/png" and not content[:8] == b"\x89PNG\r\n\x1a\n":
        raise HTTPException(status_code=400, detail="File content does not match PNG")
    if content_type == "image/webp":
        if not (content[:4] == b"RIFF" and content[8:12] == b"WEBP"):
            raise HTTPException(status_code=400, detail="File content does not match WebP")
