# Jewel AI Studio — Production Prompt Library (Final, v1.0)

Everything from the architecture and research passes, consolidated into one seed-ready document. This supersedes the partial subtype lists in the earlier two files — all 14 jewelry types are written out in full here.

---

## 0. Backend constants

```python
RAW_JEWELRY_FIDELITY_LOCK = (
    "ABSOLUTE PRESERVATION LOCK: The jewelry piece shown in Image 1 must be reproduced "
    "with zero alteration to its physical identity. Do not change its metal color, "
    "gemstone color, gemstone count, facet cuts, prong or setting structure, engraving, "
    "surface texture, proportions, or scale. Do not smooth, sharpen, redesign, or "
    "reinterpret any part of the piece. Every pixel of the jewelry itself must trace "
    "back exactly to Image 1 — only its surroundings, lighting, and background may change."
)

SUBTYPE_ORDER = [
    "ring", "necklace", "earring_stud", "earring_drop", "earring_hoop",
    "bracelet", "bangle", "kara", "pendant", "watch", "brooch",
    "anklet", "cufflinks", "multiple_items",
]

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

`choose_environment()` (rotation against last-5-used per client) and `build_attachment_mapping()` are unchanged from the earlier pass — reuse them as-is.

---

## 1. MASTER_BASE_PROMPT (every workflow, every model)

```text
ROLE: You are a master commercial jewelry photographer and luxury retoucher.

CAMERA: 100mm macro lens, f/11 aperture, edge-to-edge sharpness on the jewelry piece from Image 1, crisp focus stacking on the subject, shallow depth of field on the background so it stays softly out of focus and never competes with the jewelry detail. Editorial print quality, high resolution.

LIGHTING: Soft, diffused studio lighting from large overhead softboxes with subtle fill, revealing gemstone clarity without harsh glare or blown highlights. Generate a dense, physically accurate contact shadow directly beneath the jewelry piece from Image 1, matching its exact geometry, anchoring it to the surface. Metal surfaces reflect the color and light of the surrounding environment realistically, without overexposure.

NEGATIVE PROMPT: 3d render, CGI, digital illustration, plastic texture, artificial AI glow, over-smoothed metal, warped band, distorted facets, melted prongs, floating object, hovering jewelry, ungrounded item, missing contact shadow, mismatched shadow direction, repetitive background, fixed default studio, cluttered background, busy patterns, neon colors, cartoon or painterly effect, blurred filigree, altered pattern density, redesigned structure, changed camera angle, forced perspective, cropped edges, off-center subject, velvet jewelry box, ring box, leather display stand, generic gradient studio backdrop, overlapping logo, distorted branding, watermark collision, duplicate watermark.
```

---

## 2. SUBTYPE_PROMPTS — all 14 types

```text
RING: The ring's shank rests flat against the supporting surface at its true point of contact. Generate a tight, dark contact shadow directly beneath the band, not a diffuse ambient shadow.

NECKLACE: The chain and pendant drape across the surface following natural gravity — no rigid or perfectly symmetrical draping. Each link casts a micro-shadow onto the surface beneath it.

EARRING_STUD: The stud sits flush against its resting surface (or the earlobe, in on-model workflows) with a tight, minimal contact shadow directly beneath it — studs do not dangle or sway. If a pair is present in Image 1, both studs match exactly in scale and orientation.

EARRING_DROP: The earring hangs from its post or hook with the drop element following natural vertical gravity. Generate a soft, elongated drop shadow beneath the lowest point of the piece. If a pair is present in Image 1, both drops match in scale, length, and swing angle.

EARRING_HOOP: The hoop's true diameter and wire thickness from Image 1 are preserved exactly. Position it either resting on its edge on a flat surface or suspended with the open gap at the post facing correctly. If a pair is present in Image 1, both hoops match in diameter and orientation.

BRACELET: The bracelet rests in a natural closed or slightly open curve consistent with how it was photographed in Image 1 — do not flatten it into a straight line.

BANGLE: The bangle keeps its true circular or oval cross-section from Image 1 with a consistent contact shadow along its lowest point.

KARA: The kara (a rigid, thick-profile cuff bangle) keeps its exact circular cross-section, thickness, and — if present — opening gap from Image 1. It rests on its lowest curve with a firm, well-defined contact shadow reflecting its metal weight; do not thin the profile or round it into a delicate bangle shape.

PENDANT: The pendant hangs from its bail with the front face oriented toward camera, exactly as in Image 1. Do not reorient the pendant face.

WATCH: The watch dial's face orientation, hands, and any visible text or markers from Image 1 stay exactly as photographed — do not regenerate or reinterpret dial details. The strap or bracelet band follows natural material behavior: metal bracelets hold rigid links, leather or fabric straps drape with soft gravity, consistent with the material shown in Image 1.

