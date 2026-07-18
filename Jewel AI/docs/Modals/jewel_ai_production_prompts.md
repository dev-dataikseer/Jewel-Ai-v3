# Jewel AI Studio — Production Prompt Library (Phase 2)

## What changed from your old prompt, and why

Your pasted prompt is well-written photography language, but it's a **single monolithic block with embedded conditionals** ("If provided... If no reference image is provided, ignore this instruction..."). That's the exact prompt-bleed pattern from Phase 1 — an instruction-following image model still attends to the "ignore this" branch even when told to ignore it, because the text is present in the context either way. I did not carry that structure forward.

I also didn't just restyle your prompt — I checked current guidance for instruction-based image editing models (Black Forest Labs' own FLUX.1/FLUX.2 Kontext prompting docs and independent guides, since your stack routes through fal.ai which serves Kontext-family and similar editing models) before rewriting the wording. Three findings changed how I phrased things below:

- **Direct action verbs, not vague ones.** Guidance from Black Forest Labs and multiple independent guides is consistent: prompts that use explicit verbs ("replace," "erase," "extract," "apply") outperform vague ones ("transform," "enhance"), because "transform" style verbs can trigger a full rework instead of a targeted edit.
- **Name the subject, don't rely on pronouns.** "The primary jewelry subject" repeated explicitly beats "it" or "the item" once you're several clauses deep — pronoun drift is a cited failure mode for multi-image composition.
- **State preservation explicitly, every time.** "While maintaining X" clauses attached directly to the instruction they modify are more reliable than a single global preservation paragraph the model has to remember applies to a later, unrelated line.
- **Token budget is real and model-dependent.** Base FLUX.1 Kontext caps prompts around 512 tokens on its text encoder; Kontext Max variants and other providers accept far more. Your `build_final_prompt` output should be measured per-provider, and the blocks below are written to fail gracefully if you need to trim (each numbered clause is independently droppable) rather than degrading if cut mid-sentence.

I kept your strongest original material — Profoto lighting language, focus stacking, ambient occlusion, the specific negative-prompt vocabulary — because it's accurate photography terminology and there's no research reason to change it. What's rewritten is the *structure*: no conditionals, no pronouns standing in for the subject, explicit preservation clauses attached to each instruction, and the reference/no-reference/logo/no-logo split from Phase 1.

---

## Layer 1 — MASTER_BASE_PROMPT (always included)

```text
ROLE: You are a master commercial product photographer and high-end jewelry retoucher.

SUBJECT LOCK: The jewelry piece in [IMAGE_1] is the fixed subject. Extract it exactly as photographed — do not rotate it, do not change which way it faces, do not alter its resting angle. Preserve the exact original pixels, geometry, facet cuts, prong structure, metal color, gemstone clarity and refraction, and true-to-life scale of the jewelry piece from [IMAGE_1], while placing it into the new environment described below.

COMPOSITION: Center the jewelry piece from [IMAGE_1] with balanced negative space on all sides. Ground the piece so it reads as physically resting on the surface, not floating above it.

CAMERA: Shot on a 100mm macro lens at f/11 for edge-to-edge sharpness on the jewelry piece from [IMAGE_1]. Apply crisp focus stacking on the subject while keeping the background at a shallow depth of field, softly out of focus, so it never competes with the jewelry detail. Editorial print quality, high resolution.

LIGHTING: Soft, diffused studio lighting from large overhead softboxes with subtle fill, revealing gemstone clarity without harsh glare or blown highlights. Generate a dense, physically accurate contact shadow directly beneath the jewelry piece from [IMAGE_1], matching its exact geometry, that anchors it to the surface. Metal surfaces must reflect the color and light of the surrounding environment realistically, without overexposure.

NEGATIVE PROMPT: 3d render, CGI, digital illustration, plastic texture, artificial AI glow, over-smoothed metal, warped band, distorted facets, melted prongs, floating object, hovering jewelry, ungrounded item, missing contact shadow, mismatched shadow direction, repetitive background, fixed default studio, cluttered background, busy patterns, neon colors, cartoon or painterly effect, blurred filigree, altered pattern density, redesigned structure, changed camera angle, forced perspective, cropped edges, off-center subject, velvet jewelry box, ring box, leather display stand, generic gradient studio backdrop, overlapping logo, distorted branding, watermark collision, duplicate watermark.
```

---

## Layer 2 — CHILD_SUBTYPE_PROMPT (inject the matching block(s), in this fixed order)

```python
SUBTYPE_ORDER = ["ring", "necklace", "earring", "bracelet", "pendant", "bangle", "brooch", "anklet", "set"]
```

