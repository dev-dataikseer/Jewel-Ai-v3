# fal.ai Image-to-Image & Image Editing Model Registry
## Complete Technical Catalog — July 2026 Platform State

**Scope:** Every active Img2Img and Image Editing endpoint accessible through the fal.ai unified API ecosystem.  
**Filtering:** All models accept multimodal input (image + text prompt) and output a transformed/edited image. Pure T2I, I2V, and standalone CV utilities are excluded.  
**Coverage:** 14 models across 2 architectural classifications — 11 Dedicated Image Editing endpoints and 3 Standard Image-to-Image endpoints.

---

## Quick Reference: Model Classification Matrix

| Rank | Model | Endpoint | Category | Pricing | Max Resolution | Multi-Image |
|------|-------|----------|----------|---------|---------------|-------------|
| 1 | **FLUX.2 Max Edit** | `fal-ai/flux-2-max/edit` | Dedicated Editing | $0.07/MP | 4MP | 10 images |
| 2 | **GPT Image 2 Edit** | `openai/gpt-image-2/edit` | Dedicated Editing | $0.005-$0.401 | 3840x2160 | Multiple |
| 3 | **Nano Banana Pro Edit** | `fal-ai/nano-banana-pro/edit` | Dedicated Editing | $0.15/image | 4K | 14 images |
| 4 | **FLUX.2 Pro Edit** | `fal-ai/flux-2-pro/edit` | Dedicated Editing | $0.03/MP | 4MP | 9 images |
| 5 | **FLUX.1 Kontext Pro** | `fal-ai/flux-pro/kontext` | Std Img2Img / Context | $0.04/image | 1024x1024 | 1 image |
| 6 | **Nano Banana 2 Edit** | `fal-ai/nano-banana-2/edit` | Dedicated Editing | $0.06-$0.16 | 4K | 14 images |
| 7 | **Seedream 5.0 Lite Edit** | `fal-ai/bytedance/seedream/v5/lite/edit` | Dedicated Editing | $0.035/image | 3072x3072 | 10 images |
| 8 | **Seedream 4.5 Edit** | `fal-ai/bytedance/seedream/v4.5/edit` | Dedicated Editing | $0.04/image | 4MP | 10 images |
| 9 | **GPT Image 1.5 Edit** | `fal-ai/gpt-image-1.5/edit` | Dedicated Editing | $0.009-$0.133 | 1536x1024 | 16 images |
| 10 | **FLUX.2 [dev] Edit** | `fal-ai/flux-2/edit` | Dedicated Editing | $0.012/MP | 4MP | 4 images |
| 11 | **GLM-Image Image-to-Image** | `fal-ai/glm-image/image-to-image` | Std Img2Img | Per-MP | 2048x2048 | 4 images |
| 12 | **FireRed Image Edit v1.1** | `fal-ai/firered-image-edit-v1.1` | Dedicated Editing | $0.0325/MP | 2352x1760+ | Multiple |
| 13 | **Grok Imagine Edit** | `xai/grok-imagine-image/edit` | Dedicated Editing | $0.022/image | 2K | 3 images |
| 14 | **FLUX.1 [dev] Image-to-Image** | `fal-ai/flux/dev/image-to-image` | Std Img2Img | $0.025/MP | Standard | 1 image |

---

## Architecture Classification Overview

### Category A: Dedicated Image Editing / Instruction Endpoints
Models explicitly designed for localized edits, conversational text instructions, inpainting, or multi-reference composition. These endpoints do not expose a `strength` parameter; instead, they use natural language understanding to determine edit scope.

**Members (11):** FLUX.2 Max Edit, GPT Image 2 Edit, Nano Banana Pro Edit, FLUX.2 Pro Edit, Nano Banana 2 Edit, Seedream 5.0 Lite Edit, Seedream 4.5 Edit, GPT Image 1.5 Edit, FLUX.2 [dev] Edit, FireRed Image Edit v1.1, Grok Imagine Edit

### Category B: Standard Image-to-Image Endpoints
Built on latent diffusion/rectified flow structures where a structural image is transformed globally based on a `strength` or `denoising_strength` parameter. These expose lower-level diffusion controls (guidance_scale, num_inference_steps, strength).

**Members (3):** FLUX.1 Kontext Pro, GLM-Image Image-to-Image, FLUX.1 [dev] Image-to-Image

---

## Leaderboard Rankings & Benchmark Context

| Model | Artificial Analysis Elo | Text Rendering | Prompt Adherence | Speed | Cost Efficiency |
|-------|------------------------|----------------|------------------|-------|-----------------|
| GPT Image 2 | **1,339** [^3^] | Exceptional (Latin + CJK) | Near-perfect | Medium | Low-tier affordable |
| Nano Banana 2 | **1,260** [^3^] | Excellent (Hangul, etc.) | Strong | Very Fast | Good |
| Nano Banana Pro | **1,219** [^3^] | Excellent | Strong | Medium | Premium |
| FLUX.2 [max] | **1,192** [^3^] | Good (some menu blur) | Very Strong | Medium | Premium |
| FLUX.1 Kontext [pro] | Not ranked | Good | Strong (context-aware) | Fast | Excellent |
| Seedream 5.0 Lite | Not ranked | Good | Good | Medium | Excellent |
| Seedream 4.5 | Not ranked | Good | Good | ~60s | Good |
| GLM-Image | Not ranked | Strong (multilingual) | Good | Medium | Good |
| FireRed v1.1 | Not ranked | Good | Good | Tunable | Good |
| Grok Imagine | Not ranked | Moderate | Moderate | Fast | Best budget |
| GPT Image 1.5 | Not ranked | Strong | Strong | Fast | Variable tiers |

---

## Category A: Dedicated Image Editing Endpoints

