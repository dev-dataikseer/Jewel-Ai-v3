"""Ranked model catalog metadata for Studio dropdown and admin reference."""

MODEL_INFO: dict[str, dict] = {
    "fal-ai/nano-banana-pro/edit": {
        "rank": 1,
        "model_category": "Dedicated Image Editing",
        "architecture": (
            "Google Gemini 3 Pro Image — multimodal foundation model with advanced reasoning. "
            "Plans composition, lighting, and spatial relationships before rendering. 1,219 Elo on T2I leaderboard."
        ),
        "key_strengths": (
            "Reasoning-based generation, semantic editing without masks, up to 14 reference images, "
            "character consistency, web search grounding, thinking mode, SynthID watermarking."
        ),
        "tags": "gemini-3-pro | google | reasoning | 14-reference | character-consistency | web-search",
        "pricing": "$0.15/image at 1K, 4K at 2x rate ($0.30)",
        "max_resolution": "4K (2048x2048)",
        "multi_image_support": "Up to 14 reference images",
        "aspect_ratios": "auto, 21:9, 16:9, 3:2, 4:3, 5:4, 1:1, 4:5, 3:4, 2:3, 9:16",
    },
    "fal-ai/flux-2-max/edit": {
        "rank": 2,
        "model_category": "Dedicated Image Editing",
        "architecture": (
            "32B Parameter Architecture — Mistral-3 24B vision-language model paired with a rectified flow "
            "transformer on latent image representations."
        ),
        "key_strengths": (
            "Multi-reference editing (up to 10 images), hex-color target isolation, pixel-level shape retention, "
            "native text/typography injection, 4MP output support."
        ),
        "tags": "flux-2 | max | 32B | rectified-flow | multi-reference | hex-color | typography",
        "pricing": "$0.07 per megapixel (first MP), $0.03 per additional MP",
        "max_resolution": "4MP (2048x2048)",
        "multi_image_support": "Up to 10 reference images",
        "aspect_ratios": "auto, square_hd, square, portrait_4_3, portrait_16_9, landscape_4_3, landscape_16_9",
    },
    "openai/gpt-image-2/edit": {
        "rank": 3,
        "model_category": "Dedicated Image Editing",
        "architecture": (
            "OpenAI GPT-Image-2 — natively multimodal reasoning-guided image model. "
            "1,339 Elo on Artificial Analysis T2I leaderboard (June 2026)."
        ),
        "key_strengths": (
            "Near-perfect text rendering (Latin/CJK), complex structural instruction following, "
            "mask-based inpainting support, flexible resolutions up to 4K."
        ),
        "tags": "gpt-image-2 | openai | multimodal | 1339-elo | mask-inpainting | 4K",
        "pricing": "From $0.005/image (1024x768, low) to $0.401 (3840x2160, high)",
        "max_resolution": "3840x2160 (8.3MP), max edge 3840px",
        "multi_image_support": "Multiple image URLs supported",
        "aspect_ratios": "Custom (multiples of 16, aspect ratio <= 3:1)",
    },
    "fal-ai/flux-2-pro/edit": {
        "rank": 4,
        "model_category": "Dedicated Image Editing",
        "architecture": (
            "Black Forest Labs FLUX.2 [pro] — 32B rectified flow transformer with zero-configuration production pipeline."
        ),
        "key_strengths": (
            "Zero configuration, JSON structured prompts, multi-reference editing (up to 9 images), "
            "HEX color code control, $0.03/MP pricing."
        ),
        "tags": "flux-2 | pro | 32B | zero-config | json-prompt | multi-reference | brand-colors",
        "pricing": "$0.03 per megapixel (first MP), $0.015 per additional MP",
        "max_resolution": "4MP (2048x2048)",
        "multi_image_support": "Up to 9 reference images",
        "aspect_ratios": "auto, square_hd, square, portrait_4_3, portrait_16_9, landscape_4_3, landscape_16_9",
    },
    "fal-ai/flux-pro/kontext": {
        "rank": 5,
        "model_category": "Standard Image-to-Image / Context-Aware",
        "architecture": (
            "Black Forest Labs FLUX.1 Kontext [pro] — 12B multimodal flow transformer for in-context editing."
        ),
        "key_strengths": (
            "Character consistency across iterative edits, typography editing, targeted local edits, "
            "style transfer, 8x faster than competing SOTA models."
        ),
        "tags": "flux-1 | kontext | 12B | character-consistency | typography | iterative-editing",
        "pricing": "$0.04 per image",
        "max_resolution": "1024x1024 (standard), aspect ratios 21:9 to 9:21",
        "multi_image_support": "Single image input (image_url)",
        "aspect_ratios": "21:9, 16:9, 4:3, 3:2, 1:1, 2:3, 3:4, 9:16, 9:21",
    },
    "fal-ai/nano-banana-2/edit": {
        "rank": 6,
        "model_category": "Dedicated Image Editing",
        "architecture": (
            "Google Gemini 3.1 Flash Image (Nano Banana 2) — fast-tier multimodal model with reasoning-guided generation."
        ),
        "key_strengths": (
            "Ultra-fast Flash-tier execution, up to 14 reference images, web search grounding, "
            "thinking mode, 4 resolution tiers (0.5K-4K), extreme aspect ratios."
        ),
        "tags": "gemini-3.1-flash | google | fast | 14-reference | web-search | thinking-mode",
        "pricing": "$0.06 (512px), $0.08 (1K), $0.12 (2K), $0.16 (4K); web search +$0.015",
        "max_resolution": "4K (2048x2048)",
        "multi_image_support": "Up to 14 reference images",
        "aspect_ratios": "auto, 21:9, 16:9, 3:2, 4:3, 5:4, 1:1, 4:5, 3:4, 2:3, 9:16",
    },
    "fal-ai/bytedance/seedream/v5/lite/edit": {
        "rank": 7,
        "model_category": "Dedicated Image Editing",
        "architecture": (
            "ByteDance Seedream 5.0 Lite — DiT with Chain of Thought reasoning pass before pixel generation."
        ),
        "key_strengths": (
            "Best resolution-to-cost ratio (up to 9MP at $0.035), 10 reference images, "
            "Figure-referencing syntax, batch up to 6 generations."
        ),
        "tags": "seedream-5 | bytedance | DiT | reasoning | figure-reference | high-resolution",
        "pricing": "$0.035 per image (regardless of resolution)",
        "max_resolution": "9MP (3072x3072)",
        "multi_image_support": "Up to 10 reference images",
        "aspect_ratios": "square_hd, square, portrait_4_3, portrait_16_9, landscape_4_3, landscape_16_9, auto_2K, auto_3K, auto_4K",
    },
    "fal-ai/bytedance/seedream/v4.5/edit": {
        "rank": 8,
        "model_category": "Dedicated Image Editing",
        "architecture": (
            "ByteDance Seedream 4.5 — unified single-architecture generation and editing model."
        ),
        "key_strengths": (
            "Multi-source composition (10 reference images), context-aware transformations, "
            "Figure-referencing syntax, up to 4MP output, $0.04 flat pricing."
        ),
        "tags": "seedream-4.5 | bytedance | unified-architecture | multi-source | figure-reference",
        "pricing": "$0.04 per image (flat rate)",
        "max_resolution": "4MP (2048x2048)",
        "multi_image_support": "Up to 10 reference images",
        "aspect_ratios": "square_hd, square, portrait_4_3, portrait_16_9, landscape_4_3, landscape_16_9, auto_2K, auto_4K",
    },
    "fal-ai/gpt-image-1.5/edit": {
        "rank": 9,
        "model_category": "Dedicated Image Editing",
        "architecture": (
            "OpenAI GPT Image 1.5 — natively multimodal model on GPT-5 architecture. "
            "4x faster inference and 20% lower cost vs GPT Image 1."
        ),
        "key_strengths": (
            "Three quality tiers, mask-based inpainting, transparent background support, "
            "input fidelity control, real-time streaming."
        ),
        "tags": "gpt-image-1.5 | openai | gpt-5 | mask-inpainting | transparent-bg | streaming",
        "pricing": "Low: $0.009/image, Medium: $0.034/image, High: $0.133/image (1024x1024)",
        "max_resolution": "1536x1024 / 1024x1536",
        "multi_image_support": "Up to 16 batched images",
        "aspect_ratios": "1024x1024, 1536x1024, 1024x1536",
    },
    "fal-ai/flux-2/edit": {
        "rank": 10,
        "model_category": "Dedicated Image Editing",
        "architecture": (
            "Black Forest Labs FLUX.2 [dev] — full 32B rectified flow transformer with adjustable parameters."
        ),
        "key_strengths": (
            "Full 32B model at $0.012/MP, hex color control, adjustable guidance_scale and steps, "
            "acceleration modes, prompt expansion."
        ),
        "tags": "flux-2 | dev | 32B | adjustable-params | hex-color | acceleration",
        "pricing": "$0.012 per megapixel",
        "max_resolution": "2048x2048 (4MP)",
        "multi_image_support": "Up to 4 reference images",
        "aspect_ratios": "square_hd, square, portrait_4_3, portrait_16_9, landscape_4_3, landscape_16_9",
    },
    "fal-ai/glm-image/image-to-image": {
        "rank": 11,
        "model_category": "Standard Image-to-Image",
        "architecture": (
            "Zhipu AI GLM-Image — 9B autoregressive generator + 7B diffusion decoder (single-stream DiT)."
        ),
        "key_strengths": (
            "Accurate embedded text rendering, semantic understanding + visual synthesis, "
            "up to 4 reference images, multilingual script support."
        ),
        "tags": "glm-4 | zhipu | hybrid-ar-diffusion | 9B-7B | text-rendering | multilingual",
        "pricing": "$0.05 per megapixel",
        "max_resolution": "2048x2048 (custom dims 512-2048, divisible by 32)",
        "multi_image_support": "Up to 4 reference images",
        "aspect_ratios": "square_hd, square, landscape_16_9, landscape_4_3, portrait_16_9, portrait_4_3",
    },
    "fal-ai/firered-image-edit-v1.1": {
        "rank": 12,
        "model_category": "Dedicated Image Editing",
        "architecture": (
            "FireRed Image Edit 1.1 — open-source editing model retrained from Qwen Image Edit 2509."
        ),
        "key_strengths": (
            "Bilingual instructions (English/Chinese), acceleration modes, negative prompt support, "
            "multi-image references for style transfer and VTO."
        ),
        "tags": "firered | open-source | qwen-base | bilingual | tunable | negative-prompt",
        "pricing": "$0.0325 per megapixel",
        "max_resolution": "Custom up to 2352x1760+",
        "multi_image_support": "Multiple image URLs (style transfer, virtual try-on)",
        "aspect_ratios": "square_hd, square, portrait_4_3, portrait_16_9, landscape_4_3, landscape_16_9",
    },
    "xai/grok-imagine-image/edit": {
        "rank": 13,
        "model_category": "Dedicated Image Editing",
        "architecture": (
            "xAI Grok Imagine — Aurora engine diffusion optimized for prompt adherence."
        ),
        "key_strengths": (
            "Lowest cost per edit ($0.022), fast batch processing, revised_prompt debugging field, "
            "1K/2K resolution tiers, wide aspect ratio support."
        ),
        "tags": "grok | xai | aurora | budget | fast-batch | revised-prompt",
        "pricing": "$0.022 per image ($0.02 output + $0.002 input)",
        "max_resolution": "2K (2048x2048)",
        "multi_image_support": "Up to 3 reference images",
        "aspect_ratios": "auto, 2:1, 20:9, 16:9, 4:3, 3:2, 1:1, 2:3, 3:4, 9:16, 1:2",
    },
    "fal-ai/flux/dev/image-to-image": {
        "rank": 14,
        "model_category": "Standard Image-to-Image",
        "architecture": (
            "Black Forest Labs FLUX.1 [dev] — 12B flow transformer with strength-based composition control."
        ),
        "key_strengths": (
            "Predictable composition mapping, massive LoRA ecosystem, strength parameter (0.01-1), "
            "acceleration modes, $0.025/MP pricing."
        ),
        "tags": "flux-1 | dev | 12B | flow-transformer | strength-based | lora-ecosystem",
        "pricing": "$0.025 per megapixel",
        "max_resolution": "Standard FLUX resolutions",
        "multi_image_support": "Single image (image_url)",
        "aspect_ratios": "square_hd, square, portrait_4_3, portrait_16_9, landscape_4_3, landscape_16_9",
    },
}
