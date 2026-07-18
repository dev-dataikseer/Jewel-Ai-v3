# Jewel AI Studio — Real fal.ai Model Reference (Verified, July 2026)

Checked against fal.ai's own docs/model pages, not assumed from model family patterns. Confidence is marked per model: **Confirmed** = pulled directly from that endpoint's own fal.ai API reference page. **Inferred** = documented for a closely related endpoint in the same family (I say exactly which one) and likely the same, but not confirmed on that exact endpoint's own page — verify in your fal dashboard playground before wiring it in blind.

All fal endpoints share the same call pattern:
```python
import fal_client
result = fal_client.subscribe("ENDPOINT_ID", arguments={...}, with_logs=True)
```
```javascript
import { fal } from "@fal-ai/client";
const result = await fal.subscribe("ENDPOINT_ID", { input: {...} });
```
Auth via `FAL_KEY` env var. Only the `arguments`/`input` object differs per model — that's what's documented below.

---

## SECTION 1 — IMAGE-EDIT MODELS (image_to_image)

### 1. Gemini 3 Pro Image Edit — `fal-ai/gemini-3-pro-image-preview/edit` — **Confirmed**
Same underlying model/params family as Nano Banana Pro Edit below (Nano Banana Pro IS Gemini 3 Pro Image on fal's naming).
```json
{
  "prompt": "string, required",
  "image_urls": ["array of URLs, required for edit"],
  "num_images": 1,
  "aspect_ratio": "auto",
  "output_format": "png",
  "resolution": "1K",
  "safety_tolerance": "4",
  "sync_mode": false
}
```
Notes: `resolution` also accepts `2K`/`4K`. There's an experimental `num_images`-lock parameter to force single output even if the prompt implies multiple. Also has a web-search-grounding toggle for the generation task (use with caution — not something you want on for jewelry jobs, keep off).

### 2. Nano Banana Pro Edit — `fal-ai/nano-banana-pro/edit` — **Confirmed** (your CATALOG_IMAGE / REFERENCE_STYLE_MATCH default)
```json
{
  "prompt": "string, required",
  "image_urls": ["array of URLs — accepts multiple, role-labeled in prompt text as Image 1 / Image 2 / etc."],
  "num_images": 1,
  "aspect_ratio": "auto",
  "output_format": "png",
  "resolution": "1K",
  "safety_tolerance": "4",
  "sync_mode": false
}
```
Notes: All outputs carry an invisible SynthID watermark automatically (Google-side, not something your prompt controls — irrelevant to your own logo/branding clause, it's a separate provenance layer). `image_urls` is the correct field name — not `image_url` singular.

### 3. FLUX 2 Max Edit — `fal-ai/flux-2-max/edit` — **Confirmed** (your GEMSTONE_COLOR_CHANGE / BACKGROUND_REPLACEMENT default)
```json
{
  "prompt": "string, required",
  "image_urls": ["array of URLs"],
  "num_images": 1,
  "output_format": "jpeg",
  "seed": null,
  "guidance_scale": null
}
```
Notes: Multi-image composition supported — reference images by natural description or index in your prompt text ("using image 2"). Pricing is per-megapixel ($0.07 first MP, $0.03 each additional) — relevant if you're budgeting bulk gemstone-color jobs.

### 4. GPT Image 2 Edit — `openai/gpt-image-2/edit` — **Confirmed** (your CUSTOM_PROMPT default)
```json
{
  "prompt": "string, required",
  "image_urls": ["array of URLs, required"],
  "mask_image_url": "optional — must match input image dimensions, for masked/region-limited edits",
  "quality": "high",
  "output_format": "png"
}
```
Notes: `quality` also accepts `medium`/`low`/`auto` — cost scales sharply with quality (roughly $0.01/image low → $0.41/image high at 4K). Input images are always processed at high fidelity regardless of `quality` setting — no separate `input_fidelity` param on this model (unlike GPT Image 1.5, where it existed). No transparent-background support. Supports up to 16 reference images per call, useful if you ever need multi-image compositing beyond your current 3-image (subject/reference/logo) pattern.

### 5. FLUX 2 Pro Edit — `fal-ai/flux-2-pro/edit` — **Confirmed**
```json
{
  "prompt": "string, required",
  "image_urls": ["array of URLs, up to 9 reference images / 9MP total input"],
  "output_format": "jpeg"
}
```
Notes: Deliberately has no `guidance_scale` or step count to tune — "production-optimized," fixed internal settings. Reference images addressable by index in prompt text ("replace the background with image 3").

### 6. FLUX Kontext (Pro) — `fal-ai/flux-pro/kontext` — **Confirmed** (your LUXURY_ENHANCEMENT default)
```json
{
  "prompt": "string, required",
  "image_url": "single URL — note: singular, not image_urls",
  "guidance_scale": 3.5,
  "num_images": 1,
  "output_format": "jpeg",
  "safety_tolerance": "2",
  "enhance_prompt": false,
  "seed": null
}
```
Notes: **This endpoint takes `image_url` singular**, not the `image_urls` array plural used by every other model in this section — it's single-reference-image only. Since your Luxury Enhancement workflow is single-subject polish with no reference/logo images, this is a non-issue for that workflow specifically, but don't reuse this endpoint's request-builder code path for any workflow that needs 2+ images. `guidance_scale` range is 1–20 (default 3.5); `safety_tolerance` 1–6.

**FLUX Kontext Max variant** (`fal-ai/flux-pro/kontext/max`) shares identical parameters if you want a higher-fidelity option in the same family — same `image_url` singular constraint applies.

### 7. Nano Banana 2 Edit — `fal-ai/nano-banana-2/edit` — **Confirmed**
```json
{
  "prompt": "string, required",
  "image_urls": ["array of URLs — up to 14 reference images"]
}
```
Notes: Runs on Gemini 3.1 Flash Image — faster/cheaper than Nano Banana Pro, lower fidelity on identity preservation per Google's own comparison. Good secondary/fallback option for Catalog Image if Nano Banana Pro is rate-limited.

### 8. Gemini 3.1 Flash Image Edit — `fal-ai/gemini-3.1-flash-image-preview/edit` — **Inferred** (same family as #7, same underlying model)
Same request shape as Nano Banana 2 Edit — `prompt` + `image_urls`. This is very likely the same endpoint under fal's alternate naming convention (Gemini-native vs. Nano-Banana-branded), the way Gemini 3 Pro Image Edit and Nano Banana Pro Edit are the same model under two names in your own catalog. Verify against your dashboard rather than assuming a param difference.

### 9. Nano Banana Edit — `fal-ai/nano-banana/edit` — **Confirmed**
```json
{
  "prompt": "string, required",
  "image_urls": ["array of URLs"]
}
```
Notes: Original Gemini 2.5 Flash Image generation — fastest/cheapest tier in the family, weakest identity preservation. Fine for cheap high-volume drafts, not recommended as a primary path given your fidelity-lock requirement.

### 10. Seedream 5.0 Pro Edit — `bytedance/seedream/v5/pro/edit` — **Confirmed**
```json
{
  "prompt": "string, required",
  "image_urls": ["array of URLs — up to 10 reference images"],
  "image_size": "preset or {width, height}, up to 2048x2048",
  "num_images": 1,
  "output_format": "png"
}
```
Notes: Region-precise/"grounded" editing — designed to change one element while keeping the rest of the frame untouched, which is a strong match for your fidelity-lock model of "change only X, preserve everything else." Pricing: $0.0675/image up to 1536×1536, $0.135 above that, plus $0.0045 per additional reference image beyond the first.

### 11. Seedream 5.0 Lite Edit — `fal-ai/bytedance/seedream/v5/lite/edit` — **Confirmed**
```json
{
  "prompt": "string, required",
  "image_urls": ["array of URLs — up to 10 reference images"],
  "image_size": "preset (square_hd, portrait_3_4, landscape_16_9, auto_2K, auto_3K, etc.) — default auto_2K"
}
```
Notes: Deliberately minimal API — ByteDance stripped negative-prompt, guidance-scale, step-count, and seed controls from this tier; the model makes those decisions internally. That means your `NEGATIVE PROMPT:` block in the assembled prompt text still works (it's just prose the model reads), but there's no dedicated negative-prompt request field for this endpoint the way some others have.

### 12. Seedream 4.5 Edit — `fal-ai/bytedance/seedream/v4.5/edit` — **Inferred** (same request shape as v5 Lite/Pro edit endpoints, prior generation)
```json
{
  "prompt": "string, required",
  "image_urls": ["array of URLs"]
}
```
Previous-generation Seedream — same call pattern as v5, likely fewer max reference images and lower max resolution. Fine as a fallback tier; no reason to default to it over v5 Pro/Lite.

### 13. GPT Image 1.5 Edit — `fal-ai/gpt-image-1.5/edit` — **Inferred** (predecessor to GPT Image 2, same publisher/family on fal)
```json
{
  "prompt": "string, required",
  "image_urls": ["array of URLs"],
  "quality": "high",
  "input_fidelity": "high"
}
```
Notes: Unlike GPT Image 2, this earlier version does expose a separate `input_fidelity` parameter you can tune down for cost — GPT Image 2 removed that control and always processes at high fidelity. If your allowlist ever routes Custom Prompt jobs to this model as a cheaper fallback, that's the one meaningful behavioral difference to account for in your cost/quality logic.

### 14. FLUX 2 Dev Edit — `fal-ai/flux-2/edit` — **Inferred** (open-weight dev tier of the FLUX 2 family, same `image_urls`/`prompt` pattern as Pro/Max)
Likely same base request shape as FLUX 2 Max/Pro edit, with `guidance_scale` and step-count controls exposed (dev tiers in the FLUX line typically keep these where Pro/Max strip them for a "zero-config" experience). Verify param names in-dashboard before wiring — this is the least-documented of the FLUX 2 tier in public search results.

### 15. GLM-Image I2I — `fal-ai/glm-image/image-to-image` — **Not independently confirmed**
Zhipu AI's GLM image model on fal. I could not find a public fal-specific parameter page for this exact endpoint in this pass — treat it as `prompt` + `image_urls` (the near-universal fal image-edit shape) until you've confirmed the exact schema in your fal dashboard's own API reference tab for this model, which fal auto-generates per-endpoint and is authoritative over anything below it in your allowlist.

### 16. FireRed Image Edit v1.1 — `fal-ai/firered-image-edit-v1.1` — **Not independently confirmed**
Same caveat as #15 — not enough public documentation surfaced to confirm exact parameters beyond the standard `prompt` + `image_urls` shape. Check the dashboard schema directly.

### 17. Grok Imagine Edit — `xai/grok-imagine-image/edit` — **Not independently confirmed**
Same caveat — xAI's model routed through fal. Standard `prompt` + `image_urls` shape is the safe assumption; confirm exact field names and any xAI-specific safety/style parameters in-dashboard.

### 18. FLUX Dev I2I — `fal-ai/flux/dev/image-to-image` — **Inferred** (original FLUX.1 [dev] image-to-image, well-documented model family)
```json
{
  "prompt": "string, required",
  "image_url": "single URL (older FLUX.1 image-to-image endpoints use singular, matching the Kontext Pro pattern above)",
  "strength": 0.85,
  "guidance_scale": 3.5,
  "num_inference_steps": 40
}
```
Notes: This is the oldest/cheapest tier in your catalog. `strength` controls how much the output deviates from the input image — for your fidelity-lock use case you'd want this low, but low `strength` also limits how much environment/background change is even possible, which is a real tension on this specific model that doesn't exist on the instruction-following edit models above it in your ranking. Not a great fit for any of your 8 generation workflows given that constraint — it's better suited as a cheap fallback for LUXURY_ENHANCEMENT (minimal change) than for CATALOG_IMAGE (needs more environment freedom).

---

## SECTION 2 — VIRTUAL TRY-ON MODELS (virtual_try_on)

Recall from the last file: **none of these are appropriate as the default for jewelry** — they're all garment-focused. Documented here for completeness / as fallback options for garment-context shots only, per your own allowlist.

### 39. Lucy 2.1 Realtime VTON — `decart/lucy2-vton/realtime` — **Confirmed** (disabled in Studio)
Not a standard request/response call — this one runs over **WebRTC**, not the queue API. Takes a live webcam feed plus a text prompt and optional reference garment image; you can push a new prompt or reference mid-session on the same connection. **Jewel AI seeds this as `is_active: false` / `queue_compatible: false`** so it never appears in Studio async model selectors.

### 40. FASHN Try-On v1.6 — `fal-ai/fashn/tryon/v1.6` — **Confirmed**
```json
{
  "model_image": "URL — person photo",
  "garment_image": "URL — flat-lay or on-model garment photo",
  "category": "auto | tops | bottoms | one-pieces",
  "mode": "performance | balanced | quality",
  "garment_photo_type": "auto | model | flat-lay",
  "num_samples": 1
}
```
Notes: Confirmed again — no jewelry support in `category`. Renders at 864×1296. Most of FASHN's own example gallery runs with an empty/no prompt field at all — this model is driven almost entirely by the two images and `category`, not by text instructions, which is exactly why prompt engineering can't route around the jewelry gap.

### 41. Virtual Try-On (image-apps-v2) — `fal-ai/image-apps-v2/virtual-try-on` — **Confirmed**
```json
{
  "person_image_url": "URL",
  "clothing_image_url": "URL"
}
```
Notes: Minimal schema — no visible `category` or garment-type param in the confirmed example, meaning even less control than FASHN for anything jewelry-adjacent. A `preserve_pose` toggle and 4K aspect-ratio control are documented for this model elsewhere in fal's VTON comparison guide but weren't present in the concrete example call — verify presence in-dashboard before depending on them.

### 42. FLUX 2 LoRA Virtual Try-On — `fal-ai/flux-2-lora-gallery/virtual-tryon` — **Confirmed**
```json
{
  "image_urls": ["person URL", "garment/clothing URL"],
  "prompt": "string, required",
  "lora_scale": 1.0,
  "acceleration": "none | regular | high",
  "num_images": 1
}
```
Notes: Uses `image_urls` (person first, then garment) — **not** separate `person_image_url` / `garment_image_url` fields. Jewel AI maps packet indices accordingly (`try_on_image_order: [person, product]`). `lora_scale` range 0–2. Same garment-only scope as the rest of this section.

### 43. Kling Kolors VTON v1.5 — `fal-ai/kling/v1-5/kolors-virtual-try-on` — **Confirmed**
```json
{
  "human_image_url": "URL",
  "garment_image_url": "URL"
}
```
Notes: Deliberately minimal — just the two image URLs, no other documented parameters. $0.07/generation.

### 44. Cat-VTON — `fal-ai/cat-vton` — **Wired in Jewel AI**
```json
{
  "human_image_url": "URL — person",
  "garment_image_url": "URL — garment",
  "cloth_type": "upper | lower | overall | inner | outer",
  "image_size": "portrait_4_3",
  "num_inference_steps": 30,
  "guidance_scale": 2.5
}
```
Notes: Jewel AI uses `human_image_url` / `garment_image_url` (same as Kling Kolors), not `person_image_url`.

### 45. Leffa Virtual Try-On — `fal-ai/leffa/virtual-tryon` — **Not independently confirmed**
Same caveat as #44.

---

## Jewel AI system wiring (upload → model)

How Studio jobs prepare images for every endpoint:

1. **Packet** (`build_image_packet` / `build_model_image_plan`) — ordered slots: product → theme|portrait → logo, truncated to the model's `ImageContract` capacity (`urls_array` up to N, `single_url` = 1, try-on = 2 mapped fields).
2. **Validate** — min/max image count; JPEG/PNG/WebP magic-byte checks on upload-to-fal; try-on requires product + portrait.
3. **fal CDN** (`prepare_images` / `ensure_fal_url`) — local/storage URLs uploaded to fal.media (cached by content digest).
4. **Field map** (`SpecRequestBuilder._apply_images`) — `image_urls` | `image_url` | try-on named fields | ordered `image_urls` for LoRA VTON.
5. **Logo** — included as a reference when capacity allows; otherwise post-composed onto the output (`logo_mode: compose`).

| Contract mode | Examples | What user uploads become |
|---|---|---|
| `urls_array` | Nano Banana Pro, GPT Image 2, FLUX 2 | `[product, theme?, logo?]` as `image_urls` |
| `single_url` | Kontext, FLUX Dev I2I | product only as `image_url` (theme/logo dropped or composed) |
| `try_on_fields` | FASHN, Kling, Cat-VTON, Leffa | product→garment field, portrait→person field |
| `try_on_ordered` | FLUX LoRA VTON | `image_urls: [person, product]` |

Jewelry try-on **defaults to Nano Banana Pro / GPT Image 2** (I2I compositing). Garment VTON endpoints remain optional and are not jewelry-native.

---

## What to do with the "Not independently confirmed" entries

A few image-edit models (GLM-Image, FireRed, Grok Imagine Edit) and Leffa still have thinner public docs — fal's per-model API tab in the dashboard remains authoritative. Treat those as "verify before heavy production traffic," not broken.