---

### Rank 1. FLUX.2 Max Edit

* **API Path / Endpoint:** `fal-ai/flux-2-max/edit`
* **Category:** [Dedicated Image Editing]
* **Technical Summary:** FLUX.2 Max couples a **Mistral-3 24B vision-language model** with a **rectified flow transformer** operating on latent image representations, yielding a **32B parameter architecture** [^6^]. This is Black Forest Labs' highest-quality editing variant, delivering state-of-the-art photorealism with exceptional prompt adherence, fine detail, and natural lighting. The Max endpoint is purpose-built for professional production workflows requiring pixel-level precision.
* **Search / SDK Tags:** `flux-2` | `max` | `32B` | `rectified-flow` | `multi-reference` | `hex-color` | `typography`
* **Real Available API Parameters:**
  - `prompt` (string, *required*) — Text editing instruction. Supports `@image1`, `@image2` syntax for referencing specific inputs in multi-image workflows.
  - `image_urls` (list<string>, *required*) — Input image URLs. **Maximum 10 reference images**.
  - `image_size` (ImageSize | Enum, default: `auto`) — Output dimensions. Supports presets (`auto`, `square_hd`, `square`, `portrait_4_3`, `portrait_16_9`, `landscape_4_3`, `landscape_16_9`) or custom `{ width, height }` objects.
  - `seed` (integer) — Reproducibility seed. Same seed + prompt = deterministic output.
  - `num_images` (integer, default: `1`) — Number of output images to generate.
  - `output_format` (OutputFormatEnum, default: `jpeg`) — `jpeg` or `png`.
  - `sync_mode` (boolean, default: `false`) — Returns image as base64 data URI inline.
  - `safety_tolerance` (SafetyToleranceEnum, default: `"2"`) — Content moderation level, `1` (strictest) to `5` (most permissive).
  - `enable_safety_checker` (boolean, default: `true`) — Enable NSFW content filtering.

* **Pricing:** $0.07 per megapixel (first MP), $0.03 per additional MP [^6^]
* **Max Resolution:** 4 megapixels (2048x2048)
* **Multi-Image Support:** Up to 10 reference images with `@` referencing syntax
* **Unique Features:** HEX color code specification for brand consistency, pixel-level shape retention across edits, native typography injection

---

### Rank 2. GPT Image 2 Edit

* **API Path / Endpoint:** `openai/gpt-image-2/edit`
* **Category:** [Dedicated Image Editing]
* **Technical Summary:** OpenAI's latest multimodal reasoning-guided image model, **GPT-Image-2**, currently holds the **#1 position on the Artificial Analysis Text-to-Image leaderboard with 1,339 Elo** [^3^]. The architecture is a natively multimodal system that accepts both text and image inputs to produce image outputs. Its defining capability is near-perfect text rendering across both Latin and CJK scripts, making it the premier choice for typography-heavy editing workflows.
* **Search / SDK Tags:** `gpt-image-2` | `openai` | `multimodal` | `1339-elo` | `mask-inpainting` | `4K`
* **Real Available API Parameters:**
  - `prompt` (string, *required*) — Text description of the edit to apply.
  - `image_urls` (list<string>, *required*) — One or more reference image URLs to edit.
  - `image_size` (ImageSize | Enum, default: `auto`) — Output size. `auto` infers from input image. Supports presets (`square_hd`, `square`, `portrait_4_3`, `portrait_16_9`, `landscape_4_3`, `landscape_16_9`) or custom `{ width, height }` objects. Both dimensions must be multiples of 16, max edge 3840px, aspect ratio <= 3:1, total pixels between 655,360 and 8,294,400 [^24^].
  - `quality` (QualityEnum, default: `high`) — `low`, `medium`, or `high`. Trades cost against fidelity.
  - `num_images` (integer, default: `1`) — Number of edited images to generate.
  - `output_format` (OutputFormatEnum, default: `png`) — `jpeg`, `png`, or `webp`.
  - `sync_mode` (boolean, default: `false`) — Returns images as data URIs directly.
  - `mask_url` (string, *optional*) — URL of a mask image. White regions indicate areas to edit; enables precise inpainting.
  - `openai_api_key` (string, *optional*) — Your OpenAI API key for BYOK usage.

* **Pricing:** From $0.005/image (1024x768, low quality) to $0.401 (3840x2160, high quality) [^3^]
* **Max Resolution:** 3840x2160 (8.3MP), max edge 3840px
* **Multi-Image Support:** Multiple image URLs supported
* **Unique Features:** Mask-based inpainting, transparent background support (PNG/WebP), BYOK routing through OpenAI quota, quality tier system for cost control

---

### Rank 3. Nano Banana Pro Edit

* **API Path / Endpoint:** `fal-ai/nano-banana-pro/edit`
* **Category:** [Dedicated Image Editing]
* **Technical Summary:** Google's **Gemini 3 Pro Image** architecture, marketed as Nano Banana Pro on fal.ai. This is a **multimodal foundation model with advanced reasoning capabilities** that plans composition, lighting, spatial relationships, and element placement before rendering a single pixel [^1^][^2^]. The model carries a **1,219 Elo** on the Artificial Analysis leaderboard and trades raw speed for deeper reasoning and semantic awareness. All outputs carry SynthID digital watermarking.
* **Search / SDK Tags:** `gemini-3-pro` | `google` | `reasoning` | `14-reference` | `character-consistency` | `web-search`
* **Real Available API Parameters:**
  - `prompt` (string, *required*) — Text editing instruction.
  - `image_urls` (list<string>, *required*) — Input image URLs. **Maximum 14 reference images**.
  - `resolution` (ResolutionEnum, default: `"1K"`) — Output resolution tier: `1K`, `2K`, or `4K`. 4K charged at 2x rate.
  - `aspect_ratio` (Enum, default: `auto`) — `auto`, `21:9`, `16:9`, `3:2`, `4:3`, `5:4`, `1:1`, `4:5`, `3:4`, `2:3`, `9:16`.
  - `num_images` (integer, default: `1`) — Batch size, range **1-4**.
  - `seed` (integer) — Random seed for reproducibility.
  - `output_format` (OutputFormatEnum, default: `png`) — `jpeg`, `png`, or `webp`.
  - `sync_mode` (boolean, default: `false`) — Return data URI.
  - `safety_tolerance` (SafetyToleranceEnum, default: `"4"`) — Content moderation, `1` (strictest) to `6` (most permissive).
  - `system_prompt` (string, default: `""`) — System instruction that steers model persona and output style.
  - `enable_web_search` (boolean) — Enable real-time web search for visual grounding.
  - `limit_generations` (boolean) — Limit generations per prompt round to 1.

