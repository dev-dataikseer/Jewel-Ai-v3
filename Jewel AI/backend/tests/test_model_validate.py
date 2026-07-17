"""Tests for model param validation."""

import pytest
from fastapi import HTTPException

from app.models import ModelDefinition
from app.providers.model_validate import validate_generation_request, validate_model_params
from app.providers.types import GenerationRequest
from seeds.fal_models_data import FAL_MODELS


def _model(endpoint_id: str) -> ModelDefinition:
    spec = next(s for s in FAL_MODELS if s["endpoint_id"] == endpoint_id)
    return ModelDefinition(
        endpoint_id=spec["endpoint_id"],
        display_name=spec["display_name"],
        category=spec["category"],
        input_schema=spec["input_schema"],
        default_params=spec["default_params"],
        config=spec.get("config", {}),
        capabilities=spec.get("capabilities", {}),
        workflow_allowlist=spec.get("workflow_allowlist"),
    )


def test_validate_model_params_enum():
    model = _model("fal-ai/nano-banana-pro/edit")
    with pytest.raises(HTTPException) as exc:
        validate_model_params(model, {"resolution": "8K"})
    assert exc.value.status_code == 400


def test_validate_model_params_merges_defaults():
    model = _model("fal-ai/flux-pro/kontext")
    params = validate_model_params(model, {})
    assert params["guidance_scale"] == 3.5


def test_validate_generation_requires_image():
    model = _model("fal-ai/flux-pro/kontext")
    req = GenerationRequest(prompt="test", image_urls=[], workflow="CATALOG_IMAGE")
    with pytest.raises(HTTPException) as exc:
        validate_generation_request(model, req)
    assert exc.value.status_code == 400


def test_validate_vton_requires_two_images():
    model = _model("fal-ai/fashn/tryon/v1.6")
    req = GenerationRequest(
        prompt="",
        image_urls=["https://a.jpg"],
        workflow="CUSTOMER_TRY_ON",
    )
    with pytest.raises(HTTPException):
        validate_generation_request(model, req)


def test_validate_vton_omits_prompt_requirement():
    model = _model("fal-ai/fashn/tryon/v1.6")
    req = GenerationRequest(
        prompt="",
        image_urls=["https://a.jpg", "https://b.jpg"],
        workflow="CUSTOMER_TRY_ON",
    )
    validate_generation_request(model, req)
