# Jewel AI Studio — Prompt Library by Workflow (Phase 3)

Built against your actual catalog (`modal.txt`): 9 generation workflows, 14 jewelry types, 18 image-edit models, 7 VTON models. Two things before the prompts:

## A. One flag you need to see before you ship JEWELRY_ON_MODEL / CUSTOMER_TRY_ON

Your default model for both is FASHN Try-On v1.6. I checked FASHN's own documentation and product blog: **FASHN's virtual try-on model explicitly does not support jewelry, scarves, or hats** — their FAQ states accessories "require different rendering techniques due to their varied shapes and placement on the body," and their public roadmap says jewelry/accessory try-on isn't something they anticipate supporting. Their `category` parameter is scoped to tops/bottoms/one-pieces, and the model was trained on garment segmentation, not small accessory placement. FASHN's own example gallery mostly runs with no text prompt at all — it's a two-image, category-driven call, not something you steer with prompt wording.

That means no amount of prompt engineering fixes JEWELRY_ON_MODEL/CUSTOMER_TRY_ON on the FASHN endpoint — it's a model-capability mismatch, not a wording problem. Two options:
1. **Route jewelry-on-model through a general compositing edit model instead** (Nano Banana Pro Edit or GPT Image 2 Edit, both already in your catalog) using an explicit "place [IMAGE_1] onto the model in [IMAGE_2]" instruction — I've written that prompt below under JEWELRY_ON_MODEL as the recommended path.
2. Keep FASHN only for cases where "on model" actually means clothing context around jewelry (e.g., a necklace shot with a garment already worn) rather than FASHN placing the jewelry itself.

I'd wire the workflow to option 1 by default and treat FASHN/image-apps-v2 as fallback for garment-adjacent shots only.

## B. The non-negotiable clause — used verbatim, unchanged, in every single workflow below

You said it plainly: no matter which of your 18 models handles the job, the raw jewelry pixels are the one thing that can never move. Research on both Google's and OpenAI's current image-edit models agrees on the same fix for this, independently: state the preserve-list explicitly, name the subject directly instead of with a pronoun, and **restate it on every prompt rather than assuming it carries over** — OpenAI's own gpt-image-2 cookbook calls this out as the single most reliable technique for preventing drift, and Google's Nano Banana Pro guide recommends the same identity-lock phrasing pattern.

So this exact block is hard-coded in your backend as a constant, injected as the *first* paragraph and repeated as the *last* paragraph of every assembled prompt — primacy and recency both, since it's the one instruction that must never get lost in a longer prompt:

```text
RAW_JEWELRY_FIDELITY_LOCK = (
    "ABSOLUTE PRESERVATION LOCK: The jewelry piece shown in Image 1 must be reproduced "
    "with zero alteration to its physical identity. Do not change its metal color, "
    "gemstone color, gemstone count, facet cuts, prong or setting structure, engraving, "
    "surface texture, proportions, or scale. Do not smooth, sharpen, redesign, or "
    "reinterpret any part of the piece. Every pixel of the jewelry itself must trace "
    "back exactly to Image 1 — only its surroundings, lighting, and background may change."
)
```

Note the image labeling convention below: I dropped the `[IMAGE_N]` bracket style from Phase 2 in favor of plain `Image 1`, `Image 2`, `Image 3` — that's what the actual published prompting guides for Nano Banana Pro and GPT Image 2 use natural-language-style, unbracketed, and it's worth matching the documented convention exactly rather than a bracket format neither vendor's guide demonstrates.

---

## 1. CATALOG_IMAGE / BULK_GENERATION — `fal-ai/nano-banana-pro/edit`

Reference optional. This is the workflow your Phase 1/2 work already covers — reused here with the vendor-matched labeling and the fidelity lock bookended.

```text
RAW_JEWELRY_FIDELITY_LOCK

ROLE: You are a master commercial jewelry photographer.
CAMERA: 100mm macro lens, f/11, edge-to-edge sharpness on the jewelry piece from Image 1, shallow depth of field on the background so it stays softly out of focus.
LIGHTING: Soft diffused studio lighting, dense accurate contact shadow beneath the jewelry piece from Image 1, realistic metal reflection of the surrounding environment.

{{SUBTYPE_BLOCK}}

{{EXECUTION_BLOCK}}   # Reference Environment Match (Image 2 present) OR Modern Catalog Environment (no Image 2) — same two branches as Phase 2, Layer 3A/3B, unbracketed image labels

{{BRANDING_CLAUSE}}   # same has_logo split as Phase 2

NEGATIVE PROMPT: velvet jewelry box, ring box, leather display stand, generic gradient studio backdrop, repetitive background, 3d render look, plastic texture, warped band, floating object, missing contact shadow, cropped edges, off-center subject, overlapping logo.

RAW_JEWELRY_FIDELITY_LOCK
```

