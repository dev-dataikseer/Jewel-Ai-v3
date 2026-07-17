"""Golden fixtures for model-first request builders."""

from app.models import ModelDefinition
from app.providers.model_catalog.builders import build_arguments
from app.providers.model_catalog.registry import get_spec, load_registry
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


def test_registry_loads_all_seed_models():
    load_registry(force=True)
    for raw in FAL_MODELS:
        assert get_spec(raw["endpoint_id"]) is not None


def test_nano_banana_builder_uses_image_urls_and_truncates():
    endpoint = "fal-ai/nano-banana-pro/edit"
    model = _model_for(endpoint)
    long_prompt = "A. " * 2000
    req = GenerationRequest(
        prompt=long_prompt,
        image_urls=["https://fal.media/a.jpg"],
        workflow="CATALOG_IMAGE",
        number_of_images=1,
    )
    args = build_arguments(req, ["https://fal.media/a.jpg"], model_def=model, endpoint=endpoint)
    assert "image_urls" in args
    assert args["image_urls"] == ["https://fal.media/a.jpg"]
    assert "prompt" in args
    assert len(args["prompt"]) <= 3600


def test_kontext_builder_uses_single_image_url():
    endpoint = "fal-ai/flux-pro/kontext"
    model = _model_for(endpoint)
    req = GenerationRequest(prompt="enhance metal", image_urls=["https://fal.media/a.jpg"])
    args = build_arguments(req, ["https://fal.media/a.jpg"], model_def=model, endpoint=endpoint)
    assert args["image_url"] == "https://fal.media/a.jpg"
    assert "image_urls" not in args


def test_fashn_vton_builder_maps_fields():
    endpoint = "fal-ai/fashn/tryon/v1.6"
    model = _model_for(endpoint)
    req = GenerationRequest(
        prompt="ignored",
        image_urls=["https://fal.media/product.jpg", "https://fal.media/person.jpg"],
        workflow="CUSTOMER_TRY_ON",
    )
    args = build_arguments(
        req,
        ["https://fal.media/product.jpg", "https://fal.media/person.jpg"],
        model_def=model,
        endpoint=endpoint,
    )
    assert args["garment_image"] == "https://fal.media/product.jpg"
    assert args["model_image"] == "https://fal.media/person.jpg"
    assert "prompt" not in args


def test_t2i_fallback_registered():
    load_registry(force=True)
    schnell = get_spec("fal-ai/flux/schnell")
    assert schnell is not None
    assert schnell.ui.supports_t2i
    assert schnell.builder_id == "t2i"


def test_seed_dicts_include_ui_limits():
    from app.providers.model_catalog.registry import seed_dicts

    load_registry(force=True)
    rows = seed_dicts()
    nano = next(r for r in rows if r["endpoint_id"] == "fal-ai/nano-banana-pro/edit")
    assert "ui" in nano["config"]
    assert nano["config"]["ui"]["badge"] == "I2I"
    assert nano["config"]["limits"]["max_prompt_chars"] == 3600
    assert nano["config"]["limits"]["official_prompt_status"] == "undocumented"
    gpt = next(r for r in rows if r["endpoint_id"] == "openai/gpt-image-2/edit")
    assert gpt["config"]["limits"]["official_max_prompt_chars"] == 32_000
    assert gpt["config"]["limits"]["recommended_max_prompt_chars"] == 12_000
    assert gpt["config"]["limits"]["max_prompt_chars"] == 12_000