```text
RING: The ring's shank must rest flat against the supporting surface at its true point of contact. Generate a tight, dark contact shadow directly beneath the band, not a diffuse ambient shadow.

NECKLACE: The chain and pendant must drape across the surface following natural gravity — no rigid or perfectly symmetrical draping. Each link should cast a micro-shadow onto the surface beneath it.

EARRING: Position the earring either standing upright against a supporting surface or suspended with a visible, physically accurate drop shadow reflecting vertical gravity. Both earrings in a pair, if present in [IMAGE_1], must match in scale and orientation.

BRACELET: The bracelet must rest in a natural closed or slightly open curve consistent with how it was photographed in [IMAGE_1] — do not flatten it into a straight line.

PENDANT: The pendant hangs from its bail with the front face oriented toward camera, exactly as in [IMAGE_1]. Do not reorient the pendant face.

BANGLE: The bangle keeps its true circular or oval cross-section from [IMAGE_1] with a consistent contact shadow along its lowest point.

BROOCH: The brooch's pin mechanism, if visible in [IMAGE_1], stays exactly as photographed. Do not add or remove a garment/fabric mount unless one is already present in [IMAGE_1].

ANKLET: Same draping physics as necklace, scaled to a smaller circumference and closer to the surface.

SET: When multiple jewelry pieces from [IMAGE_1] are part of one set, preserve their relative scale to one another exactly as photographed, and apply each piece's own subtype grounding rules above.
```

---

## Layer 3A — REFERENCE MIRRORING (used only when `has_reference = True`)

```text
EXECUTION MODE: REFERENCE ENVIRONMENT MATCH
1. Extract the background surface, materials, lighting direction, shadow density, and color grading from [IMAGE_2]. Apply this exact environment style around the jewelry piece from [IMAGE_1].
2. Ignore any jewelry, hands, mannequins, or models shown in [IMAGE_2] — use [IMAGE_2] only as an environment and lighting reference, never as a subject reference.
3. Keep the camera angle, framing, and composition of [IMAGE_1]'s jewelry piece unchanged while placing it into the [IMAGE_2] environment.
{{BRANDING_CLAUSE}}
```

Branding clause (Python-selected, never both, never a dangling `[IMAGE_3]` reference when no logo was attached):

```text
# has_logo = True
4. Erase any existing watermark, logo, or text overlay found in [IMAGE_2] completely — it must not appear in the output. Apply the logo from [IMAGE_3] as the only branding in the final image, scaled small and positioned in the bottom-right or top-center corner with refined opacity, matching the scene's lighting. The logo from [IMAGE_3] must never overlap the jewelry piece from [IMAGE_1] or cast a shadow.

# has_logo = False
4. Erase any existing watermark, logo, or text overlay found in [IMAGE_2] completely. The final image must contain no branding of any kind.
```

---

## Layer 3B — MODERN DYNAMIC CATALOG (used only when `has_reference = False`)

```text
EXECUTION MODE: MODERN CATALOG ENVIRONMENT
1. Place the jewelry piece from [IMAGE_1] into the following environment, generated fresh for this image: {{CHOSEN_ENVIRONMENT}}
2. Align the surface plane and horizon to match the jewelry piece's current resting orientation from [IMAGE_1]. Generate a deep, dense contact shadow anchoring the piece to this surface based on its exact geometry.
3. Do not use a velvet jewelry box, ring box, leather display stand, mannequin, or generic gradient studio backdrop under any circumstances.
{{BRANDING_CLAUSE}}
```

`{{CHOSEN_ENVIRONMENT}}` — a single concrete sentence chosen and rotated by your backend (see Phase 1 doc §2, Layer 3B), never a list handed to the model. Sample pool, phrased as complete environment descriptions rather than a menu, per the "be specific, not vague" finding above:

```python
ENVIRONMENT_POOL = [
    "a matte travertine stone slab, soft architectural shadow lines crossing the surface at a low camera angle",
    "dark brushed concrete lit from one direction, casting a long soft-edged shadow across the frame",
    "fluted cream marble with vertical channel grooves catching diffuse overhead light",
    "a dark glass surface with caustic water reflections rippling across the background",
    "smooth grey river stones arranged with generous negative space around the jewelry",
    "dark volcanic basalt with a fine mist of water droplets catching specular highlights",
    "raw unbleached silk drapery pooling softly beneath the jewelry, natural fiber texture visible",
    "a frosted acrylic plinth lit from below with a cool rim light separating subject from background",
    "a brushed champagne-gold metal surface with a soft gradient reflection of the jewelry piece",
]
```

Branding clause (same split logic as 3A, with no reference image to clean up):

```text
# has_logo = True
4. Apply the logo from [IMAGE_3] as the only branding in the final image, scaled small and positioned in the bottom-right or top-center corner with refined opacity, matching the scene's lighting. The logo from [IMAGE_3] must never overlap the jewelry piece from [IMAGE_1] or cast a shadow.

# has_logo = False
4. The final image must contain no branding, watermark, or text of any kind.
```

---

