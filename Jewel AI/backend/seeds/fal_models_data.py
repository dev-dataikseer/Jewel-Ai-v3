"""fal.ai catalog: text + image in → image out (no mask-required inpainting).

Runtime enrichment (ImageContract, UI/limits, builders) lives in
`app.providers.model_catalog`. Seeds here remain the schema/defaults source;
`seed_model_definitions` persists catalog `to_seed_dict()` rows into the DB.
"""

from seeds.model_catalog_info import MODEL_INFO

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
            "default": "1K",
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
        "safety_tolerance": {
            "type": "string",
            "title": "Safety tolerance",
            "enum": ["1", "2", "3", "4", "5", "6"],
            "default": "4",
        },
        "enable_web_search": {"type": "boolean", "title": "Web search", "default": False},
        "system_prompt": {"type": "string", "title": "System prompt"},
        "limit_generations": {"type": "boolean", "title": "Limit generations", "default": False},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

NANO_BANANA_BASE_PARAMS = {
    "type": "object",
    "properties": {
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
        "safety_tolerance": {
            "type": "string",
            "title": "Safety tolerance",
            "enum": ["1", "2", "3", "4", "5", "6"],
            "default": "4",
        },
        "limit_generations": {"type": "boolean", "title": "Limit generations", "default": False},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

NANO_BANANA_2_PARAMS = {
    "type": "object",
    "properties": {
        "resolution": {
            "type": "string",
            "title": "Resolution",
            "enum": ["0.5K", "1K", "2K", "4K"],
            "default": "1K",
        },
        "aspect_ratio": {
            "type": "string",
            "title": "Aspect ratio",
            "enum": [
                "auto",
                "21:9",
                "16:9",
                "3:2",
                "4:3",
                "5:4",
                "1:1",
                "4:5",
                "3:4",
                "2:3",
                "9:16",
                "4:1",
                "1:4",
                "8:1",
                "1:8",
            ],
            "default": "auto",
        },
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "output_format": {
            "type": "string",
            "title": "Output format",
            "enum": ["jpeg", "png", "webp"],
            "default": "png",
        },
        "safety_tolerance": {
            "type": "string",
            "title": "Safety tolerance",
            "enum": ["1", "2", "3", "4", "5", "6"],
            "default": "4",
        },
        "limit_generations": {"type": "boolean", "title": "Limit generations", "default": True},
        "enable_web_search": {"type": "boolean", "title": "Web search", "default": False},
        "system_prompt": {"type": "string", "title": "System prompt"},
        "thinking_level": {
            "type": "string",
            "title": "Thinking level",
            "enum": ["minimal", "high"],
        },
        "seed": {"type": "integer", "title": "Seed"},
    },
}

GEMINI_3_PRO_PARAMS = NANO_BANANA_EDIT_PARAMS
GEMINI_3_1_FLASH_PARAMS = NANO_BANANA_2_PARAMS

# Quality rank reference (mirrors sort_order on image-edit / VTON entries).

GPT_IMAGE_2_PARAMS = {
    "type": "object",
    "properties": {
        "image_size": {
            "type": "string",
            "title": "Image size",
            # Official fal openai/gpt-image-2/edit schema (Jul 2026)
            "enum": [
                "auto",
                "square_hd",
                "square",
                "portrait_4_3",
                "portrait_16_9",
                "landscape_4_3",
                "landscape_16_9",
            ],
            "default": "auto",
        },
        "quality": {
            "type": "string",
            "title": "Quality",
            "enum": ["auto", "low", "medium", "high"],
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

GPT_EDIT_PARAMS = GPT_IMAGE_2_PARAMS

GPT_IMAGE_1_5_PARAMS = {
    "type": "object",
    "properties": {
        "image_size": {
            "type": "string",
            "title": "Image size",
            "enum": ["auto", "1024x1024", "1536x1024", "1024x1536"],
            "default": "1024x1024",
        },
        "background": {
            "type": "string",
            "title": "Background",
            "enum": ["auto", "transparent", "opaque"],
            "default": "auto",
        },
        "quality": {
            "type": "string",
            "title": "Quality",
            "enum": ["low", "medium", "high"],
            "default": "medium",
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

FLUX_2_PRO_PARAMS = {
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

FLUX_2_DEV_EDIT_PARAMS = {
    "type": "object",
    "properties": {
        "image_size": {
            "type": "string",
            "title": "Image size",
            "enum": ["auto"] + IMAGE_SIZE_ENUM,
            "default": "auto",
        },
        "guidance_scale": {"type": "number", "title": "Guidance scale", "minimum": 0, "maximum": 20, "default": 2.5},
        "num_inference_steps": {"type": "integer", "title": "Inference steps", "minimum": 4, "maximum": 50, "default": 28},
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "acceleration": {
            "type": "string",
            "title": "Acceleration",
            "enum": ["none", "regular", "high"],
            "default": "regular",
        },
        "enable_prompt_expansion": {"type": "boolean", "title": "Prompt expansion", "default": False},
        "enable_safety_checker": {"type": "boolean", "title": "Safety checker", "default": True},
        "output_format": {"type": "string", "title": "Output format", "enum": ["jpeg", "png", "webp"], "default": "png"},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

FLUX_EDIT_PARAMS = FLUX_2_PRO_PARAMS

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
        "enhance_prompt": {"type": "boolean", "title": "Enhance prompt", "default": False},
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

# Seedream 5.0 Lite official enums include auto_3K; 4.5 docs list auto_2K/auto_4K only.
SEEDREAM_V5_LITE_EDIT_PARAMS = {
    "type": "object",
    "properties": {
        "image_size": {
            "type": "string",
            "title": "Image size",
            "enum": [
                "square_hd",
                "square",
                "portrait_4_3",
                "portrait_16_9",
                "landscape_4_3",
                "landscape_16_9",
                "auto_2K",
                "auto_3K",
                "auto_4K",
            ],
            "default": "auto_2K",
        },
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 6, "default": 1},
        "max_images": {"type": "integer", "title": "Max images per gen", "minimum": 1, "maximum": 6, "default": 1},
        "enable_safety_checker": {"type": "boolean", "title": "Safety checker", "default": True},
    },
}

SEEDREAM_V45_EDIT_PARAMS = {
    "type": "object",
    "properties": {
        "image_size": {
            "type": "string",
            "title": "Image size",
            "enum": [
                "square_hd",
                "square",
                "portrait_4_3",
                "portrait_16_9",
                "landscape_4_3",
                "landscape_16_9",
                "auto_2K",
                "auto_4K",
            ],
            "default": "auto_2K",
        },
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 6, "default": 1},
        "max_images": {"type": "integer", "title": "Max images per gen", "minimum": 1, "maximum": 6, "default": 1},
        "enable_safety_checker": {"type": "boolean", "title": "Safety checker", "default": True},
    },
}

# Back-compat alias used by older references / docs snippets.
SEEDREAM_EDIT_PARAMS = SEEDREAM_V5_LITE_EDIT_PARAMS

# Seedream 5.0 Pro uses a different endpoint id (no fal-ai/ prefix) and distinct size enums.
SEEDREAM_V5_PRO_EDIT_PARAMS = {
    "type": "object",
    "properties": {
        "image_size": {
            "type": "string",
            "title": "Image size",
            "enum": [
                "square_hd",
                "square",
                "portrait_4_3",
                "portrait_16_9",
                "landscape_4_3",
                "landscape_16_9",
                "auto_1K",
                "auto_2K",
            ],
            "default": "auto_2K",
        },
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 6, "default": 1},
        "output_format": {
            "type": "string",
            "title": "Output format",
            "enum": ["jpeg", "png"],
            "default": "jpeg",
        },
        "enable_safety_checker": {"type": "boolean", "title": "Safety checker", "default": True},
    },
}

FASHN_TRYON_PARAMS = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "title": "Garment category",
            "enum": ["auto", "tops", "bottoms", "one-pieces"],
            "default": "auto",
        },
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
    """Apply default output_paths, param_aliases, and catalog metadata."""
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
    info = MODEL_INFO.get(spec["endpoint_id"])
    if info:
        config["model_info"] = info
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
        "strength": {"type": "number", "title": "Strength", "minimum": 0.01, "maximum": 1, "default": 0.85},
        "image_size": {"type": "string", "title": "Image size", "enum": IMAGE_SIZE_ENUM, "default": "square_hd"},
        "guidance_scale": {"type": "number", "title": "Guidance scale", "minimum": 1, "maximum": 20, "default": 3.5},
        "num_inference_steps": {"type": "integer", "title": "Inference steps", "minimum": 10, "maximum": 50, "default": 40},
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "acceleration": {
            "type": "string",
            "title": "Acceleration",
            "enum": ["none", "regular", "high"],
            "default": "none",
        },
        "enable_safety_checker": {"type": "boolean", "title": "Safety checker", "default": True},
        "output_format": {"type": "string", "title": "Output format", "enum": ["jpeg", "png"], "default": "jpeg"},
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
        "aspect_ratio": {
            "type": "string",
            "title": "Aspect ratio",
            "enum": [
                "auto",
                "2:1",
                "20:9",
                "19.5:9",
                "16:9",
                "4:3",
                "3:2",
                "1:1",
                "2:3",
                "3:4",
                "9:16",
                "9:19.5",
                "9:20",
                "1:2",
            ],
            "default": "auto",
        },
        "resolution": {
            "type": "string",
            "title": "Resolution",
            "enum": ["1k", "2k"],
            "default": "1k",
        },
        "output_format": {
            "type": "string",
            "title": "Output format",
            "enum": ["jpeg", "png", "webp"],
            "default": "jpeg",
        },
    },
}

GLM_IMAGE_PARAMS = {
    "type": "object",
    "properties": {
        "image_size": {"type": "string", "title": "Image size", "enum": IMAGE_SIZE_ENUM, "default": "square_hd"},
        "num_inference_steps": {"type": "integer", "title": "Inference steps", "minimum": 10, "maximum": 100, "default": 30},
        "guidance_scale": {"type": "number", "title": "Guidance scale", "minimum": 1, "maximum": 10, "default": 1.5},
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "enable_safety_checker": {"type": "boolean", "title": "Safety checker", "default": True},
        "output_format": {"type": "string", "title": "Output format", "enum": ["jpeg", "png"], "default": "jpeg"},
        "enable_prompt_expansion": {"type": "boolean", "title": "Prompt expansion", "default": False},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

FIRERED_EDIT_PARAMS = {
    "type": "object",
    "properties": {
        "image_size": {"type": "string", "title": "Image size", "enum": ["auto"] + IMAGE_SIZE_ENUM, "default": "auto"},
        "num_inference_steps": {"type": "integer", "title": "Inference steps", "minimum": 2, "maximum": 50, "default": 30},
        "guidance_scale": {"type": "number", "title": "Guidance scale", "minimum": 1, "maximum": 10, "default": 4},
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "negative_prompt": {"type": "string", "title": "Negative prompt", "default": ""},
        "acceleration": {
            "type": "string",
            "title": "Acceleration",
            "enum": ["none", "regular", "high"],
            "default": "regular",
        },
        "enable_safety_checker": {"type": "boolean", "title": "Safety checker", "default": True},
        "output_format": {"type": "string", "title": "Output format", "enum": ["jpeg", "png"], "default": "png"},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

FLUX_2_MAX_PARAMS = {
    "type": "object",
    "properties": {
        "image_size": {
            "type": "string",
            "title": "Image size",
            "enum": ["auto"] + IMAGE_SIZE_ENUM,
            "default": "auto",
        },
        "safety_tolerance": {
            "type": "string",
            "title": "Safety tolerance",
            "enum": ["1", "2", "3", "4", "5"],
            "default": "2",
        },
        "enable_safety_checker": {"type": "boolean", "title": "Safety checker", "default": True},
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "output_format": {"type": "string", "title": "Output format", "enum": ["jpeg", "png"], "default": "jpeg"},
        "seed": {"type": "integer", "title": "Seed"},
    },
}

LUCY2_VTON_PARAMS = {
    "type": "object",
    "properties": {
        "prompt": {
            "type": "string",
            "title": "Try-on prompt",
            "default": (
                "Substitute the current top with the outfit from the reference image, "
                "matching its color, material, and fit"
            ),
        },
    },
}

IDEOGRAM_V4_I2I_PARAMS = {
    "type": "object",
    "properties": {
        "strength": {
            "type": "number",
            "title": "Edit strength",
            "minimum": 0,
            "maximum": 1,
            "default": 0.8,
        },
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
        "image_size": {
            "type": "string",
            "title": "Image size",
            "enum": IMAGE_SIZE_ENUM,
            "default": "square_hd",
        },
        "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
        "output_format": {
            "type": "string",
            "title": "Output format",
            "enum": ["jpeg", "png", "webp"],
            "default": "png",
        },
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
    "CATALOG_IMAGE": "fal-ai/nano-banana-pro/edit",
    "BULK_GENERATION": "fal-ai/nano-banana-pro/edit",
    "VIRTUAL_TRY_ON": "fal-ai/nano-banana-pro/edit",
    # Legacy aliases — jewelry compositing via image-edit, not garment VTON
    "JEWELRY_ON_MODEL": "fal-ai/nano-banana-pro/edit",
    "CUSTOMER_TRY_ON": "fal-ai/nano-banana-pro/edit",
    "GEMSTONE_COLOR_CHANGE": "fal-ai/flux-2-max/edit",
    "BACKGROUND_REPLACEMENT": "fal-ai/flux-2-max/edit",
    "LUXURY_ENHANCEMENT": "fal-ai/flux-pro/kontext",
    "REFERENCE_STYLE_MATCH": "fal-ai/nano-banana-pro/edit",
    "CUSTOM_PROMPT": "openai/gpt-image-2/edit",
}

_IMAGE_EDIT_MODELS: list[dict] = [
    {
        "endpoint_id": "fal-ai/gemini-3-pro-image-preview/edit",
        "display_name": "Gemini 3 Pro Image Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True, "material_accuracy": True},
        "input_schema": GEMINI_3_PRO_PARAMS,
        "default_params": {
            "resolution": "1K",
            "aspect_ratio": "auto",
            "num_images": 1,
            "output_format": "png",
            "safety_tolerance": "4",
            "enable_web_search": False,
            "limit_generations": False,
        },
        "workflow_allowlist": None,
        "config": {
            "image_field": "image_urls",
            "max_reference_images": 14,
            "recommended_max_prompt_chars": 3600,
            "official_prompt_status": "undocumented",
            "official_prompt_note": "Gemini / Nano Banana: no published character limit",
        },
        "sort_order": 2,
        "cost_per_call": 0.15,
    },
    {
        "endpoint_id": "fal-ai/nano-banana-pro/edit",
        "display_name": "Nano Banana Pro Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True, "material_accuracy": True},
        "input_schema": NANO_BANANA_EDIT_PARAMS,
        "default_params": {
            "resolution": "1K",
            "aspect_ratio": "auto",
            "num_images": 1,
            "output_format": "png",
            "safety_tolerance": "4",
            "enable_web_search": False,
        },
        "workflow_allowlist": None,
        "config": {
            "image_field": "image_urls",
            "max_reference_images": 14,
            "recommended_max_prompt_chars": 3600,
            "official_prompt_status": "undocumented",
            "official_prompt_note": "Gemini / Nano Banana: no published character limit",
        },
        "sort_order": 1,
        "cost_per_call": 0.15,
    },
    {
        "endpoint_id": "fal-ai/flux-2-max/edit",
        "display_name": "FLUX 2 Max Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True, "hex_matching": True},
        "input_schema": FLUX_2_MAX_PARAMS,
        "default_params": {
            "image_size": "auto",
            "safety_tolerance": "2",
            "enable_safety_checker": True,
            "num_images": 1,
            "output_format": "jpeg",
        },
        "workflow_allowlist": ["GEMSTONE_COLOR_CHANGE", "BACKGROUND_REPLACEMENT", "LUXURY_ENHANCEMENT"],
        "config": {"image_field": "image_urls", "max_reference_images": 10},
        "sort_order": 3,
        "cost_per_call": 0.07,
    },
    {
        "endpoint_id": "openai/gpt-image-2/edit",
        "display_name": "GPT Image 2 Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": GPT_IMAGE_2_PARAMS,
        "default_params": {"image_size": "auto", "quality": "high", "num_images": 1, "output_format": "png"},
        "workflow_allowlist": None,
        "config": {
            "image_field": "image_urls",
            "max_reference_images": 16,
            "recommended_max_prompt_chars": 12_000,
            "official_max_prompt_chars": 32_000,
            "official_prompt_status": "documented",
            "official_prompt_note": "OpenAI GPT Image 2: 32,000 characters",
        },
        "sort_order": 4,
        "cost_per_call": 0.08,
    },
    {
        "endpoint_id": "fal-ai/flux-2-pro/edit",
        "display_name": "FLUX 2 Pro Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True, "hex_matching": True},
        "input_schema": FLUX_2_PRO_PARAMS,
        "default_params": {
            "image_size": "auto",
            "safety_tolerance": "2",
            "enable_safety_checker": True,
            "num_images": 1,
            "output_format": "jpeg",
        },
        "workflow_allowlist": None,
        "config": {"image_field": "image_urls", "max_reference_images": 9},
        "sort_order": 5,
        "cost_per_call": 0.03,
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
            "enhance_prompt": False,
            "safety_tolerance": "2",
            "aspect_ratio": "1:1",
        },
        "workflow_allowlist": None,
        "config": {"image_field": "image_url", "max_reference_images": 1},
        "sort_order": 6,
        "cost_per_call": 0.04,
    },
    {
        "endpoint_id": "fal-ai/nano-banana-2/edit",
        "display_name": "Nano Banana 2 Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": NANO_BANANA_2_PARAMS,
        "default_params": {
            "resolution": "1K",
            "aspect_ratio": "auto",
            "num_images": 1,
            "output_format": "png",
            "safety_tolerance": "4",
            "limit_generations": True,
        },
        "workflow_allowlist": None,
        "config": {
            "image_field": "image_urls",
            "max_reference_images": 14,
            "recommended_max_prompt_chars": 3600,
            "official_prompt_status": "undocumented",
            "official_prompt_note": "Gemini / Nano Banana: no published character limit",
        },
        "sort_order": 7,
        "cost_per_call": 0.08,
    },
    {
        "endpoint_id": "fal-ai/gemini-3.1-flash-image-preview/edit",
        "display_name": "Gemini 3.1 Flash Image Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": GEMINI_3_1_FLASH_PARAMS,
        "default_params": {
            "resolution": "1K",
            "aspect_ratio": "auto",
            "num_images": 1,
            "output_format": "png",
            "safety_tolerance": "4",
            "limit_generations": True,
            "enable_web_search": False,
        },
        "workflow_allowlist": None,
        "config": {
            "image_field": "image_urls",
            "max_reference_images": 14,
            "recommended_max_prompt_chars": 3600,
            "official_prompt_status": "undocumented",
            "official_prompt_note": "Gemini / Nano Banana: no published character limit",
        },
        "sort_order": 8,
        "cost_per_call": 0.08,
    },
    {
        "endpoint_id": "fal-ai/nano-banana/edit",
        "display_name": "Nano Banana Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": NANO_BANANA_BASE_PARAMS,
        "default_params": {
            "aspect_ratio": "auto",
            "num_images": 1,
            "output_format": "png",
            "safety_tolerance": "4",
            "limit_generations": False,
        },
        "workflow_allowlist": None,
        "config": {
            "image_field": "image_urls",
            "max_reference_images": 14,
            "recommended_max_prompt_chars": 3600,
            "official_prompt_status": "undocumented",
            "official_prompt_note": "Gemini / Nano Banana: no published character limit",
        },
        "sort_order": 9,
        "cost_per_call": 0.039,
    },
    {
        "endpoint_id": "bytedance/seedream/v5/pro/edit",
        "display_name": "Seedream 5.0 Pro Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": SEEDREAM_V5_PRO_EDIT_PARAMS,
        "default_params": {
            "image_size": "auto_2K",
            "num_images": 1,
            "output_format": "jpeg",
            "enable_safety_checker": True,
        },
        "workflow_allowlist": None,
        "config": {"image_field": "image_urls", "max_reference_images": 10},
        "sort_order": 10,
        "cost_per_call": 0.0675,
    },
    {
        "endpoint_id": "fal-ai/bytedance/seedream/v5/lite/edit",
        "display_name": "Seedream 5.0 Lite Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": SEEDREAM_V5_LITE_EDIT_PARAMS,
        "default_params": {
            "image_size": "auto_2K",
            "num_images": 1,
            "max_images": 1,
            "enable_safety_checker": True,
        },
        "workflow_allowlist": None,
        "config": {"image_field": "image_urls", "max_reference_images": 10},
        "sort_order": 11,
        "cost_per_call": 0.035,
    },
    {
        "endpoint_id": "fal-ai/bytedance/seedream/v4.5/edit",
        "display_name": "Seedream 4.5 Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": SEEDREAM_V45_EDIT_PARAMS,
        "default_params": {
            "image_size": "auto_2K",
            "num_images": 1,
            "max_images": 1,
            "enable_safety_checker": True,
        },
        "workflow_allowlist": None,
        "config": {"image_field": "image_urls", "max_reference_images": 10},
        "sort_order": 12,
        "cost_per_call": 0.04,
    },
    {
        "endpoint_id": "fal-ai/gpt-image-1.5/edit",
        "display_name": "GPT Image 1.5 Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": GPT_IMAGE_1_5_PARAMS,
        "default_params": {
            "image_size": "1024x1024",
            "quality": "medium",
            "input_fidelity": "high",
            "background": "auto",
            "num_images": 1,
            "output_format": "png",
        },
        "workflow_allowlist": None,
        "config": {"image_field": "image_urls"},
        "sort_order": 13,
        "cost_per_call": 0.08,
    },
    {
        "endpoint_id": "fal-ai/flux-2/edit",
        "display_name": "FLUX 2 Dev Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True, "hex_matching": True},
        "input_schema": FLUX_2_DEV_EDIT_PARAMS,
        "default_params": {
            "image_size": "auto",
            "guidance_scale": 2.5,
            "num_inference_steps": 28,
            "acceleration": "regular",
            "num_images": 1,
            "output_format": "png",
        },
        "workflow_allowlist": None,
        "config": {"image_field": "image_urls", "max_reference_images": 4},
        "sort_order": 14,
        "cost_per_call": 0.012,
    },
    {
        "endpoint_id": "fal-ai/glm-image/image-to-image",
        "display_name": "GLM-Image I2I",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": GLM_IMAGE_PARAMS,
        "default_params": {
            "image_size": "square_hd",
            "num_inference_steps": 30,
            "guidance_scale": 1.5,
            "num_images": 1,
            "output_format": "jpeg",
        },
        "workflow_allowlist": None,
        "config": {"image_field": "image_urls", "max_reference_images": 4},
        "sort_order": 15,
        "cost_per_call": 0.05,
    },
    {
        "endpoint_id": "fal-ai/firered-image-edit-v1.1",
        "display_name": "FireRed Image Edit v1.1",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": FIRERED_EDIT_PARAMS,
        "default_params": {
            "image_size": "auto",
            "num_inference_steps": 30,
            "guidance_scale": 4,
            "acceleration": "regular",
            "num_images": 1,
            "output_format": "png",
        },
        "workflow_allowlist": None,
        "config": {"image_field": "image_urls"},
        "sort_order": 16,
        "cost_per_call": 0.0325,
    },
    {
        "endpoint_id": "xai/grok-imagine-image/edit",
        "display_name": "Grok Imagine Edit",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "multi_image": True},
        "input_schema": GROK_EDIT_PARAMS,
        "default_params": {"num_images": 1, "aspect_ratio": "auto", "resolution": "1k", "output_format": "jpeg"},
        "workflow_allowlist": None,
        "config": {"image_field": "image_urls", "max_reference_images": 3},
        "sort_order": 17,
        "cost_per_call": 0.022,
    },
    {
        "endpoint_id": "fal-ai/flux/dev/image-to-image",
        "display_name": "FLUX Dev I2I",
        "category": "image_to_image",
        "capabilities": {**IMAGE_EDIT_CAPS, "person_generation": False},
        "input_schema": FLUX_DEV_I2I_PARAMS,
        "default_params": {
            "strength": 0.85,
            "image_size": "square_hd",
            "guidance_scale": 3.5,
            "num_inference_steps": 40,
            "acceleration": "none",
            "num_images": 1,
            "output_format": "jpeg",
        },
        "workflow_allowlist": ["LUXURY_ENHANCEMENT"],
        "config": {"image_field": "image_url", "max_reference_images": 1},
        "sort_order": 18,
        "cost_per_call": 0.025,
    },
]

_VTON_MODELS: list[dict] = [
    {
        "endpoint_id": "decart/lucy2-vton/realtime",
        "display_name": "Lucy 2.1 Realtime VTON (WebRTC only)",
        "category": "virtual_try_on",
        "capabilities": {**VTON_CAPS, "realtime": True, "queue_compatible": False},
        "input_schema": LUCY2_VTON_PARAMS,
        "default_params": {
            "prompt": (
                "Substitute the current top with the outfit from the reference image, "
                "matching its color, material, and fit"
            ),
        },
        # Not used by async jobs.py — WebRTC realtime only. Hidden from Studio selectors.
        "workflow_allowlist": [],
        "config": {
            "input_mode": "try_on",
            "try_on_fields": {"person": "image_url", "product": "reference_image_url"},
            "product_image_index": 0,
            "person_image_index": 1,
            "min_images": 2,
            "realtime": True,
            "queue_compatible": False,
        },
        "sort_order": 99,
        "cost_per_call": 0.02,
        "is_active": False,
    },
    {
        "endpoint_id": "fal-ai/fashn/tryon/v1.6",
        "display_name": "FASHN Try-On v1.6",
        "category": "virtual_try_on",
        "capabilities": VTON_CAPS,
        "input_schema": FASHN_TRYON_PARAMS,
        "default_params": {
            "category": "auto",
            "garment_photo_type": "flat-lay",
            "mode": "balanced",
            "num_samples": 1,
        },
        "workflow_allowlist": ["VIRTUAL_TRY_ON", "JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"],
        "config": {
            "input_mode": "try_on",
            "try_on_fields": {"person": "model_image", "product": "garment_image"},
            "product_image_index": 0,
            "person_image_index": 1,
            "min_images": 2,
            "omit_prompt": True,
            "garment_only": True,
            "jewelry_warning": "FASHN does not support jewelry accessories — use Nano Banana Pro / GPT Image 2 for jewelry try-on.",
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
        "workflow_allowlist": ["VIRTUAL_TRY_ON", "JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"],
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
                "acceleration": {
                    "type": "string",
                    "title": "Acceleration",
                    "enum": ["none", "regular", "high"],
                    "default": "none",
                },
                "num_images": {"type": "integer", "title": "Images", "minimum": 1, "maximum": 4, "default": 1},
            },
        },
        "default_params": {"lora_scale": 1, "acceleration": "none", "num_images": 1},
        "workflow_allowlist": ["VIRTUAL_TRY_ON", "JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"],
        "config": {
            "input_mode": "try_on",
            "image_field": "image_urls",
            "try_on_image_order": ["person", "product"],
            "product_image_index": 0,
            "person_image_index": 1,
            "min_images": 2,
            "max_reference_images": 4,
            "garment_only": True,
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
        "workflow_allowlist": ["VIRTUAL_TRY_ON", "JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"],
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
        "workflow_allowlist": ["VIRTUAL_TRY_ON", "JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"],
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
        "workflow_allowlist": ["VIRTUAL_TRY_ON", "JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"],
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

_RAW_FAL_MODELS: list[dict] = _IMAGE_EDIT_MODELS + _VTON_MODELS

FAL_MODELS = [_enrich_model_spec(spec) for spec in _RAW_FAL_MODELS]