* **Pricing:** $0.15/image at 1K; 4K outputs at $0.30/image (2x rate) [^1^]
* **Max Resolution:** 4K (2048x2048)
* **Multi-Image Support:** Up to 14 reference images (joint-highest capacity)
* **Unique Features:** Web search grounding (+$0.015), thinking mode (+$0.002), character consistency for 5+ people, SynthID watermarking on all outputs

---

### Rank 4. FLUX.2 Pro Edit

* **API Path / Endpoint:** `fal-ai/flux-2-pro/edit`
* **Category:** [Dedicated Image Editing]
* **Technical Summary:** Black Forest Labs' **FLUX.2 [pro]** editing endpoint shares the same **32B rectified flow transformer backbone** as Max, but is optimized for zero-configuration production workflows [^35^]. The defining characteristic is the absence of tunable guidance_scale and num_inference_steps — internal optimizations produce consistent, predictable output quality across runs. Supports JSON structured prompts for granular control over scene elements, subjects, camera settings, and color palettes.
* **Search / SDK Tags:** `flux-2` | `pro` | `32B` | `zero-config` | `json-prompt` | `multi-reference` | `brand-colors`
* **Real Available API Parameters:**
  - `prompt` (string, *required*) — Text editing instruction. Supports `@image1`, `@image2` positional referencing for multi-image compositing.
  - `image_urls` (list<string>, *required*) — Input image URLs for editing.
  - `image_size` (ImageSize | Enum, default: `auto`) — `auto`, `square_hd`, `square`, `portrait_4_3`, `portrait_16_9`, `landscape_4_3`, `landscape_16_9`, or custom `{ width, height }`.
  - `seed` (integer) — Reproducibility seed.
  - `num_images` (integer, default: `1`) — Output count.
  - `output_format` (OutputFormatEnum, default: `jpeg`) — `jpeg` or `png`.
  - `sync_mode` (boolean, default: `false`) — Data URI return mode.
  - `safety_tolerance` (SafetyToleranceEnum, default: `"2"`) — `1` to `5`.
  - `enable_safety_checker` (boolean, default: `true`) — NSFW filtering.

* **Pricing:** $0.03 per megapixel (first MP), $0.015 per additional MP of input+output [^37^]
* **Max Resolution:** 4MP (2048x2048)
* **Multi-Image Support:** Up to 9 reference images (9MP total input)
* **Unique Features:** JSON structured prompt syntax, zero configuration (no guidance/steps), HEX color code control for brand consistency, pixel-for-pixel context preservation

---

### Rank 6. Nano Banana 2 Edit

* **API Path / Endpoint:** `fal-ai/nano-banana-2/edit`
* **Category:** [Dedicated Image Editing]
* **Technical Summary:** Google's **Gemini 3.1 Flash Image** model, marketed as Nano Banana 2 on fal.ai. Built for speed and vibrant output with reasoning-guided generation at Flash-tier inference speeds [^38^][^42^]. While Pro prioritizes reasoning depth, Nano Banana 2 prioritizes iteration velocity — delivering semantic edits in seconds rather than minutes. Supports the same 14-reference-image pipeline as Pro but at significantly lower cost.
* **Search / SDK Tags:** `gemini-3.1-flash` | `google` | `fast` | `14-reference` | `web-search` | `thinking-mode`
* **Real Available API Parameters:**
  - `prompt` (string, *required*) — Editing instruction.
  - `image_urls` (list<string>, *required*) — Input images, max 14.
  - `resolution` (ResolutionEnum, default: `"1K"`) — `0.5K`, `1K`, `2K`, `4K`.
  - `aspect_ratio` (Enum, default: `auto`) — Full range including `21:9` and `9:16`.
  - `num_images` (integer, default: `1`) — Batch 1-4.
  - `seed` (integer) — Reproducibility seed.
  - `output_format` (OutputFormatEnum, default: `png`) — `jpeg`, `png`, `webp`.
  - `sync_mode` (boolean, default: `false`).
  - `safety_tolerance` (SafetyToleranceEnum, default: `"4"`) — `1` to `6`.
  - `enable_web_search` (boolean) — Web grounding for current visual references.
  - `limit_generations` (boolean) — Cap generations at 1 per round.
  - `system_prompt` (string) — Style/persona steering.

* **Pricing:** $0.06 (512px), $0.08 (1K), $0.12 (2K), $0.16 (4K); web search +$0.015 [^37^]
* **Max Resolution:** 4K (2048x2048)
* **Multi-Image Support:** Up to 14 reference images
* **Unique Features:** Four resolution tiers (0.5K-4K), extreme aspect ratios (21:9, 9:21), Flash-tier speed, web search + thinking mode

---

### Rank 7. Seedream 5.0 Lite Edit