---

## 2. REFERENCE_STYLE_MATCH — `fal-ai/nano-banana-pro/edit`

Different from Catalog Image in one structural way: this workflow only exists when the user picked it specifically to match a mood/lighting reference, so there's no no-reference branch to route around — a reference image is implicit to the workflow. Keep it a pure style/mood transfer, not a full re-environment (that's what Background Replacement is for).

```text
RAW_JEWELRY_FIDELITY_LOCK

ROLE: You are a master commercial jewelry photographer matching a specific visual style.

STYLE EXTRACTION: From Image 2, extract only its lighting direction, color temperature, contrast level, and overall mood — warm/cool grading, shadow softness, highlight intensity. Do not extract or copy any object, background material, or composition from Image 2, only its lighting and color character.

APPLICATION: Apply this lighting and color mood to the jewelry piece from Image 1 in its own environment. Keep the framing, angle, and composition of Image 1 unchanged.

{{SUBTYPE_BLOCK}}

{{BRANDING_CLAUSE}}

NEGATIVE PROMPT: mismatched shadow direction, color cast on gemstones that alters true stone color, over-saturated grading, background elements copied from Image 2.

RAW_JEWELRY_FIDELITY_LOCK
```

This is the one workflow where you need an explicit safeguard against the fidelity lock and the style-match instruction fighting each other — "warm mood lighting" can visually shift how a gemstone color reads even when the underlying pixels are untouched, so the negative prompt calls that out specifically.

---

## 3. BACKGROUND_REPLACEMENT — `fal-ai/flux-2-max/edit`

Pure background swap, nothing else. Reference optional (with-reference: literal background swap; without: same Modern Catalog environment logic as Catalog Image, but background-only — no relighting of the subject itself).

```text
RAW_JEWELRY_FIDELITY_LOCK

ROLE: You are a commercial retoucher performing a background replacement only.

INSTRUCTION: Replace only the background behind the jewelry piece from Image 1. {{BACKGROUND_SOURCE}}

Do not change the jewelry piece's lighting, angle, position, or the direction of its existing contact shadow — regenerate the contact shadow only enough to match the new surface beneath it, keeping its density and shape consistent with the original.

NEGATIVE PROMPT: change to jewelry lighting, change to jewelry angle, relit metal reflections that don't match the original capture, background bleeding onto the jewelry edges.

RAW_JEWELRY_FIDELITY_LOCK
```

`{{BACKGROUND_SOURCE}}` — Python-injected, one of:
```text
# has_reference = True
"Use the background surface and material shown in Image 2 exactly, cropped and scaled to fit behind the existing jewelry composition."

# has_reference = False
"Generate this background: {{CHOSEN_ENVIRONMENT}}"   # same rotation pool as Phase 2 Layer 3B
```

---

## 4. GEMSTONE_COLOR_CHANGE — `fal-ai/flux-2-max/edit`

The highest-risk workflow for your stated invariant, because the entire point of this workflow is to deliberately change something about the piece — so the fidelity lock has to explicitly carve out the one allowed exception rather than blanket-forbidding all change.

```text
RAW_JEWELRY_FIDELITY_LOCK

ROLE: You are a gemological retoucher performing a single, precise color edit.

INSTRUCTION: Change only the color of the gemstone(s) in Image 1 to {{TARGET_COLOR}}. This is the one explicit exception to the preservation lock above — every other attribute stays governed by it in full: do not change facet cuts, stone count, stone size, cut style, setting, prong structure, metal color, or the jewelry's position and lighting. Match the new gemstone color's refraction and internal light behavior to the original stone's cut and clarity — a color change must still look physically correct for that specific cut, not flat or painted on.

NEGATIVE PROMPT: flat unrefracted color, painted-on gemstone look, altered facet pattern, changed stone size, changed stone count, changed setting or prongs, changed metal color, bleeding color onto the metal band.

RAW_JEWELRY_FIDELITY_LOCK
```

`{{TARGET_COLOR}}` is the one field this workflow actually needs from the job payload (e.g. `"a deep emerald green"`, `"a vivid ruby red"`) — pass it as a specific, named color, not a hex code; named gemstone-adjacent color language (sapphire blue, emerald green) reads more reliably to these models than raw hex per the same "be specific and concrete, not abstract" pattern that held across every model I checked.

---

## 5. LUXURY_ENHANCEMENT — `fal-ai/flux-pro/kontext`

Polish only — no background, composition, or color change. This is the workflow most likely to accidentally violate your invariant if left vague, because "enhance" is exactly the kind of verb that FLUX Kontext's own prompting guide warns can trigger a full rework instead of a targeted edit. Avoid it entirely.

