"""Spec-aware validation for model params and generation requests."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.models import ModelDefinition
from app.providers.model_catalog.registry import get_spec
from app.providers.model_catalog.spec import SYSTEM_FIELDS, ModelSpec, model_spec_from_seed_dict
from app.providers.types import GenerationRequest

# Back-compat alias used by older imports
SYSTEM_PARAM_KEYS = SYSTEM_FIELDS


def _spec_from_model_def(model_def: ModelDefinition | None) -> ModelSpec | None:
    if not model_def:
        return None
    cached = get_spec(model_def.endpoint_id)
    if cached:
        return cached
    return model_spec_from_seed_dict(
        {
            "endpoint_id": model_def.endpoint_id,
            "display_name": model_def.display_name,
            "category": model_def.category,
            "capabilities": model_def.capabilities or {},
            "input_schema": model_def.input_schema or {},
            "default_params": model_def.default_params or {},
            "workflow_allowlist": model_def.workflow_allowlist,
            "config": model_def.config or {},
            "sort_order": model_def.sort_order,
            "cost_per_call": model_def.cost_per_call,
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
                detail=f"{key}: Invalid value for {key}: {exc}",
            ) from exc
        enum = prop.get("enum")
        if enum and coerced not in enum:
            # Drop stale client prefs (e.g. old pixel sizes) instead of hard-failing.
            default = prop.get("default")
            if default is not None and default in enum:
                cleaned[key] = default
                continue
            if enum:
                cleaned[key] = enum[0]
                continue
            raise HTTPException(
                status_code=400,
                detail=f"{key}: Must be one of: {', '.join(map(str, enum))}",
            )
        minimum = prop.get("minimum")
        maximum = prop.get("maximum")
        if minimum is not None and coerced < minimum:
            raise HTTPException(status_code=400, detail=f"{key}: Minimum is {minimum}")
        if maximum is not None and coerced > maximum:
            raise HTTPException(status_code=400, detail=f"{key}: Maximum is {maximum}")
        cleaned[key] = coerced

    return cleaned


def validate_generation_request(model_def: ModelDefinition | None, request: GenerationRequest) -> None:
    if not model_def:
        return

    spec = _spec_from_model_def(model_def)
    caps = (spec.capabilities if spec else None) or (model_def.capabilities or {})
    image_count = len(request.image_urls or [])
    contract = spec.image if spec else None

    if contract and contract.mode != "none":
        if image_count < contract.min_images:
            raise HTTPException(
                status_code=400,
                detail=f"This model requires at least {contract.min_images} image(s); received {image_count}",
            )
        if contract.max_images and image_count > contract.max_images:
            raise HTTPException(
                status_code=400,
                detail=f"This model accepts at most {contract.max_images} image(s); received {image_count}",
            )
    else:
        if caps.get("requires_image", True) and image_count < 1:
            raise HTTPException(status_code=400, detail="This model requires an input image")

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

    omit_prompt = bool(contract.omit_prompt) if contract else bool((model_def.config or {}).get("omit_prompt"))
    if not omit_prompt and (not request.prompt or not request.prompt.strip()):
        raise HTTPException(status_code=400, detail="A prompt is required for this model")