* **API Path / Endpoint:** `fal-ai/bytedance/seedream/v5/lite/edit`
* **Category:** [Dedicated Image Editing]
* **Technical Summary:** ByteDance's **Seedream 5.0 Lite** is built on a **Diffusion Transformer (DiT) architecture** with a high-compression VAE and a **Chain of Thought reasoning pass** that evaluates spatial relationships, physical plausibility, and domain knowledge before pixel generation [^48^]. The editing endpoint uses Figure-referencing syntax (`"replace product in Figure 1 with that in Figure 2"`) for intuitive multi-source composition. API is deliberately minimal — no guidance scale, inference steps, or seed controls.
* **Search / SDK Tags:** `seedream-5` | `bytedance` | `DiT` | `reasoning` | `figure-reference` | `high-resolution`
* **Real Available API Parameters:**
  - `prompt` (string, *required*) — Editing instruction using Figure-referencing syntax.
  - `image_urls` (list<string>, *required*) — Input images, **maximum 10**. Excess images use last 10.
  - `image_size` (ImageSize | Enum, default: `auto_2K`) — `square_hd`, `square`, `portrait_4_3`, `portrait_16_9`, `landscape_4_3`, `landscape_16_9`, `auto_2K`, `auto_3K`, `auto_4K`. Total pixels must be between 2560x1440 and 4096x4096 [^45^].
  - `num_images` (integer, default: `1`) — Separate generation runs, range 1-6.
  - `max_images` (integer, default: `1`) — Multi-image output per generation.
  - `sync_mode` (boolean, default: `false`).
  - `enable_safety_checker` (boolean, default: `true`) — Content filtering.

* **Pricing:** $0.035 per image (flat rate, regardless of resolution) [^48^]
* **Max Resolution:** 9MP (3072x3072)
* **Multi-Image Support:** Up to 10 reference images with Figure-referencing
* **Unique Features:** Best resolution-to-cost ratio, batch up to 6 generations per call, no tuning parameters (model handles internally)

---

### Rank 8. Seedream 4.5 Edit

* **API Path / Endpoint:** `fal-ai/bytedance/seedream/v4.5/edit`
* **Category:** [Dedicated Image Editing]
* **Technical Summary:** ByteDance's **Seedream 4.5** consolidates image generation and editing into a **unified single-architecture model** [^23^][^31^]. The editing endpoint interprets spatial references directly from natural language prompts without requiring layer masks or selection tools. Processes up to 10 reference images simultaneously for complex multi-source compositions like product swaps, text overlay copying, and element positioning.
* **Search / SDK Tags:** `seedream-4.5` | `bytedance` | `unified-architecture` | `multi-source` | `figure-reference`
* **Real Available API Parameters:**
  - `prompt` (string, *required*) — Natural language edit instruction with spatial references.
  - `image_urls` (list<string>, *required*) — Input images, **maximum 10**.
  - `image_size` (ImageSize | Enum, default: `auto_2K`) — `square_hd`, `square`, `portrait_4_3`, `portrait_16_9`, `landscape_4_3`, `landscape_16_9`, `auto_2K`, `auto_4K`. Dimensions 1920-4096px per axis [^23^].
  - `num_images` (integer, default: `1`) — Separate generations, range 1-6.
  - `max_images` (integer, default: `1`) — Multi-output per generation.
  - `sync_mode` (boolean, default: `false`).
  - `enable_safety_checker` (boolean, default: `true`).

* **Pricing:** $0.04 per image (flat rate) [^31^]
* **Max Resolution:** 4MP (2048x2048), configurable 1920-4096px per axis
* **Multi-Image Support:** Up to 10 reference images
* **Unique Features:** Unified generation-editing architecture (no endpoint switching), context-aware depth/perspective/lighting preservation

---

### Rank 9. GPT Image 1.5 Edit

* **API Path / Endpoint:** `fal-ai/gpt-image-1.5/edit`
* **Category:** [Dedicated Image Editing]
* **Technical Summary:** OpenAI's **GPT Image 1.5**, built on the GPT-5 architecture, is a natively multimodal model that generates and edits production-quality images with superior prompt adherence and precise text rendering [^51^][^56^]. The successor to GPT Image 1 runs up to **4x faster** and costs **20% less**. The editing endpoint supports mask-based inpainting, transparent backgrounds, and input fidelity control for facial feature preservation.
* **Search / SDK Tags:** `gpt-image-1.5` | `openai` | `gpt-5` | `mask-inpainting` | `transparent-bg` | `streaming`
* **Real Available API Parameters:**
  - `prompt` (string, *required*) — Editing instruction.
  - `image_urls` (list<string>, *required*) — Reference image URLs.
  - `image_size` (ImageSizeEnum, default: `auto`) — `auto`, `1024x1024`, `1536x1024`, `1024x1536`.
  - `background` (BackgroundEnum, default: `auto`) — `auto`, `transparent`, `opaque`.
  - `quality` (QualityEnum, default: `high`) — `low`, `medium`, `high`. Variable cost tiers.
  - `input_fidelity` (InputFidelityEnum, default: `high`) — `low` or `high`. Controls effort to match input style/features, especially faces.
  - `num_images` (integer, default: `1`) — Range 1-4.
  - `output_format` (OutputFormatEnum, default: `png`) — `jpeg`, `png`, `webp`.
  - `sync_mode` (boolean, default: `false`).
  - `mask_image_url` (string) — Mask for inpainting. White regions = edit area.

* **Pricing:** Low: $0.009/image, Medium: $0.034/image, High: $0.133/image (1024x1024) [^56^]
* **Max Resolution:** 1536x1024 / 1024x1536
* **Multi-Image Support:** Up to 16 batched images
* **Unique Features:** Three quality tiers for cost control, transparent background support, input fidelity for face preservation, real-time streaming support