```text
RAW_JEWELRY_FIDELITY_LOCK

ROLE: You are a luxury jewelry retoucher performing a light technical polish pass only.

INSTRUCTION: On the jewelry piece from Image 1, increase micro-contrast and specular clarity on the metal surface and gemstone facets only. Do not add reflections, environments, or elements that were not present in the original capture. Do not change the metal's hue, only its clarity and highlight crispness. Keep composition, angle, background, and lighting direction exactly as in Image 1.

NEGATIVE PROMPT: full re-render, changed metal hue, added environment elements, over-sharpened plastic look, altered gemstone facet geometry, changed composition.

RAW_JEWELRY_FIDELITY_LOCK
```

---

## 6. CUSTOM_PROMPT — `openai/gpt-image-2/edit`

This is the one workflow where a user types free text directly — which is exactly the case your invariant most needs to survive, since you don't control their wording. GPT Image 2's own prompting cookbook recommends a fixed three-slot structure — **Change / Preserve / Physical Realism** — and explicitly recommends restating the Preserve list on every request rather than trusting it to persist. Use that structure directly: the user's text only ever fills the Change slot; your backend always owns Preserve and Physical Realism.

```text
RAW_JEWELRY_FIDELITY_LOCK

CHANGE: {{USER_CUSTOM_INSTRUCTION}}

PRESERVE: The jewelry piece's exact geometry, facet cuts, metal color, gemstone color and clarity, proportions, and scale from Image 1, in every case, regardless of what the Change instruction above requests. If the Change instruction conflicts with preserving the jewelry piece itself, apply the Change only to background, lighting, or composition, and do not apply any part of it that would alter the jewelry piece's physical identity.

PHYSICAL REALISM: Maintain a single consistent light source, an accurate contact shadow, and correct perspective between the jewelry piece and its surroundings.

RAW_JEWELRY_FIDELITY_LOCK
```

This is the one place you should add a backend-side check, not just a prompt-side one: scan `{{USER_CUSTOM_INSTRUCTION}}` for jewelry-altering language (resize, recolor the metal, change the stone, redesign) before assembly, and either strip that clause or route it to GEMSTONE_COLOR_CHANGE-style explicit-exception phrasing instead of letting free text fight the lock silently.

---

## 7. JEWELRY_ON_MODEL — recommended: `fal-ai/nano-banana-pro/edit` (not FASHN, see flag A above)

```text
RAW_JEWELRY_FIDELITY_LOCK

ROLE: You are a jewelry compositing specialist placing a real piece onto a model photo.

INSTRUCTION: Place the jewelry piece from Image 1 onto the model in Image 2, at the anatomically correct position for {{JEWELRY_TYPE}} (ring: finger; necklace/pendant: neck/collarbone; earring: ear; bracelet/bangle/kara: wrist; anklet: ankle; brooch: garment lapel or chest; watch: wrist; cufflinks: cuff). Match the jewelry's scale, perspective, and lighting to the model's pose and the scene's light direction. Do not alter the model's face, body, pose, skin tone, or existing clothing. Do not alter the jewelry piece itself beyond the perspective and lighting match required to seat it naturally on the body.

NEGATIVE PROMPT: warped jewelry to fit body contour, resized jewelry disproportionate to body scale, changed model identity, changed model pose, floating jewelry not touching skin, missing contact shadow where jewelry meets skin.

RAW_JEWELRY_FIDELITY_LOCK
```

## 8. CUSTOMER_TRY_ON — recommended: `fal-ai/nano-banana-pro/edit` (customer's own photo as Image 2, same reasoning as #7)

Same structure as JEWELRY_ON_MODEL, with one addition since this is a real customer photo, not a studio model shot:

```text
Add before the NEGATIVE PROMPT line:
"Preserve the customer's photo exactly — do not retouch, smooth, or beautify their skin, face, or body. Only add the jewelry piece."
```

---

## What's intentionally not in this file

**RATE_TOOLS** isn't a generation workflow (metals pricing, non-AI per your doc) — no prompt needed. I also didn't write per-subtype variants for all 14 jewelry types again here since Phase 2's `SUBTYPE_PROMPTS` dict already covers the physics language — extend that dict with entries for Bangles, Kara, the three Earrings sub-variants (Studs/Drops/Hoops can likely share one earring block unless you find they need to diverge in testing), Watch, and Cufflinks, following the same pattern as the existing Ring/Necklace/Earring entries.

Run every workflow above through the Phase 1 §4 regression methodology before shipping — the fidelity-lock bookending in particular needs to be verified against real outputs, not assumed to work because the wording is grounded in vendor docs.
