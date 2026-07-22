"""Per-model smoke tests for fal adapter argument building (full catalog)."""

import pytest

from app.models import ModelDefinition
from app.providers.adapters.fal import _build_arguments, _image_input_field, _merge_params
from app.providers.types import GenerationRequest
from seeds.fal_models_data import FAL_MODELS


def _model_for(endpoint_id: str) -> ModelDefinition:
    spec = next(s for s in FAL_MODELS if s["endpoint_id"] == endpoint_id)
    return ModelDefinition(
        endpoint_id=spec["endpoint_id"],
        display_name=spec["display_name"],
        category=spec["category"],
        input_schema=spec["input_schema"],
        default_params=spec["default_params"],
        config=spec.get("config", {}),
        capabilities=spec.get("capabilities", {}),
    )


def test_catalog_model_count():
    assert len(FAL_MODELS) == 25


@pytest.mark.parametrize("spec", FAL_MODELS, ids=[m["endpoint_id"] for m in FAL_MODELS])
def test_each_model_builds_arguments(spec):
    endpoint = spec["endpoint_id"]
    model = _model_for(endpoint)
    config = spec.get("config") or {}
    is_vton = config.get("input_mode") == "try_on"
    fal_urls = (
        ["https://fal.media/product.jpg", "https://fal.media/model.jpg"]
        if is_vton
        else ["https://fal.media/product.jpg"]
    )
    req = GenerationRequest(
        prompt="luxury jewelry catalog shot on white background",
        image_urls=fal_urls,
        workflow="CUSTOMER_TRY_ON" if is_vton else "CATALOG_IMAGE",
        number_of_images=2 if is_vton else 1,
    )
    args = _build_arguments(req, model, endpoint, fal_urls)
    if config.get("omit_prompt"):
        assert "prompt" not in args
        assert "instruction" not in args or config.get("prompt_field") == "instruction"
    else:
        prompt_field = config.get("prompt_field", "prompt")
        assert prompt_field in args
    if is_vton:
        assert "image_url" not in args or config.get("image_field") == "image_urls"
    else:
        field = config.get("image_field")
        assert field in args


@pytest.mark.parametrize("spec", FAL_MODELS, ids=[m["endpoint_id"] for m in FAL_MODELS])
def test_image_field_from_config(spec):
    config = spec.get("config") or {}
    if config.get("input_mode") == "try_on" and config.get("try_on_fields"):
        return
    endpoint = spec["endpoint_id"]
    model = _model_for(endpoint)
    field = config.get("image_field")
    if field:
        assert _image_input_field(model, endpoint) == field


def test_fashn_aliases_num_samples():
    model = _model_for("fal-ai/fashn/tryon/v1.6")
    req = GenerationRequest(
        prompt="",
        image_urls=["a", "b"],
        workflow="CUSTOMER_TRY_ON",
        number_of_images=3,
    )
    merged = _merge_params(model, req)
    assert merged.get("num_samples") == 3


def test_gpt_edit_uses_image_urls():
    model = _model_for("openai/gpt-image-2/edit")
    req = GenerationRequest(
        prompt="test",
        image_urls=["/uploads/test.jpg"],
        workflow="CATALOG_IMAGE",
    )
    args = _build_arguments(req, model, model.endpoint_id, ["https://fal.media/test.jpg"])
    assert args["image_urls"] == ["https://fal.media/test.jpg"]
    assert "image_url" not in args


def test_flux_dev_i2i_uses_image_url():
    model = _model_for("fal-ai/flux/dev/image-to-image")
    req = GenerationRequest(prompt="luxury jewelry", image_urls=["/ring.jpg"], workflow="CATALOG_IMAGE")
    args = _build_arguments(req, model, model.endpoint_id, ["https://fal.media/ring.jpg"])
    assert args["image_url"] == "https://fal.media/ring.jpg"
    assert "image_urls" not in args
