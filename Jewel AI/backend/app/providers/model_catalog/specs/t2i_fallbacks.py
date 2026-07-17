"""T2I fallback models for workflows with no product image."""

from __future__ import annotations

from app.providers.model_catalog.spec import ImageContract, ModelSpec, ModelUiMeta

_FLUX_SCHNELL_SCHEMA = {
    "type": "object",
    "properties": {
        "image_size": {
            "type": "string",
            "title": "Image size",
            "enum": ["square_hd", "square", "portrait_4_3", "portrait_16_9", "landscape_4_3", "landscape_16_9"],
            "default": "square_hd",
        },
        "num_inference_steps": {"type": "integer", "title": "Steps", "minimum": 1, "maximum": 12, "default": 4},
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "enable_safety_checker": {"type": "boolean", "title": "Safety checker", "default": True},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

_FLUX_2_PRO_T2I_SCHEMA = {
    "type": "object",
    "properties": {
        "image_size": {
            "type": "string",
            "title": "Image size",
            "enum": ["square_hd", "square", "portrait_4_3", "portrait_16_9", "landscape_4_3", "landscape_16_9", "auto"],
            "default": "square_hd",
        },
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "safety_tolerance": {
            "type": "string",
            "title": "Safety tolerance",
            "enum": ["1", "2", "3", "4", "5", "6"],
            "default": "2",
        },
        "output_format": {
            "type": "string",
            "title": "Output format",
            "enum": ["jpeg", "png"],
            "default": "jpeg",
        },
        "seed": {"type": "integer", "title": "Seed"},
    },
}

T2I_CAPS = {
    "text_to_image": True,
    "image_to_image": False,
    "requires_image": False,
    "requires_mask": False,
    "multi_image": False,
    "person_generation": True,
    "material_accuracy": True,
}

T2I_FALLBACK_SPECS: list[ModelSpec] = [
    ModelSpec(
        endpoint_id="fal-ai/flux/schnell",
        display_name="FLUX Schnell (T2I)",
        family="t2i",
        category="text_to_image",
        capabilities=dict(T2I_CAPS),
        input_schema=_FLUX_SCHNELL_SCHEMA,
        default_params={
            "image_size": "square_hd",
            "num_inference_steps": 4,
            "num_images": 1,
            "enable_safety_checker": True,
        },
        image=ImageContract(mode="none", min_images=0, max_images=0),
        ui=ModelUiMeta(
            provider="bfl",
            provider_label="Black Forest Labs",
            tasks=("T2I",),
            docs_url="https://fal.ai/models/fal-ai/flux/schnell",
            pricing_note="~$0.003/MP",
            supports_edit=False,
            supports_i2i=False,
            supports_t2i=True,
            badge="T2I",
        ),
        workflow_allowlist=["CUSTOM_PROMPT"],
        sort_order=90,
        cost_per_call=0.003,
        builder_id="t2i",
        config_extra={"output_paths": ["images", "image"]},
    ),
    ModelSpec(
        endpoint_id="fal-ai/flux-2-pro",
        display_name="FLUX 2 Pro (T2I)",
        family="t2i",
        category="text_to_image",
        capabilities=dict(T2I_CAPS),
        input_schema=_FLUX_2_PRO_T2I_SCHEMA,
        default_params={
            "image_size": "square_hd",
            "num_images": 1,
            "safety_tolerance": "2",
            "output_format": "jpeg",
        },
        image=ImageContract(mode="none", min_images=0, max_images=0),
        ui=ModelUiMeta(
            provider="bfl",
            provider_label="Black Forest Labs",
            tasks=("T2I",),
            docs_url="https://fal.ai/models/fal-ai/flux-2-pro",
            supports_edit=False,
            supports_i2i=False,
            supports_t2i=True,
            badge="T2I",
        ),
        workflow_allowlist=["CUSTOM_PROMPT"],
        sort_order=91,
        cost_per_call=0.03,
        builder_id="t2i",
        config_extra={"output_paths": ["images", "image"]},
    ),
]