---

### Rank 10. FLUX.2 [dev] Edit

* **API Path / Endpoint:** `fal-ai/flux-2/edit`
* **Category:** [Dedicated Image Editing]
* **Technical Summary:** The **FLUX.2 [dev]** editing endpoint exposes the full **32B rectified flow transformer** with adjustable parameters for developers who need fine-grained control [^46^]. Unlike Pro (zero-config), the Dev endpoint exposes `guidance_scale`, `num_inference_steps`, and `acceleration` modes. This is the same 32B backbone as Max/Pro but at the lowest per-megapixel price point in the FLUX.2 family.
* **Search / SDK Tags:** `flux-2` | `dev` | `32B` | `adjustable-params` | `hex-color` | `acceleration`
* **Real Available API Parameters:**
  - `prompt` (string, *required*) — Editing instruction.
  - `image_urls` (list<string>, *required*) — Input images, **maximum 4**. Excess images use first 4 only.
  - `guidance_scale` (float, default: `2.5`) — CFG scale controlling prompt adherence.
  - `num_inference_steps` (integer, default: `28`) — Denoising steps.
  - `image_size` (ImageSize | Enum) — `square_hd`, `square`, `portrait_4_3`, `portrait_16_9`, `landscape_4_3`, `landscape_16_9`, or custom `{ width, height }` (512-2048px).
  - `seed` (integer) — Reproducibility seed.
  - `num_images` (integer, default: `1`) — Output count.
  - `acceleration` (AccelerationEnum, default: `regular`) — `none`, `regular`, `high`.
  - `enable_prompt_expansion` (boolean) — LLM prompt enhancement for better results.
  - `sync_mode` (boolean, default: `false`).
  - `enable_safety_checker` (boolean, default: `true`).
  - `output_format` (OutputFormatEnum, default: `png`) — `jpeg`, `png`, `webp`.

* **Pricing:** $0.012 per megapixel [^6^]
* **Max Resolution:** 2048x2048 (4MP)
* **Multi-Image Support:** Up to 4 reference images
* **Unique Features:** Full parameter control on 32B model, acceleration modes for speed/quality tradeoff, prompt expansion, lowest-cost FLUX.2 editing

---

### Rank 12. FireRed Image Edit v1.1

* **API Path / Endpoint:** `fal-ai/firered-image-edit-v1.1`
* **Category:** [Dedicated Image Editing]
* **Technical Summary:** **FireRed Image Edit 1.1** is an open-source editing model retrained from **Qwen Image Edit 2509** [^53^][^55^]. It provides enhanced identity consistency, portrait makeup capabilities, and multi-element fusion. The model offers unique tunable acceleration modes and bilingual instruction support (English and Chinese), making it the most customizable editing pipeline on fal.ai for developers who need direct control over inference parameters.
* **Search / SDK Tags:** `firered` | `open-source` | `qwen-base` | `bilingual` | `tunable` | `negative-prompt`
* **Real Available API Parameters:**
  - `prompt` (string, *required*) — Editing instruction (English or Chinese).
  - `image_urls` (list<string>, *required*) — Input image URLs. Supports multi-image for style transfer, virtual try-on.
  - `image_size` (ImageSize | Enum) — `square_hd`, `square`, `portrait_4_3`, `portrait_16_9`, `landscape_4_3`, `landscape_16_9`, or custom `{ width, height }`.
  - `num_inference_steps` (integer, default: `30`) — Quality steps. Reduce below 20 for speed at detail cost.
  - `guidance_scale` (float, default: `4`) — CFG adherence. Higher = more literal prompt following.
  - `seed` (integer) — Reproducibility seed.
  - `num_images` (integer, default: `1`) — Output count.
  - `negative_prompt` (string, default: `""`) — Elements to explicitly exclude from output.
  - `acceleration` (AccelerationEnum, default: `regular`) — `none` (max quality), `regular` (balanced), `high` (speed priority).
  - `sync_mode` (boolean, default: `false`).
  - `enable_safety_checker` (boolean, default: `true`).
  - `output_format` (OutputFormatEnum, default: `png`) — `jpeg`, `png`.

* **Pricing:** $0.0325 per megapixel [^37^]
* **Max Resolution:** Custom up to 2352x1760+
* **Multi-Image Support:** Multiple image URLs (style transfer, VTO workflows)
* **Unique Features:** Open-source weights, negative prompt support, three acceleration modes, bilingual instructions, Agent module for 3+ image auto-preprocessing [^55^]

---

### Rank 13. Grok Imagine Edit

* **API Path / Endpoint:** `xai/grok-imagine-image/edit`
* **Category:** [Dedicated Image Editing]
* **Technical Summary:** xAI's **Grok Imagine** editing model, powered by the **Aurora engine** using a concentrated diffusion architecture [^66^][^67^]. The model bridges semantic understanding and visual synthesis through alignment between latent visual space and conversational language patterns. At **$0.022 per image**, it is the most cost-effective editing option on fal.ai for high-volume workflows.
* **Search / SDK Tags:** `grok` | `xai` | `aurora` | `budget` | `fast-batch` | `revised-prompt`
* **Real Available API Parameters:**
  - `prompt` (string, *required*) — Text description of desired edit.
  - `image_urls` (list<string>) — Input images, **maximum 3**.
  - `num_images` (integer, default: `1`) — Range 1-4.
  - `aspect_ratio` (AspectRatioEnum, default: `auto`) — `auto`, `2:1`, `20:9`, `19.5:9`, `16:9`, `4:3`, `3:2`, `1:1`, `2:3`, `3:4`, `9:16`, `9:19.5`, `9:20`, `1:2`. `auto` preserves input aspect ratio.
  - `resolution` (ResolutionEnum, default: `"1k"`) — `1k` (standard) or `2k` (high).
  - `output_format` (OutputFormatEnum, default: `jpeg`) — `jpeg`, `png`, `webp`.
  - `sync_mode` (boolean, default: `false`).