BROOCH: The brooch's pin mechanism, if visible in Image 1, stays exactly as photographed. Do not add or remove a garment/fabric mount unless one is already present in Image 1.

ANKLET: Same draping physics as necklace, scaled to a smaller circumference and positioned closer to the surface.

CUFFLINKS: Both cufflinks in a pair match exactly in design, scale, and orientation, front face toward camera. Preserve the back-post/toggle structure exactly as shown in Image 1 if visible.

MULTIPLE_ITEMS: When several distinct jewelry pieces appear together in Image 1 without one dominant type, preserve each piece's individual scale relative to the others exactly as photographed, and apply that piece's own subtype grounding rule above to each item independently. Arrange with enough negative space that no piece overlaps or obscures another.
```

Compose order and the "drop generic Multiple Items if specific types are also selected" rule from your `modal.txt` stay exactly as documented — `SUBTYPE_ORDER` above already reflects that sequence.

---

## 3. Workflow execution blocks

### 3.1 CATALOG_IMAGE / BULK_GENERATION — `fal-ai/nano-banana-pro/edit`

```text
{{EXECUTION_A_or_B}}
```
**A — Reference present:**
```text
EXECUTION MODE: REFERENCE ENVIRONMENT MATCH
1. Extract the background surface, materials, lighting direction, shadow density, and color grading from Image 2. Apply this exact environment style around the jewelry piece from Image 1.
2. Ignore any jewelry, hands, mannequins, or models shown in Image 2 — environment/lighting reference only, never a subject reference.
3. Keep the camera angle, framing, and composition of Image 1's jewelry piece unchanged while placing it into the Image 2 environment.
{{BRANDING_CLAUSE}}
```
**B — No reference:**
```text
EXECUTION MODE: MODERN CATALOG ENVIRONMENT
1. Place the jewelry piece from Image 1 into the following environment, generated fresh for this image: {{CHOSEN_ENVIRONMENT}}
2. Align the surface plane and horizon to the jewelry piece's current resting orientation from Image 1.
3. Never use a velvet jewelry box, ring box, leather display stand, mannequin, or generic gradient studio backdrop.
{{BRANDING_CLAUSE}}
```
**Branding clause (both branches):**
```text
# has_logo = True
Erase any existing watermark, logo, or text overlay found in Image 2 (if present) completely. Apply the logo from Image 3 (or Image 2 if no environment reference) as the only branding, scaled small, bottom-right or top-center, refined opacity matching scene lighting, never overlapping the jewelry piece.

# has_logo = False
The final image must contain no branding, watermark, or text of any kind. If Image 2 contains existing branding, erase it completely.
```

### 3.2 REFERENCE_STYLE_MATCH — `fal-ai/nano-banana-pro/edit`

```text
EXECUTION MODE: STYLE & MOOD MATCH ONLY
1. From Image 2, extract only lighting direction, color temperature, contrast level, and overall mood. Do not extract any object, background material, or composition from Image 2.
2. Apply this lighting and color mood to the jewelry piece from Image 1 in its own environment. Keep framing, angle, and composition of Image 1 unchanged.
{{BRANDING_CLAUSE}}
```
Negative prompt addition for this workflow only: `color cast on gemstones that alters true stone color, over-saturated grading, background elements copied from Image 2`.

### 3.3 BACKGROUND_REPLACEMENT — `fal-ai/flux-2-max/edit`

```text
EXECUTION MODE: BACKGROUND SWAP ONLY
1. Replace only the background behind the jewelry piece from Image 1. {{BACKGROUND_SOURCE}}
2. Do not change the jewelry piece's lighting, angle, or position. Regenerate the contact shadow only enough to match the new surface, keeping its density and shape consistent with the original.
```
```text
# has_reference = True
BACKGROUND_SOURCE = "Use the background surface and material shown in Image 2 exactly, cropped and scaled to fit behind the existing jewelry composition."
# has_reference = False
BACKGROUND_SOURCE = "Generate this background: {{CHOSEN_ENVIRONMENT}}"
```

### 3.4 GEMSTONE_COLOR_CHANGE — `fal-ai/flux-2-max/edit`

```text
EXECUTION MODE: GEMSTONE COLOR CHANGE (explicit exception to the fidelity lock)
1. Change only the color of the gemstone(s) in Image 1 to {{TARGET_COLOR}}. Every other attribute stays governed by the preservation lock in full: facet cuts, stone count, stone size, cut style, setting, prong structure, metal color, position, and lighting are unchanged.
2. Match the new gemstone color's refraction and internal light behavior to the original stone's cut and clarity — it must look physically correct for that cut, not flat or painted on.
```
`{{TARGET_COLOR}}`: pass a named, concrete color (`"a deep emerald green"`, `"a vivid ruby red"`), not a hex code.

### 3.5 LUXURY_ENHANCEMENT — `fal-ai/flux-pro/kontext`

```text
EXECUTION MODE: TECHNICAL POLISH ONLY
1. Increase micro-contrast and specular clarity on the metal surface and gemstone facets of the jewelry piece from Image 1 only.
2. Do not add reflections, environments, or elements absent from the original capture. Do not change the metal's hue — clarity and highlight crispness only.
3. Keep composition, angle, background, and lighting direction exactly as in Image 1.
```

### 3.6 CUSTOM_PROMPT — `openai/gpt-image-2/edit`

```text
CHANGE: {{USER_CUSTOM_INSTRUCTION}}

