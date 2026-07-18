"""Default prompt fragment copy — seeded into DB; runtime prefers active DB versions.

After seed, Admin edits are the source of truth. These defaults exist only for
bootstrap / empty-DB fallback (tests). Do not add new creative prose elsewhere.
"""

from __future__ import annotations

from typing import Any

# --- Fragment keys (frozen vocabulary) ---

FIDELITY_LOCK = "RAW_JEWELRY_FIDELITY_LOCK"
EXEC_REFERENCE_MIRROR = "EXEC_REFERENCE_MIRROR"
EXEC_MODERN_CATALOG = "EXEC_MODERN_CATALOG"
EXEC_STYLE_MOOD = "EXEC_STYLE_MOOD"
BRAND_REF_WITH_LOGO = "BRAND_REF_WITH_LOGO"
BRAND_REF_NO_LOGO = "BRAND_REF_NO_LOGO"
BRAND_CATALOG_WITH_LOGO = "BRAND_CATALOG_WITH_LOGO"
BRAND_CATALOG_NO_LOGO = "BRAND_CATALOG_NO_LOGO"
ATTACH_CATALOG_ROLE_MAP = "ATTACH_CATALOG_ROLE_MAP"
ATTACH_ARTIFACT_SCRUB = "ATTACH_ARTIFACT_SCRUB"
ATTACH_TRY_ON = "ATTACH_TRY_ON"
ATTACH_PRODUCT = "ATTACH_PRODUCT"
ATTACH_LOGO = "ATTACH_LOGO"
BACKGROUND_SOURCE_REF = "BACKGROUND_SOURCE_REF"
BACKGROUND_SOURCE_GENERATED = "BACKGROUND_SOURCE_GENERATED"
CUSTOM_PRESERVE = "CUSTOM_PRESERVE"
CUSTOM_REALISM = "CUSTOM_REALISM"
TRYON_CUSTOMER_PRESERVE = "TRYON_CUSTOMER_PRESERVE"
MULTI_ITEM_FRAME = "MULTI_ITEM_FRAME"
MULTI_ITEM_BLEND_GUARD = "MULTI_ITEM_BLEND_GUARD"
USER_ADDITION_WRAP = "USER_ADDITION_WRAP"
ENVIRONMENT_POOL = "ENVIRONMENT_POOL"

FRAGMENT_KEYS: list[str] = [
    FIDELITY_LOCK,
    EXEC_REFERENCE_MIRROR,
    EXEC_MODERN_CATALOG,
    EXEC_STYLE_MOOD,
    BRAND_REF_WITH_LOGO,
    BRAND_REF_NO_LOGO,
    BRAND_CATALOG_WITH_LOGO,
    BRAND_CATALOG_NO_LOGO,
    ATTACH_CATALOG_ROLE_MAP,
    ATTACH_ARTIFACT_SCRUB,
    ATTACH_TRY_ON,
    ATTACH_PRODUCT,
    ATTACH_LOGO,
    BACKGROUND_SOURCE_REF,
    BACKGROUND_SOURCE_GENERATED,
    CUSTOM_PRESERVE,
    CUSTOM_REALISM,
    TRYON_CUSTOMER_PRESERVE,
    MULTI_ITEM_FRAME,
    MULTI_ITEM_BLEND_GUARD,
    USER_ADDITION_WRAP,
    ENVIRONMENT_POOL,
]

FRAGMENT_LABELS: dict[str, str] = {
    FIDELITY_LOCK: "Raw Jewelry Fidelity Lock",
    EXEC_REFERENCE_MIRROR: "Execution — Reference Mirroring",
    EXEC_MODERN_CATALOG: "Execution — Modern Dynamic Catalog",
    EXEC_STYLE_MOOD: "Execution — Style Mood Match",
    BRAND_REF_WITH_LOGO: "Branding — Reference + Logo",
    BRAND_REF_NO_LOGO: "Branding — Reference Cleanup",
    BRAND_CATALOG_WITH_LOGO: "Branding — Catalog + Logo",
    BRAND_CATALOG_NO_LOGO: "Branding — Catalog No Logo",
    ATTACH_CATALOG_ROLE_MAP: "Attachment — Catalog Role Map",
    ATTACH_ARTIFACT_SCRUB: "Attachment — Artifact Scrub",
    ATTACH_TRY_ON: "Attachment — Try-On",
    ATTACH_PRODUCT: "Attachment — Product Only",
    ATTACH_LOGO: "Attachment — Logo",
    BACKGROUND_SOURCE_REF: "Background Source — From Reference",
    BACKGROUND_SOURCE_GENERATED: "Background Source — Generated",
    CUSTOM_PRESERVE: "Custom Prompt — Preserve Slot",
    CUSTOM_REALISM: "Custom Prompt — Physical Realism",
    TRYON_CUSTOMER_PRESERVE: "Try-On — Customer Photo Preserve",
    MULTI_ITEM_FRAME: "Multi-Item Frame Header",
    MULTI_ITEM_BLEND_GUARD: "Multi-Item Blend Guard",
    USER_ADDITION_WRAP: "User Addition Wrapper",
    ENVIRONMENT_POOL: "Environment Rotation Pool (JSON list)",
}