* **Pricing:** $0.022 per image ($0.02 output + $0.002 input) [^67^]
* **Max Resolution:** 2K (2048x2048)
* **Multi-Image Support:** Up to 3 reference images
* **Unique Features:** `revised_prompt` field for debugging prompt interpretation, widest aspect ratio selection (13 options), cheapest per-edit cost

---

## Category B: Standard Image-to-Image Endpoints

---

### Rank 5. FLUX.1 Kontext Pro

* **API Path / Endpoint:** `fal-ai/flux-pro/kontext`
* **Category:** [Standard Image-to-Image / Context-Aware]
* **Technical Summary:** Black Forest Labs' **FLUX.1 Kontext [pro]** is a **12B parameter multimodal flow transformer** designed specifically for in-context image generation and editing [^14^][^15^]. Unlike standard Img2Img models that use a `strength` parameter, Kontext uses text-and-image conditioning to make targeted local edits while preserving global context. It is the pioneer of iterative editing — allowing users to build upon previous edits through multiple turns while maintaining characters, identities, and styles.
* **Search / SDK Tags:** `flux-1` | `kontext` | `12B` | `character-consistency` | `typography` | `iterative-editing`
* **Real Available API Parameters:**
  - `prompt` (string, *required*) — Editing instruction.
  - `image_url` (string, *required*) — Input image URL (single image only).
  - `guidance_scale` (float, default: `3.5`) — CFG scale, range **1-20**.
  - `num_inference_steps` (integer) — Generation denoising steps.
  - `seed` (integer) — Reproducibility seed.
  - `num_images` (integer, default: `1`) — Range **1-4**.
  - `output_format` (OutputFormatEnum, default: `jpeg`) — `jpeg`, `png`.
  - `sync_mode` (boolean, default: `false`).
  - `aspect_ratio` (Enum) — `21:9`, `16:9`, `4:3`, `3:2`, `1:1`, `2:3`, `3:4`, `9:16`, `9:21`.
  - `safety_tolerance` (SafetyToleranceEnum, default: `"2"`) — `1` to `6`.
  - `enhance_prompt` (boolean, default: `false`) — LLM prompt enhancement for vague instructions.

* **Pricing:** $0.04 per image [^14^]
* **Max Resolution:** 1024x1024 standard, aspect ratios 21:9 to 9:21
* **Multi-Image Support:** Single image input only (iterative refinement workflow)
* **Unique Features:** Best character consistency across multiple editing rounds, typography editing (signs/labels/posters), 8x faster than previous SOTA, enhance_prompt for vague instructions

---

### Rank 11. GLM-Image Image-to-Image

* **API Path / Endpoint:** `fal-ai/glm-image/image-to-image`
* **Category:** [Standard Image-to-Image]
* **Technical Summary:** **GLM-Image** by Zhipu AI uses a **hybrid autoregressive + diffusion architecture**: a **9B-parameter autoregressive generator** (initialized from GLM-4-9B) handles semantic understanding and text layout, while a **7B-parameter diffusion decoder** synthesizes visual details through a single-stream DiT [^27^]. This hybrid approach overcomes the long-range spatial dependency limitations of pure diffusion models, enabling accurate embedded text rendering and multilingual script support.
* **Search / SDK Tags:** `glm-4` | `zhipu` | `hybrid-ar-diffusion` | `9B-7B` | `text-rendering` | `multilingual`
* **Real Available API Parameters:**
  - `prompt` (string, *required*) — Editing or style transfer instruction.
  - `image_urls` (list<string>, *required*) — Reference images, **maximum 4**. First image serves as primary subject; additional images provide style/compositional guidance.
  - `image_size` (enum | object, default: `square_hd`) — `square_hd`, `square`, `landscape_16_9`, `landscape_4_3`, `landscape_3_2`, `landscape_hd`, `portrait_16_9`, `portrait_4_3`, `portrait_3_2`, `portrait_hd`, or custom `{ width, height }` (512-2048, divisible by 32).
  - `num_inference_steps` (integer, default: `30`) — Denoising steps, range **10-100**.
  - `guidance_scale` (float, default: `1.5`) — CFG scale. **Lower than typical diffusion models** because the AR component provides semantic guidance.
  - `seed` (integer) — Reproducibility seed.
  - `num_images` (integer, default: `1`) — Batch size **1-4**.
  - `enable_safety_checker` (boolean, default: `true`) — NSFW filtering.
  - `output_format` (enum, default: `jpeg`) — `jpeg`, `png`.
  - `sync_mode` (boolean, default: `false`).
  - `enable_prompt_expansion` (boolean, default: `false`) — LLM prompt enhancement.

* **Pricing:** Competitive per-megapixel pricing
* **Max Resolution:** 2048x2048 (custom dims 512-2048, divisible by 32)
* **Multi-Image Support:** Up to 4 reference images
* **Unique Features:** Hybrid AR+diffusion architecture for text accuracy, lower guidance_scale default (1.5), high temperature sampling (0.9-0.95) — use seed for reproducibility

---

### Rank 14. FLUX.1 [dev] Image-to-Image

