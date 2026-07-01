"""Validate model params and generation requests against ModelDefinition schema."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.models import ModelDefinition
from app.providers.types import GenerationRequest

SYSTEM_PARAM_KEYS = frozenset(
    {
        "prompt",
        "instruction",
        "image_url",
        "image_urls",
        "negative_prompt",
        "mask_url",
        "mask_image_url",
        "model_image",
        "garment_image",
        "person_image_url",
        "clothing_image_url",
        "human_image_url",
        "garment_image_url",
    }
)


def _coerce_value(prop: dict[str, Any], value: Any) -> Any:
    prop_type = prop.get("type")
    if prop_type == "integer":
        return int(value)
    if prop_type == "number":
        return float(value)
    if prop_type == "boolean":
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes")
    return value


def validate_model_params(model_def: ModelDefinition | None, params: dict[str, Any] | None) -> dict[str, Any]:
    if not model_def:
        return dict(params or {})
    schema = model_def.input_schema or {}
    props = schema.get("properties") or {}
    merged = {**(model_def.default_params or {}), **(params or {})}
    cleaned: dict[str, Any] = {}

    for key, value in merged.items():
        if key in SYSTEM_PARAM_KEYS:
            continue
        if value is None or value == "":
            continue
        prop = props.get(key)
        if not prop:
            continue
        try:
            coerced = _coerce_value(prop, value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=400,
                detail={"field": key, "message": f"Invalid value for {key}: {exc}"},
            ) from exc
        enum = prop.get("enum")
        if enum and coerced not in enum:
            raise HTTPException(
                status_code=400,
                detail={"field": key, "message": f"Must be one of: {', '.join(map(str, enum))}"},
            )
        minimum = prop.get("minimum")
        maximum = prop.get("maximum")
        if minimum is not None and coerced < minimum:
            raise HTTPException(status_code=400, detail={"field": key, "message": f"Minimum is {minimum}"})
        if maximum is not None and coerced > maximum:
            raise HTTPException(status_code=400, detail={"field": key, "message": f"Maximum is {maximum}"})
        cleaned[key] = coerced

    return cleaned


def validate_generation_request(model_def: ModelDefinition | None, request: GenerationRequest) -> None:
    if not model_def:
        return

    caps = model_def.capabilities or {}
    config = model_def.config or {}
    image_count = len(request.image_urls or [])

    if caps.get("requires_image", True) and image_count < 1:
        raise HTTPException(status_code=400, detail="This model requires an input image")

    min_images = int(config.get("min_images", 1))
    if image_count < min_images:
        raise HTTPException(
            status_code=400,
            detail=f"This model requires at least {min_images} image(s); received {image_count}",
        )

    if caps.get("virtual_try_on") and image_count < 2:
        raise HTTPException(
            status_code=400,
            detail="Virtual try-on models require product and model portrait images",
        )

    if request.workflow and model_def.workflow_allowlist is not None:
        if request.workflow not in model_def.workflow_allowlist:
            raise HTTPException(
                status_code=400,
                detail=f"Model {model_def.endpoint_id} is not allowed for workflow {request.workflow}",
            )

    omit_prompt = bool(config.get("omit_prompt"))
    if not omit_prompt and (not request.prompt or not request.prompt.strip()):
        raise HTTPException(status_code=400, detail="A prompt is required for this model")