## Layer 4 — ATTACHMENT ROLE MAPPING (append last, only for images actually attached)

```text
ATTACHMENT ROLES:
- [IMAGE_1]: PRIMARY SUBJECT. The jewelry piece to preserve exactly and place into the new environment.
```
```text
# appended only if has_reference:
- [IMAGE_2]: ENVIRONMENT REFERENCE. Background, lighting, and material style source only. Not a subject reference.
```
```text
# appended only if has_logo:
- [IMAGE_{2 or 3}]: LOGO. Brand mark to apply as a small watermark. Never a subject or environment reference.
```

---

## Worked example — full assembled prompt, `has_reference=True, has_logo=True, jewelry_types=["ring"]`

This is what `build_final_prompt` should produce as one string for this combination — no conditionals left in the text, every image reference concrete:

```text
ROLE: You are a master commercial product photographer and high-end jewelry retoucher.

SUBJECT LOCK: The jewelry piece in [IMAGE_1] is the fixed subject. Extract it exactly as photographed — do not rotate it, do not change which way it faces, do not alter its resting angle. Preserve the exact original pixels, geometry, facet cuts, prong structure, metal color, gemstone clarity and refraction, and true-to-life scale of the jewelry piece from [IMAGE_1], while placing it into the new environment described below.

COMPOSITION: Center the jewelry piece from [IMAGE_1] with balanced negative space on all sides. Ground the piece so it reads as physically resting on the surface, not floating above it.

CAMERA: Shot on a 100mm macro lens at f/11 for edge-to-edge sharpness on the jewelry piece from [IMAGE_1]. Apply crisp focus stacking on the subject while keeping the background at a shallow depth of field, softly out of focus, so it never competes with the jewelry detail. Editorial print quality, high resolution.

LIGHTING: Soft, diffused studio lighting from large overhead softboxes with subtle fill, revealing gemstone clarity without harsh glare or blown highlights. Generate a dense, physically accurate contact shadow directly beneath the jewelry piece from [IMAGE_1], matching its exact geometry, that anchors it to the surface. Metal surfaces must reflect the color and light of the surrounding environment realistically, without overexposure.

NEGATIVE PROMPT: 3d render, CGI, digital illustration, plastic texture, artificial AI glow, over-smoothed metal, warped band, distorted facets, melted prongs, floating object, hovering jewelry, ungrounded item, missing contact shadow, mismatched shadow direction, repetitive background, fixed default studio, cluttered background, busy patterns, neon colors, cartoon or painterly effect, blurred filigree, altered pattern density, redesigned structure, changed camera angle, forced perspective, cropped edges, off-center subject, velvet jewelry box, ring box, leather display stand, generic gradient studio backdrop, overlapping logo, distorted branding, watermark collision, duplicate watermark.

RING: The ring's shank must rest flat against the supporting surface at its true point of contact. Generate a tight, dark contact shadow directly beneath the band, not a diffuse ambient shadow.

EXECUTION MODE: REFERENCE ENVIRONMENT MATCH
1. Extract the background surface, materials, lighting direction, shadow density, and color grading from [IMAGE_2]. Apply this exact environment style around the jewelry piece from [IMAGE_1].
2. Ignore any jewelry, hands, mannequins, or models shown in [IMAGE_2] — use [IMAGE_2] only as an environment and lighting reference, never as a subject reference.
3. Keep the camera angle, framing, and composition of [IMAGE_1]'s jewelry piece unchanged while placing it into the [IMAGE_2] environment.
4. Erase any existing watermark, logo, or text overlay found in [IMAGE_2] completely — it must not appear in the output. Apply the logo from [IMAGE_3] as the only branding in the final image, scaled small and positioned in the bottom-right or top-center corner with refined opacity, matching the scene's lighting. The logo from [IMAGE_3] must never overlap the jewelry piece from [IMAGE_1] or cast a shadow.

ATTACHMENT ROLES:
- [IMAGE_1]: PRIMARY SUBJECT. The jewelry piece to preserve exactly and place into the new environment.
- [IMAGE_2]: ENVIRONMENT REFERENCE. Background, lighting, and material style source only. Not a subject reference.
- [IMAGE_3]: LOGO. Brand mark to apply as a small watermark. Never a subject or environment reference.
```

Run this exact string (and the other three role combinations) through your Phase 1 §4 regression set before it goes live — don't ship on the strength of this one example looking right.

---

## Model-budget note

If any provider in your fal.ai failover chain is base FLUX.1 Kontext (not Max) or another editing model with a hard prompt-length ceiling, count tokens on the fully assembled string per combination and per subtype count (multi-type "set" jobs are your longest case). Every clause above is written as a standalone numbered sentence specifically so you can drop the lowest-priority one (composition/framing repetition is usually safest to cut first) without leaving a broken reference behind, if you ever need to trim for a specific provider.