* **API Path / Endpoint:** `fal-ai/flux/dev/image-to-image`
* **Category:** [Standard Image-to-Image]
* **Technical Summary:** The foundational **FLUX.1 [dev]** Image-to-Image endpoint is a **12B parameter flow transformer** that uses a `strength` parameter to control the denoising process [^36^]. At `strength=0.95` (default), the model preserves composition while applying the prompt-driven transformation. Lower values preserve more of the original; higher values produce more dramatic changes. This endpoint has the largest community LoRA ecosystem support of any FLUX model.
* **Search / SDK Tags:** `flux-1` | `dev` | `12B` | `flow-transformer` | `strength-based` | `lora-ecosystem`
* **Real Available API Parameters:**
  - `prompt` (string, *required*) — Transformation prompt.
  - `image_url` (string, *required*) — Source image URL.
  - `strength` (float, default: `0.95`) — Denoising strength, range **0.01 to 1**. Higher = more transformation, less original preserved.
  - `num_inference_steps` (integer, default: `40`) — Denoising steps, range **10-50**.
  - `guidance_scale` (float, default: `3.5`) — CFG scale, range **1-20**.
  - `seed` (integer) — Reproducibility seed.
  - `num_images` (integer, default: `1`) — Range **1-4**.
  - `sync_mode` (boolean, default: `false`).
  - `enable_safety_checker` (boolean, default: `true`).
  - `output_format` (OutputFormatEnum, default: `jpeg`) — `jpeg`, `png`.
  - `acceleration` (AccelerationEnum, default: `none`) — `none`, `regular`, `high`.

* **Pricing:** $0.025 per megapixel [^36^]
* **Max Resolution:** Standard FLUX resolutions
* **Multi-Image Support:** Single image input
* **Unique Features:** `strength` parameter for granular composition control, massive LoRA ecosystem, three acceleration modes, most mature FLUX Img2Img endpoint

---

## Python SDK Integration Guide

### Installation

```bash
pip install fal-client
```

Set your API key:

```bash
export FAL_KEY="your-fal-api-key"
```

### Pattern A: Dedicated Editing (Natural Language Instructions)

Use this pattern for models that accept conversational edit instructions:

```python
import fal_client

def edit_image_dedicated(
    endpoint: str,
    prompt: str,
    image_urls: list[str],
    **kwargs
) -> dict:
    """
    Generic caller for Dedicated Image Editing endpoints.
    Works with: FLUX.2 Max, GPT Image 2, Nano Banana Pro, FLUX.2 Pro,
                Nano Banana 2, Seedream 5.0/4.5, GPT Image 1.5,
                FLUX.2 dev, FireRed, Grok Imagine
    """
    arguments = {
        "prompt": prompt,
        "image_urls": image_urls,
        **kwargs
    }
    
    result = fal_client.subscribe(
        endpoint,
        arguments=arguments,
        with_logs=True,
    )
    return result

# --- Example: FLUX.2 Max Edit ---
result = edit_image_dedicated(
    endpoint="fal-ai/flux-2-max/edit",
    prompt="Change the car color to midnight blue while maintaining reflections",
    image_urls=["https://example.com/car-photo.jpg"],
    num_images=1,
    output_format="png",
)
print(result["images"][0]["url"])

# --- Example: Nano Banana Pro Edit (multi-reference) ---
result = edit_image_dedicated(
    endpoint="fal-ai/nano-banana-pro/edit",
    prompt="Make a photo of the man driving the car down the california coastline",
    image_urls=[
        "https://example.com/man-portrait.jpg",
        "https://example.com/car-interior.jpg",
    ],
    resolution="2K",
    aspect_ratio="16:9",
    num_images=2,
)

# --- Example: Seedream 5.0 Lite Edit (Figure-referencing) ---
result = edit_image_dedicated(
    endpoint="fal-ai/bytedance/seedream/v5/lite/edit",
    prompt="Replace the product in Figure 1 with that in Figure 2. Keep the background.",
    image_urls=[
        "https://example.com/original-product.jpg",  # Figure 1
        "https://example.com/new-product.jpg",        # Figure 2
    ],
    image_size="auto_2K",
    num_images=1,
)
```

### Pattern B: Standard Image-to-Image (Strength-Based)

Use this pattern for models that expose `strength`, `guidance_scale`, and `num_inference_steps`:

```python
import fal_client

def edit_image_standard(
    endpoint: str,
    prompt: str,
    image_url: str,
    strength: float = 0.95,
    guidance_scale: float = 3.5,
    num_inference_steps: int = 40,
    **kwargs
) -> dict:
    """
    Generic caller for Standard Image-to-Image endpoints.
    Works with: FLUX.1 dev Img2Img, FLUX.1 Kontext Pro, GLM-Image Img2Img
    """
    arguments = {
        "prompt": prompt,
        "image_url": image_url,
        "strength": strength,
        "guidance_scale": guidance_scale,
        "num_inference_steps": num_inference_steps,
        **kwargs
    }
    
    result = fal_client.subscribe(
        endpoint,
        arguments=arguments,
        with_logs=True,
    )
    return result

# --- Example: FLUX.1 dev Image-to-Image (subtle style transfer) ---
result = edit_image_standard(
    endpoint="fal-ai/flux/dev/image-to-image",
    prompt="Transform to oil painting with visible brushstrokes and rich color depth",
    image_url="https://example.com/photo.jpg",
    strength=0.75,           # Lower = preserve more original
    guidance_scale=3.5,
    num_inference_steps=28,
    acceleration="regular",
)

# --- Example: FLUX.1 Kontext Pro (iterative character editing) ---
result = fal_client.subscribe(
    "fal-ai/flux-pro/kontext",
    arguments={
        "prompt": "Change the background to a sunset beach while keeping the person identical",
        "image_url": "https://example.com/portrait.jpg",
        "guidance_scale": 3.5,
        "num_inference_steps": 28,
        "aspect_ratio": "3:4",
    },
    with_logs=True,
)

# --- Example: GLM-Image Image-to-Image (text-accurate editing) ---
result = fal_client.subscribe(
    "fal-ai/glm-image/image-to-image",
    arguments={
        "prompt": "Apply watercolor style while preserving the subject and all text",
        "image_urls": ["https://example.com/poster.jpg"],
        "guidance_scale": 1.5,   # Lower default for AR-guided model
        "num_inference_steps": 35,
        "enable_prompt_expansion": True,
    },
    with_logs=True,
)
```