DEFAULT_ENVIRONMENT_POOL: list[str] = [
    "A matte travertine stone slab with soft architectural shadow lines crossing the surface at a low angle.",
    "Dark brushed concrete with a single directional light source casting a long, soft-edged shadow.",
    "Fluted cream marble with vertical channel grooves catching diffuse studio light.",
    "Caustic water reflections on a dark glass surface, with rippling light patterns playing across the background.",
    "Smooth river stones in graduated grey tones, arranged with negative space around the subject.",
    "Dark volcanic basalt with a fine mist of water droplets catching specular highlights.",
    "Raw unbleached silk drapery pooling softly beneath the subject, natural fiber texture visible.",
    "A frosted acrylic plinth lit from below with a cool rim light separating subject from background.",
    "Brushed champagne-gold metal surface with a soft gradient reflection of the jewelry piece.",
]

DEFAULT_FRAGMENTS: dict[str, str] = {
    FIDELITY_LOCK: (
        "ABSOLUTE PRESERVATION LOCK: The jewelry piece shown in Image 1 must be reproduced "
        "with zero alteration to its physical identity. Do not change its metal color, "
        "gemstone color, gemstone count, facet cuts, prong or setting structure, engraving, "
        "surface texture, proportions, or scale. Do not smooth, sharpen, redesign, or "
        "reinterpret any part of the piece. Every pixel of the jewelry itself must trace "
        "back exactly to Image 1 — only its surroundings, lighting, and background may change."
    ),
    EXEC_REFERENCE_MIRROR: (
        "EXECUTION MODE: REFERENCE MIRRORING\n"
        "1. ENVIRONMENT MIRRORING: Analyze Image 2. Extract and replicate its "
        "background architecture, surface material, lighting direction, shadow density, and "
        "color grading. Place the primary jewelry subject from Image 1 into this exact style "
        "of environment.\n"
        "2. SUBJECT ISOLATION: Ignore any jewelry, hands, or models shown in Image 2. "
        "It is a style/environment reference only — never copy its subject matter.\n"
        "{{BRANDING_CLAUSE}}"
    ),
    EXEC_MODERN_CATALOG: (
        "EXECUTION MODE: MODERN DYNAMIC CATALOG\n"
        "1. MODERN LUXURY STANDARDS: Generate a fresh, ultra-modern editorial catalog setting. "
        "Strictly forbidden: velvet jewelry boxes, ring boxes, leather display stands, "
        "generic gradient studio backdrops, and any prop that resembles traditional retail packaging.\n"
        "2. ASSIGNED ENVIRONMENT: {{CHOSEN_ENVIRONMENT}}\n"
        "3. GROUNDING & PERSPECTIVE: The supporting surface plane must align with the jewelry's "
        "current resting orientation. Generate a deep, dense ambient-occlusion contact shadow "
        "anchoring the piece to the surface.\n"
        "{{BRANDING_CLAUSE}}"
    ),
    EXEC_STYLE_MOOD: (
        "ROLE: You are a master commercial jewelry photographer matching a specific visual style.\n\n"
        "STYLE EXTRACTION: From Image 2, extract only its lighting direction, color temperature, "
        "contrast level, and overall mood — warm/cool grading, shadow softness, highlight intensity. "
        "Do not extract or copy any object, background material, or composition from Image 2, "
        "only its lighting and color character.\n\n"
        "APPLICATION: Apply this lighting and color mood to the jewelry piece from Image 1 in its "
        "own environment. Keep the framing, angle, and composition of Image 1 unchanged.\n\n"
        "{{BRANDING_CLAUSE}}\n\n"
        "NEGATIVE PROMPT: mismatched shadow direction, color cast on gemstones that alters true "
        "stone color, over-saturated grading, background elements copied from Image 2."
    ),
    BRAND_REF_WITH_LOGO: (
        "3. BRAND REPLACEMENT: Inspect the Reference Image for any existing watermark, "
        "logo, or text overlay. Erase it completely — it must not appear in the output. "
        "Apply {{LOGO_LABEL}} as the sole branding, positioned as a discreet high-end "
        "commercial watermark (bottom-right or top-center), matching the scene's lighting "
        "and never overlapping the jewelry subject."
    ),
    BRAND_REF_NO_LOGO: (
        "3. BRAND CLEANUP: If the Reference Image contains any existing watermark, logo, "
        "or text overlay, erase it completely. The output must contain no branding of any kind."
    ),
    BRAND_CATALOG_WITH_LOGO: (
        "3. BRAND APPLICATION: Apply {{LOGO_LABEL}} as a discreet high-end commercial watermark "
        "(bottom-right or top-center). Match scene lighting; never overlap the jewelry subject; "
        "do not invent a different mark."
    ),
    BRAND_CATALOG_NO_LOGO: (
        "3. BRANDING: Do not add any watermark, logo, shop name, or text overlay. "
        "The output must contain no branding of any kind."
    ),
    ATTACH_CATALOG_ROLE_MAP: (
        "ATTACHMENT ROLES & INSTRUCTIONS:\n"
        "- Image 1: PRIMARY SUBJECT. Extract ONLY the jewelry piece. "
        "Preserve 100% of its physical structure and pixels."
        "{{THEME_LINE}}"
        "{{LOGO_LINE}}"
    ),
    ATTACH_ARTIFACT_SCRUB: (
        "Exclude source watermarks, weight labels, price tags, and burned-in overlay text."
    ),
    ATTACH_TRY_ON: (
        "ATTACHED IMAGES: Image {{PRODUCT_INDEX}} is the jewelry product. "
        "Image {{PORTRAIT_INDEX}} is the model or customer portrait. "
        "Place the jewelry naturally on the person."
    ),
    ATTACH_PRODUCT: (
        "ATTACHED IMAGES: Image {{PRODUCT_INDEX}} is the jewelry product — "
        "preserve geometry, materials, and design exactly."
    ),
    ATTACH_LOGO: (
        "ATTACHED LOGO: {{LOGO_LABEL}} is the shop brand logo. "
        "Place it as a discreet commercial watermark (bottom-right or top-center). "
        "Do not stretch it, invent a different mark, or obscure the jewelry."
    ),
    BACKGROUND_SOURCE_REF: (
        "Use the background surface and material shown in Image 2 exactly, "
        "cropped and scaled to fit behind the existing jewelry composition."
    ),
    BACKGROUND_SOURCE_GENERATED: "Generate this background: {{CHOSEN_ENVIRONMENT}}",
    CUSTOM_PRESERVE: (
        "PRESERVE: The jewelry piece's exact geometry, facet cuts, metal color, gemstone color "
        "and clarity, proportions, and scale from Image 1, in every case, regardless of what the "
        "Change instruction above requests. If the Change instruction conflicts with preserving "
        "the jewelry piece itself, apply the Change only to background, lighting, or composition, "
        "and do not apply any part of it that would alter the jewelry piece's physical identity."
    ),
    CUSTOM_REALISM: (
        "PHYSICAL REALISM: Maintain a single consistent light source, an accurate contact shadow, "
        "and correct perspective between the jewelry piece and its surroundings."
    ),
    TRYON_CUSTOMER_PRESERVE: (
        "Preserve the customer's photo exactly — do not retouch, smooth, or beautify their skin, "
        "face, or body. Only add the jewelry piece."
    ),
    MULTI_ITEM_FRAME: "An image containing {{ITEM_COUNT}} distinct jewelry items.",
    MULTI_ITEM_BLEND_GUARD: "Ensure item properties do not blend across pieces.",
    USER_ADDITION_WRAP: "User addition (must not override preservation): {{USER_INSTRUCTION}}",
    ENVIRONMENT_POOL: "",  # stored as JSON list in prompt_text via seed
}


def substitute(template: str, variables: dict[str, Any]) -> str:
    """Replace {{KEY}} placeholders. Unknown keys left as empty string."""
    out = template or ""
    for key, value in variables.items():
        token = "{{" + key + "}}"
        out = out.replace(token, "" if value is None else str(value))
    # Clear any leftover known-empty optional lines
    while "{{" in out and "}}" in out:
        start = out.find("{{")
        end = out.find("}}", start)
        if start < 0 or end < 0:
            break
        out = out[:start] + out[end + 2 :]
    return out.strip()