PRESERVE: The jewelry piece's exact geometry, facet cuts, metal color, gemstone color and clarity, proportions, and scale from Image 1, in every case, regardless of what the Change instruction requests. If Change conflicts with preserving the jewelry piece, apply it only to background, lighting, or composition — never to the jewelry piece's physical identity.

PHYSICAL REALISM: Single consistent light source, accurate contact shadow, correct perspective between the jewelry piece and its surroundings.
```
Backend pre-check: scan `{{USER_CUSTOM_INSTRUCTION}}` for jewelry-altering language (resize/recolor metal/change stone/redesign) before assembly; strip it or reroute to the Gemstone Color Change explicit-exception phrasing rather than letting free text silently fight the lock.

### 3.7 JEWELRY_ON_MODEL — recommended `fal-ai/nano-banana-pro/edit` (not FASHN — see note below)

```text
EXECUTION MODE: BODY-CORRECT COMPOSITING
1. Place the jewelry piece from Image 1 onto the model in Image 2, at the anatomically correct position for {{JEWELRY_TYPE}}: ring→finger, necklace/pendant→neck/collarbone, earring(any)→ear, bracelet/bangle/kara→wrist, watch→wrist, anklet→ankle, brooch→lapel/chest, cufflinks→cuff.
2. Match the jewelry's scale, perspective, and lighting to the model's pose and the scene's light direction.
3. Do not alter the model's face, body, pose, skin tone, or existing clothing. Do not alter the jewelry piece itself beyond the perspective/lighting match required to seat it naturally on the body.
```

### 3.8 CUSTOMER_TRY_ON — recommended `fal-ai/nano-banana-pro/edit` (same as 3.7, plus one line)

```text
Add: "Preserve the customer's photo exactly — do not retouch, smooth, or beautify their skin, face, or body. Only add the jewelry piece."
```

**Reroute note (unchanged finding, repeated here since it directly affects this seed data):** FASHN Try-On v1.6, your current default for both, doesn't support jewelry per FASHN's own documentation — its `category` param and training are garment-scoped. Point `JEWELRY_ON_MODEL` / `CUSTOMER_TRY_ON` at `nano-banana-pro/edit` with the block above; keep FASHN only for pure clothing-context shots.

---

## 4. Final assembly (bookended lock, every workflow)

```python
def build_final_prompt(job_data: dict, provider_metadata: dict) -> str:
    workflow = job_data["workflow"]
    image_roles = provider_metadata.get("imageRoles", {})
    has_reference = "reference" in image_roles
    has_logo = "logo" in image_roles or provider_metadata.get("logoMode") == "active"
    jewelry_types = job_data.get("jewelryTypes", [])

    parts = [RAW_JEWELRY_FIDELITY_LOCK, MASTER_BASE_PROMPT, get_subtype_prompt(jewelry_types)]
    parts.append(get_workflow_execution_block(workflow, has_reference, has_logo, job_data, provider_metadata))
    parts.append(build_attachment_mapping(has_reference, has_logo))
    parts.append(RAW_JEWELRY_FIDELITY_LOCK)  # recency repeat

    final_prompt = "\n\n".join(p for p in parts if p)

    provider_metadata["imageRoles"] = image_roles
    provider_metadata["logoMode"] = "active" if has_logo else "inactive"
    provider_metadata["promptDebug"] = {
        "workflow": workflow,
        "hasReference": has_reference,
        "hasLogo": has_logo,
        "subtypesIncluded": jewelry_types,
        "masterVersion": "v1.0",
    }
    return final_prompt
```

`get_workflow_execution_block` is a simple dispatch to §3.1–3.8 above keyed on `workflow`, each returning its already-composed text with `{{...}}` placeholders filled from `job_data`/`provider_metadata`.

This is the complete, seed-ready set — every workflow, every jewelry type, one shared fidelity lock, no dangling image references, no vague randomness left to the model.