### Pattern C: FireRed Edit (Full Parameter Control)

```python
import fal_client

# FireRed offers the most tunable parameter set including negative_prompt
result = fal_client.subscribe(
    "fal-ai/firered-image-edit-v1.1",
    arguments={
        "prompt": "Transform into romantic Parisian evening style with soft smoky eye makeup",
        "image_urls": ["https://example.com/portrait.jpg"],
        "negative_prompt": "harsh lighting, overexposed, blurry",
        "guidance_scale": 4,
        "num_inference_steps": 30,
        "acceleration": "regular",  # none, regular, high
        "output_format": "png",
    },
    with_logs=True,
)
```

### Pattern D: GPT Image 1.5/2 Edit (Quality Tiers & Masking)

```python
import fal_client

# GPT Image 1.5 with mask-based inpainting
result = fal_client.subscribe(
    "fal-ai/gpt-image-1.5/edit",
    arguments={
        "prompt": "Add a red scarf to the person",
        "image_urls": ["https://example.com/person.jpg"],
        "mask_image_url": "https://example.com/mask.png",  # White = edit area
        "quality": "high",
        "input_fidelity": "high",  # Preserve facial features
        "background": "auto",
        "output_format": "png",
    },
    with_logs=True,
)

# GPT Image 2 (latest, highest quality)
result = fal_client.subscribe(
    "openai/gpt-image-2/edit",
    arguments={
        "prompt": "Change the menu prices to 2026 rates, keep all text crisp",
        "image_urls": ["https://example.com/menu.jpg"],
        "quality": "high",
        "image_size": "auto",
        "output_format": "png",
    },
    with_logs=True,
)
```

### Streaming for Real-Time Workflows

Both GPT Image 2 and FLUX.2 [dev] Edit support streaming:

```python
import fal_client

# Streaming with FLUX.2 dev Edit
handler = fal_client.submit_async(
    "fal-ai/flux-2/edit",
    arguments={
        "prompt": "Add realistic flames emerging from the coffee cup",
        "image_urls": ["https://example.com/coffee.jpg"],
    },
)

async for event in handler.iter_events(with_logs=True):
    if hasattr(event, "logs"):
        for log in event.logs:
            print(log.get("message", ""))

result = await handler.get()
print(result["images"][0]["url"])
```

---

## Model Selection Decision Matrix

| Use Case | Recommended Model | Why |
|----------|------------------|-----|
| **Jewelry product photography** | FLUX.2 Max / Pro | Precise material reflectivity, hex color accuracy |
| **Catalog image batch editing** | Seedream 5.0 Lite | Best resolution-to-cost, batch 6 generations |
| **Customer try-on (virtual)** | FireRed / FLUX.2 Max | Multi-image references, style transfer, identity preservation |
| **Typography-heavy edits** | GPT Image 2 | Near-perfect text rendering across scripts |
| **Iterative character refinement** | FLUX.1 Kontext Pro | Best character consistency across multiple edit rounds |
| **Fast draft/prototyping** | Nano Banana 2 | Flash-tier speed, 14 reference images |
| **Premium final output** | Nano Banana Pro | Maximum reasoning depth, 4K output |
| **Budget-conscious bulk processing** | Grok Imagine | Cheapest at $0.022/image |
| **Mask-based inpainting** | GPT Image 1.5 | Built-in mask support, transparent backgrounds |
| **Open-source tunable pipeline** | FireRed | Full parameter control, negative prompts, acceleration modes |
| **Multilingual text in images** | GLM-Image | Hybrid AR+diffusion for accurate script rendering |
| **Strength-controlled style transfer** | FLUX.1 dev Img2Img | `strength` parameter for granular control, LoRA support |

---

## Pricing Comparison (Normalized to 1024x1024)

| Model | Cost per 1024x1024 Edit | Cost per 4K Edit | Architecture |
|-------|------------------------|------------------|-------------|
| Grok Imagine Edit | **$0.022** | $0.022 (2K max) | Aurora (xAI) |
| GPT Image 1.5 (Low) | **$0.009** | N/A | GPT-5 |
| FLUX.2 [dev] Edit | **$0.012** | ~$0.048 | 32B Rectified Flow |
| FLUX.2 Pro Edit | **$0.030** | ~$0.120 | 32B Rectified Flow |
| FLUX.1 Kontext Pro | **$0.040** | N/A | 12B Flow Transformer |
| Seedream 5.0 Lite | **$0.035** | $0.035 (up to 9MP) | DiT + CoT |
| Seedream 4.5 Edit | **$0.040** | $0.040 | Unified DiT |
| FLUX.1 dev Img2Img | **$0.025** | N/A | 12B Flow Transformer |
| FireRed Image Edit | **~$0.033** | ~$0.130 | Qwen-based |
| GPT Image 2 | **$0.005-$0.401** | Variable | GPT-Image-2 |
| Nano Banana 2 (1K) | **$0.080** | $0.160 (4K) | Gemini 3.1 Flash |
| Nano Banana Pro (1K) | **$0.150** | $0.300 (4K) | Gemini 3. Pro |
| FLUX.2 Max | **$0.070** | ~$0.280 | 32B Rectified Flow |

---

*Registry compiled July 2, 2026. Pricing and parameters reflect the live fal.ai platform state. Elo ratings sourced from Artificial Analysis Text-to-Image Leaderboard (June 2, 2026). All API schemas verified against fal.ai OpenAPI documentation.*
