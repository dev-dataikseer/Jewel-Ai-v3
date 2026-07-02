"""Tests for fal adapter argument building."""

import pytest

from app.models import ModelDefinition
from app.providers.adapters.fal import _build_arguments, _image_input_field
from app.providers.fal_upload import discover_public_app_base
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


@pytest.mark.parametrize(
    "endpoint_id,expected_field",
    [
        ("fal-ai/nano-banana-pro/edit", "image_urls"),
        ("openai/gpt-image-2/edit", "image_urls"),
        ("fal-ai/flux-2-pro/edit", "image_urls"),
        ("fal-ai/flux-pro/kontext", "image_url"),
        ("fal-ai/bytedance/seedream/v5/lite/edit", "image_urls"),
        ("fal-ai/flux/dev/image-to-image", "image_url"),
    ],
)
def test_image_field_per_model(endpoint_id: str, expected_field: str):
    model = _model_for(endpoint_id)
    assert _image_input_field(model, endpoint_id) == expected_field


def test_build_requires_image():
    model = _model_for("fal-ai/flux-pro/kontext")
    req = GenerationRequest(prompt="test", image_urls=[], workflow="CATALOG_IMAGE")
    with pytest.raises(ValueError, match="requires an input image"):
        _build_arguments(req, model, "fal-ai/flux-pro/kontext", [])


def test_image_field_requires_config():
    with pytest.raises(ValueError, match="No image_field config"):
        _image_input_field(None, "fal-ai/unknown/model")


def test_discover_public_app_base_from_railway_service_url(monkeypatch):
    monkeypatch.delenv("API_PUBLIC_URL", raising=False)
    monkeypatch.setenv("RAILWAY_SERVICE_JEWEL_AI_V3_URL", "jewel-ai.up.railway.app")
    from app.config import get_settings

    get_settings.cache_clear()
    assert discover_public_app_base() == "https://jewel-ai.up.railway.app"
    get_settings.cache_clear()


def test_discover_public_app_base_uses_api_public_url(monkeypatch):
    monkeypatch.setenv("API_PUBLIC_URL", "https://jewel-ai.up.railway.app")
    from app.config import get_settings

    get_settings.cache_clear()
    assert discover_public_app_base() == "https://jewel-ai.up.railway.app"
    get_settings.cache_clear()



def test_fashn_try_on_maps_dual_fields():
    model = _model_for("fal-ai/fashn/tryon/v1.6")
    req = GenerationRequest(
        prompt="Place necklace on model",
        image_urls=["/uploads/ring.jpg", "/uploads/model.jpg"],
        workflow="CUSTOMER_TRY_ON",
    )
    args = _build_arguments(
        req,
        model,
        "fal-ai/fashn/tryon/v1.6",
        ["https://fal.media/ring.jpg", "https://fal.media/model.jpg"],
    )
    assert args["garment_image"] == "https://fal.media/ring.jpg"
    assert args["model_image"] == "https://fal.media/model.jpg"
    assert "prompt" not in args
    assert "image_url" not in args
    assert "image_urls" not in args


def test_fashn_requires_two_images():
    model = _model_for("fal-ai/fashn/tryon/v1.6")
    req = GenerationRequest(prompt="try on", image_urls=["/uploads/ring.jpg"], workflow="CUSTOMER_TRY_ON")
    with pytest.raises(ValueError, match="requires 2 images"):
        _build_arguments(req, model, "fal-ai/fashn/tryon/v1.6", ["https://fal.media/ring.jpg"])


def test_flux_lora_tryon_orders_person_first():
    model = _model_for("fal-ai/flux-2-lora-gallery/virtual-tryon")
    req = GenerationRequest(
        prompt="virtual try-on",
        image_urls=["/product.jpg", "/model.jpg"],
        workflow="JEWELRY_ON_MODEL",
    )
    args = _build_arguments(
        req,
        model,
        "fal-ai/flux-2-lora-gallery/virtual-tryon",
        ["https://fal.media/product.jpg", "https://fal.media/model.jpg"],
    )
    assert args["image_urls"] == ["https://fal.media/model.jpg", "https://fal.media/product.jpg"]
