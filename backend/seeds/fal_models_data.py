"""fal.ai catalog: text + image in → image out (no mask-required inpainting)."""

IMAGE_SIZE_ENUM = [
    "square_hd",
    "square",
    "portrait_4_3",
    "portrait_16_9",
    "landscape_4_3",
    "landscape_16_9",
]

NANO_BANANA_EDIT_PARAMS = {
    "type": "object",
    "properties": {
        "resolution": {
            "type": "string",
            "title": "Resolution",
            "enum": ["1K", "2K", "4K"],
            "default": "2K",
        },
        "aspect_ratio": {
            "type": "string",
            "title": "Aspect ratio",
            "enum": ["auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4", "2:3", "9:16"],
            "default": "auto",
        },
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "output_format": {
            "type": "string",
            "title": "Output format",
            "enum": ["jpeg", "png", "webp"],
            "default": "png",
        },
    },
}

GEMINI_EDIT_PARAMS = {
    **NANO_BANANA_EDIT_PARAMS,
    "properties": {
        **NANO_BANANA_EDIT_PARAMS["properties"],
        "enable_web_search": {"type": "boolean", "title": "Web search", "default": False},
    },
}

# Quality rank reference (mirrors sort_order on image-edit / VTON entries above).

GPT_EDIT_PARAMS = {
    "type": "object",
    "properties": {
        "image_size": {
            "type": "string",
            "title": "Image size",
            "enum": ["auto", "1024x1024", "1536x1024", "1024x1536"],
            "default": "auto",
        },
        "quality": {
            "type": "string",
            "title": "Quality",
            "enum": ["low", "medium", "high"],
            "default": "high",
        },
        "input_fidelity": {
            "type": "string",
            "title": "Input fidelity",
            "enum": ["low", "high"],
            "default": "high",
        },
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "output_format": {
            "type": "string",
            "title": "Output format",
            "enum": ["jpeg", "png", "webp"],
            "default": "png",
        },
    },
}

FLUX_EDIT_PARAMS = {
    "type": "object",
    "properties": {
        "image_size": {
            "type": "string",
            "title": "Image size",
            "enum": ["auto"] + IMAGE_SIZE_ENUM,
            "default": "auto",
        },
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "output_format": {
            "type": "string",
            "title": "Output format",
            "enum": ["jpeg", "png"],
            "default": "jpeg",
        },
        "safety_tolerance": {
            "type": "string",
            "title": "Safety tolerance",
            "enum": ["1", "2", "3", "4", "5"],
            "default": "2",
        },
        "enable_safety_checker": {"type": "boolean", "title": "Safety checker", "default": True},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

FLUX_KONTEXT_PARAMS = {
    "type": "object",
    "properties": {
        "guidance_scale": {
            "type": "number",
            "title": "Guidance scale",
            "minimum": 1,
            "maximum": 20,
            "default": 3.5,
        },
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "output_format": {
            "type": "string",
            "title": "Output format",
            "enum": ["jpeg", "png"],
            "default": "jpeg",
        },
        "safety_tolerance": {
            "type": "string",
            "title": "Safety tolerance",
            "enum": ["1", "2", "3", "4", "5", "6"],
            "default": "2",
        },
        "enhance_prompt": {"type": "boolean", "title": "Enhance prompt", "default": True},
        "aspect_ratio": {
            "type": "string",
            "title": "Aspect ratio",
            "enum": ["21:9", "16:9", "4:3", "3:2", "1:1", "2:3", "3:4", "9:16", "9:21"],
            "default": "1:1",
        },
        "seed": {"type": "integer", "title": "Seed"},
    },
}

FLUX_REDUX_PARAMS = {
    "type": "object",
    "properties": {
        "image_size": {
            "type": "string",
            "title": "Image size",
            "enum": IMAGE_SIZE_ENUM,
            "default": "landscape_4_3",
        },
        "guidance_scale": {
            "type": "number",
            "title": "Guidance scale",
            "minimum": 1,
            "maximum": 20,
            "default": 3.5,
        },
        "num_inference_steps": {
            "type": "integer",
            "title": "Inference steps",
            "minimum": 1,
            "maximum": 50,
            "default": 28,
        },
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "output_format": {
            "type": "string",
            "title": "Output format",
            "enum": ["jpeg", "png"],
            "default": "jpeg",
        },
        "enhance_prompt": {"type": "boolean", "title": "Enhance prompt", "default": True},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

RECRAFT_I2I_PARAMS = {
    "type": "object",
    "properties": {
        "style": {
            "type": "string",
            "title": "Style",
            "enum": ["realistic_image", "digital_illustration", "vector_illustration", "icon"],
            "default": "realistic_image",
        },
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
    },
}

IDEOGRAM_REMIX_PARAMS = {
    "type": "object",
    "properties": {
        "strength": {
            "type": "number",
            "title": "Remix strength",
            "minimum": 0,
            "maximum": 1,
            "default": 0.8,
        },
        "rendering_speed": {
            "type": "string",
            "title": "Rendering speed",
            "enum": ["TURBO", "BALANCED", "QUALITY"],
            "default": "BALANCED",
        },
        "expand_prompt": {"type": "boolean", "title": "Magic prompt", "default": True},
        "image_size": {
            "type": "string",
            "title": "Image size",
            "enum": IMAGE_SIZE_ENUM,
            "default": "square_hd",
        },
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

IMAGE_EDIT_CAPS = {
    "text_to_image": False,
    "image_to_image": True,
    "requires_image": True,
    "requires_mask": False,
    "multi_image": False,
    "person_generation": True,
    "material_accuracy": True,
}

VTON_CAPS = {
    **IMAGE_EDIT_CAPS,
    "multi_image": True,
    "virtual_try_on": True,
}

SEEDREAM_EDIT_PARAMS = {
    "type": "object",
    "properties": {
        "image_size": {
            "type": "string",
            "title": "Image size",
            "enum": ["auto_4K", "auto_2K"],
            "default": "auto_4K",
        },
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 6, "default": 1},
        "enable_safety_checker": {"type": "boolean", "title": "Safety checker", "default": True},
    },
}

FASHN_TRYON_PARAMS = {
    "type": "object",
    "properties": {
        "garment_photo_type": {
            "type": "string",
            "title": "Garment photo type",
            "enum": ["auto", "model", "flat-lay"],
            "default": "flat-lay",
        },
        "mode": {
            "type": "string",
            "title": "Quality mode",
            "enum": ["performance", "balanced", "quality"],
            "default": "balanced",
        },
        "num_samples": {"type": "integer", "title": "Samples", "minimum": 1, "maximum": 4, "default": 1},
    },
}


def _enrich_model_spec(spec: dict) -> dict:
    """Apply default output_paths and param_aliases from input_schema."""
    config = dict(spec.get("config") or {})
    props = (spec.get("input_schema") or {}).get("properties") or {}
    aliases = dict(config.get("param_aliases") or {})
    if "num_samples" in props:
        aliases.setdefault("number_of_images", "num_samples")
    elif "num_images" in props:
        aliases.setdefault("number_of_images", "num_images")
    config.setdefault("output_paths", ["images", "image"])
    if aliases:
        config["param_aliases"] = aliases
    return {**spec, "config": config}


IMAGE_APPS_VTON_PARAMS = {
    "type": "object",
    "properties": {
        "preserve_pose": {"type": "boolean", "title": "Preserve pose", "default": True},
        "aspect_ratio": {
            "type": "string",
            "title": "Aspect ratio",
            "enum": ["1:1", "3:4", "4:3", "9:16", "16:9"],
            "default": "3:4",
        },
    },
}

FLUX_2_EDIT_PARAMS = {
    "type": "object",
    "properties": {
        "image_size": {
            "type": "string",
            "title": "Image size",
            "enum": ["auto"] + IMAGE_SIZE_ENUM,
            "default": "auto",
        },
        "guidance_scale": {"type": "number", "title": "Guidance scale", "minimum": 0, "maximum": 20, "default": 3.5},
        "num_inference_steps": {"type": "integer", "title": "Inference steps", "minimum": 1, "maximum": 50, "default": 28},
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "output_format": {"type": "string", "title": "Output format", "enum": ["jpeg", "png", "webp"], "default": "png"},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

FLUX_DEV_I2I_PARAMS = {
    "type": "object",
    "properties": {
        "strength": {"type": "number", "title": "Strength", "minimum": 0, "maximum": 1, "default": 0.35},
        "image_size": {"type": "string", "title": "Image size", "enum": IMAGE_SIZE_ENUM, "default": "square_hd"},
        "guidance_scale": {"type": "number", "title": "Guidance scale", "minimum": 1, "maximum": 20, "default": 3.5},
        "num_inference_steps": {"type": "integer", "title": "Inference steps", "minimum": 1, "maximum": 50, "default": 28},
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

BRIA_FIBO_EDIT_PARAMS = {
    "type": "object",
    "properties": {
        "instruction": {"type": "string", "title": "Structured instruction"},
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

GROK_EDIT_PARAMS = {
    "type": "object",
    "properties": {
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

IDEOGRAM_V4_I2I_PARAMS = {
    "type": "object",
    "properties": {
        "style_type": {
            "type": "string",
            "title": "Style",
            "enum": ["AUTO", "GENERAL", "REALISTIC", "DESIGN"],
            "default": "AUTO",
        },
        "rendering_speed": {
            "type": "string",
            "title": "Rendering speed",
            "enum": ["TURBO", "BALANCED", "QUALITY"],
            "default": "BALANCED",
        },
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

KOLORS_VTON_PARAMS = {
    "type": "object",
    "properties": {
        "sync_mode": {"type": "boolean", "title": "Sync mode", "default": False},
    },
}

CAT_VTON_PARAMS = {
    "type": "object",
    "properties": {
        "cloth_type": {
            "type": "string",
            "title": "Cloth type",
            "enum": ["upper", "lower", "overall", "inner", "outer"],
            "default": "upper",
        },
        "image_size": {"type": "string", "title": "Image size", "enum": IMAGE_SIZE_ENUM, "default": "portrait_4_3"},
        "num_inference_steps": {"type": "integer", "title": "Inference steps", "minimum": 1, "maximum": 50, "default": 30},
        "guidance_scale": {"type": "number", "title": "Guidance scale", "minimum": 0, "maximum": 20, "default": 2.5},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

LEFFA_VTON_PARAMS = {
    "type": "object",
    "properties": {
        "garment_type": {
            "type": "string",
            "title": "Garment type",
            "enum": ["upper_body", "lower_body", "dresses"],
            "default": "upper_body",
        },
        "num_inference_steps": {"type": "integer", "title": "Inference steps", "minimum": 1, "maximum": 50, "default": 30},
        "guidance_scale": {"type": "number", "title": "Guidance scale", "minimum": 0, "maximum": 20, "default": 2.5},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

FLUX_VTO_PARAMS = {
    "type": "object",
    "properties": {
        "guidance_scale": {"type": "number", "title": "Guidance scale", "minimum": 0, "maximum": 20, "default": 3.5},
        "num_inference_steps": {"type": "integer", "title": "Inference steps", "minimum": 1, "maximum": 50, "default": 28},
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "seed": {"type": "integer", "title": "Seed"},
    },
}


WORKFLOW_DEFAULTS: dict[str, str] = {
    "CATALOG_IMAGE": "fal-ai/gemini-3-pro-image-preview/edit",
    "BULK_GENERATION": "fal-ai/gemini-3-pro-image-preview/edit",
    "JEWELRY_ON_MODEL": "fal-ai/fashn/tryon/v1.6",
    "CUSTOMER_TRY_ON": "fal-ai/image-apps-v2/virtual-try-on",
    "GEMSTONE_COLOR_CHANGE": "fal-ai/flux-pro/kontext",
    "BACKGROUND_REPLACEMENT": "fal-ai/flux-pro/kontext",
    "LUXURY_ENHANCEMENT": "fal-ai/flux-pro/kontext",
    "REFERENCE_STYLE_MATCH": "fal-ai/gemini-3-pro-image-preview/edit",
    "CUSTOM_PROMPT": "fal-ai/gpt-image-1.5/edit",
}

_RAW_FAL_MODELS: list[dict] = [
    {
        "endpoint_id": "fal-ai/gemini-3-pro-image-preview/edit",
        "display_name": "Gemini 3 Pro Image",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True, "material_accuracy": True},
        "input_schema": GEMINI_EDIT_PARAMS,
        "default_params": {
            "resolution": "2K",
            "aspect_ratio": "auto",
            "num_images": 1,
            "output_format": "png",
            "enable_web_search": False,
        },
        "workflow_allowlist": None,
        "config": {"image_field": "image_urls"},
        "sort_order": 1,
        "cost_per_call": 0.15,
    },
    {
        "endpoint_id": "fal-ai/bytedance/seedream/v4.5/edit",
        "display_name": "Seedream 4.5 Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": SEEDREAM_EDIT_PARAMS,
        "default_params": {"image_size": "auto_4K", "num_images": 1, "enable_safety_checker": True},
        "workflow_allowlist": None,
        "config": {"image_field": "image_urls"},
        "sort_order": 2,
        "cost_per_call": 0.04,
    },
    {
        "endpoint_id": "fal-ai/gpt-image-1.5/edit",
        "display_name": "GPT Image 1.5 Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": GPT_EDIT_PARAMS,
        "default_params": {
            "image_size": "auto",
            "quality": "high",
            "input_fidelity": "high",
            "num_images": 1,
            "output_format": "png",
        },
        "workflow_allowlist": None,
        "config": {"image_field": "image_urls"},
        "sort_order": 3,
        "cost_per_call": 0.08,
    },
    {
        "endpoint_id": "fal-ai/nano-banana-pro/edit",
        "display_name": "Nano Banana Pro Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": NANO_BANANA_EDIT_PARAMS,
        "default_params": {"resolution": "2K", "aspect_ratio": "auto", "num_images": 1, "output_format": "png"},
        "workflow_allowlist": None,
        "config": {"image_field": "image_urls"},
        "sort_order": 4,
        "cost_per_call": 0.15,
    },
    {
        "endpoint_id": "fal-ai/flux-2-pro/edit",
        "display_name": "FLUX 2 Pro Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": FLUX_2_EDIT_PARAMS,
        "default_params": {"image_size": "auto", "guidance_scale": 3.5, "num_images": 1, "output_format": "png"},
        "workflow_allowlist": None,
        "config": {"image_field": "image_urls"},
        "sort_order": 5,
        "cost_per_call": 0.05,
    },
    {
        "endpoint_id": "fal-ai/flux-pro/kontext/max",
        "display_name": "FLUX Kontext Max",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "person_generation": False},
        "input_schema": FLUX_KONTEXT_PARAMS,
        "default_params": {
            "guidance_scale": 3.5,
            "num_images": 1,
            "output_format": "jpeg",
            "enhance_prompt": True,
            "aspect_ratio": "1:1",
        },
        "workflow_allowlist": None,
        "config": {"image_field": "image_url"},
        "sort_order": 6,
        "cost_per_call": 0.06,
    },
    {
        "endpoint_id": "fal-ai/flux-pro/kontext",
        "display_name": "FLUX Kontext",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "person_generation": False},
        "input_schema": FLUX_KONTEXT_PARAMS,
        "default_params": {
            "guidance_scale": 3.5,
            "num_images": 1,
            "output_format": "jpeg",
            "enhance_prompt": True,
            "aspect_ratio": "1:1",
        },
        "workflow_allowlist": None,
        "config": {"image_field": "image_url"},
        "sort_order": 7,
        "cost_per_call": 0.04,
    },
    {
        "endpoint_id": "fal-ai/flux-pro/v1.1-ultra/redux",
        "display_name": "FLUX 1.1 Pro Ultra Redux",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "person_generation": False},
        "input_schema": FLUX_REDUX_PARAMS,
        "default_params": {"image_size": "landscape_4_3", "guidance_scale": 3.5, "num_images": 1},
        "workflow_allowlist": None,
        "config": {"image_field": "image_url"},
        "sort_order": 8,
        "cost_per_call": 0.05,
    },
    {
        "endpoint_id": "fal-ai/flux-pro/v1.1/redux",
        "display_name": "FLUX 1.1 Redux",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "person_generation": False},
        "input_schema": FLUX_REDUX_PARAMS,
        "default_params": {"image_size": "landscape_4_3", "guidance_scale": 3.5, "num_images": 1},
        "workflow_allowlist": None,
        "config": {"image_field": "image_url"},
        "sort_order": 9,
        "cost_per_call": 0.04,
    },
    {
        "endpoint_id": "fal-ai/recraft/v3/image-to-image",
        "display_name": "Recraft V3 I2I",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "person_generation": False},
        "input_schema": RECRAFT_I2I_PARAMS,
        "default_params": {"style": "realistic_image", "num_images": 1},
        "workflow_allowlist": None,
        "config": {"image_field": "image_url", "max_prompt_chars": 1000},
        "sort_order": 10,
        "cost_per_call": 0.06,
    },
    {
        "endpoint_id": "fal-ai/ideogram/v3/remix",
        "display_name": "Ideogram V3 Remix",
        "category": "image_to_image",
        "capabilities": IMAGE_EDIT_CAPS,
        "input_schema": IDEOGRAM_REMIX_PARAMS,
        "default_params": {"strength": 0.8, "rendering_speed": "BALANCED", "expand_prompt": True, "image_size": "square_hd", "num_images": 1},
        "workflow_allowlist": None,
        "config": {"image_field": "image_url"},
        "sort_order": 11,
        "cost_per_call": 0.06,
    },
    {
        "endpoint_id": "fal-ai/flux-2/klein/9b/edit",
        "display_name": "FLUX 2 Klein 9B Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": FLUX_2_EDIT_PARAMS,
        "default_params": {"image_size": "auto", "guidance_scale": 3.5, "num_images": 1, "output_format": "png"},
        "workflow_allowlist": None,
        "config": {"image_field": "image_urls"},
        "sort_order": 12,
        "cost_per_call": 0.03,
    },
    {
        "endpoint_id": "bria/fibo-edit/edit",
        "display_name": "Bria FIBO Edit",
        "category": "image_to_image",
        "capabilities": IMAGE_EDIT_CAPS,
        "input_schema": BRIA_FIBO_EDIT_PARAMS,
        "default_params": {"num_images": 1},
        "workflow_allowlist": None,
        "config": {"image_field": "image_url", "prompt_field": "instruction", "max_prompt_chars": 4000},
        "sort_order": 13,
        "cost_per_call": 0.06,
    },
    {
        "endpoint_id": "xai/grok-imagine-image/edit",
        "display_name": "Grok Imagine Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": GROK_EDIT_PARAMS,
        "default_params": {"num_images": 1},
        "workflow_allowlist": None,
        "config": {"image_field": "image_urls"},
        "sort_order": 14,
        "cost_per_call": 0.04,
    },
    {
        "endpoint_id": "fal-ai/fashn/tryon/v1.6",
        "display_name": "FASHN Try-On v1.6",
        "category": "virtual_try_on",
        "capabilities": VTON_CAPS,
        "input_schema": FASHN_TRYON_PARAMS,
        "default_params": {"garment_photo_type": "flat-lay", "mode": "balanced", "num_samples": 1},
        "workflow_allowlist": ["JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"],
        "config": {
            "input_mode": "try_on",
            "try_on_fields": {"person": "model_image", "product": "garment_image"},
            "product_image_index": 0,
            "person_image_index": 1,
            "min_images": 2,
            "omit_prompt": True,
        },
        "sort_order": 40,
        "cost_per_call": 0.05,
    },
    {
        "endpoint_id": "fal-ai/image-apps-v2/virtual-try-on",
        "display_name": "Virtual Try-On (image-apps-v2)",
        "category": "virtual_try_on",
        "capabilities": VTON_CAPS,
        "input_schema": IMAGE_APPS_VTON_PARAMS,
        "default_params": {"preserve_pose": True, "aspect_ratio": "3:4"},
        "workflow_allowlist": ["JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"],
        "config": {
            "input_mode": "try_on",
            "try_on_fields": {"person": "person_image_url", "product": "clothing_image_url"},
            "product_image_index": 0,
            "person_image_index": 1,
            "min_images": 2,
            "omit_prompt": True,
        },
        "sort_order": 41,
        "cost_per_call": 0.05,
    },
    {
        "endpoint_id": "fal-ai/flux-2-lora-gallery/virtual-tryon",
        "display_name": "FLUX 2 LoRA Virtual Try-On",
        "category": "virtual_try_on",
        "capabilities": VTON_CAPS,
        "input_schema": {
            "type": "object",
            "properties": {
                "lora_scale": {"type": "number", "title": "LoRA scale", "minimum": 0, "maximum": 2, "default": 1},
                "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
            },
        },
        "default_params": {"lora_scale": 1, "num_images": 1},
        "workflow_allowlist": ["JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"],
        "config": {
            "input_mode": "try_on",
            "image_field": "image_urls",
            "try_on_image_order": ["person", "product"],
            "min_images": 2,
        },
        "sort_order": 42,
        "cost_per_call": 0.05,
    },
    {
        "endpoint_id": "fal-ai/kling/v1-5/kolors-virtual-try-on",
        "display_name": "Kling Kolors VTON v1.5",
        "category": "virtual_try_on",
        "capabilities": VTON_CAPS,
        "input_schema": KOLORS_VTON_PARAMS,
        "default_params": {"sync_mode": False},
        "workflow_allowlist": ["JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"],
        "config": {
            "input_mode": "try_on",
            "try_on_fields": {"person": "human_image_url", "product": "garment_image_url"},
            "product_image_index": 0,
            "person_image_index": 1,
            "min_images": 2,
            "omit_prompt": True,
        },
        "sort_order": 43,
        "cost_per_call": 0.07,
    },
    {
        "endpoint_id": "fal-ai/cat-vton",
        "display_name": "Cat-VTON",
        "category": "virtual_try_on",
        "capabilities": VTON_CAPS,
        "input_schema": CAT_VTON_PARAMS,
        "default_params": {"cloth_type": "upper", "image_size": "portrait_4_3", "num_inference_steps": 30, "guidance_scale": 2.5},
        "workflow_allowlist": ["JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"],
        "config": {
            "input_mode": "try_on",
            "try_on_fields": {"person": "human_image_url", "product": "garment_image_url"},
            "product_image_index": 0,
            "person_image_index": 1,
            "min_images": 2,
            "omit_prompt": True,
        },
        "sort_order": 44,
        "cost_per_call": 0.04,
    },
    {
        "endpoint_id": "fal-ai/leffa/virtual-tryon",
        "display_name": "Leffa Virtual Try-On",
        "category": "virtual_try_on",
        "capabilities": VTON_CAPS,
        "input_schema": LEFFA_VTON_PARAMS,
        "default_params": {"garment_type": "upper_body", "num_inference_steps": 30, "guidance_scale": 2.5},
        "workflow_allowlist": ["JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"],
        "config": {
            "input_mode": "try_on",
            "try_on_fields": {"person": "human_image_url", "product": "garment_image_url"},
            "product_image_index": 0,
            "person_image_index": 1,
            "min_images": 2,
            "omit_prompt": True,
        },
        "sort_order": 45,
        "cost_per_call": 0.05,
    },
]

FAL_MODELS = [_enrich_model_spec(spec) for spec in _RAW_FAL_MODELS]
