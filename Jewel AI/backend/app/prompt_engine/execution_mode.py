"""Catalog Layer 3 execution modes — reference mirroring vs modern dynamic catalog.

Routed in Python from has_reference × has_logo flags (no dangling IMAGE_3).
Master/subject layers stay in Admin DB; this module only injects execution blocks.
"""

from __future__ import annotations

from typing import Literal

from app.prompt_engine.document import PromptDocument, PromptPart

EXECUTION_MODE_VERSION = "v1.0.0"

CATALOG_EXEC_WORKFLOWS = frozenset({"CATALOG_IMAGE", "BULK_GENERATION"})

ENVIRONMENT_POOL: list[str] = [
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

ExecutionModeName = Literal["reference_mirroring", "modern_dynamic_catalog"]


def build_branding_clause(
    has_logo: bool,
    *,
    mode: Literal["reference", "catalog"],
    logo_image_label: str | None = None,
) -> str:
    """Independent logo/reference branding text — never mentions a logo image unless has_logo."""
    if mode == "reference":
        if has_logo:
            label = logo_image_label or "[IMAGE_LOGO: LOGO]"
            return (
                "3. BRAND REPLACEMENT: Inspect the Reference Image for any existing watermark, "
                "logo, or text overlay. Erase it completely — it must not appear in the output. "
                f"Apply {label} as the sole branding, positioned as a discreet high-end "
                "commercial watermark (bottom-right or top-center), matching the scene's lighting "
                "and never overlapping the jewelry subject."
            )
        return (
            "3. BRAND CLEANUP: If the Reference Image contains any existing watermark, logo, "
            "or text overlay, erase it completely. The output must contain no branding of any kind."
        )

    # catalog / modern dynamic
    if has_logo:
        label = logo_image_label or "[IMAGE_LOGO: LOGO]"
        return (
            "3. BRAND APPLICATION: Apply "
            f"{label} as a discreet high-end commercial watermark "
            "(bottom-right or top-center). Match scene lighting; never overlap the jewelry subject; "
            "do not invent a different mark."
        )
    return (
        "3. BRANDING: Do not add any watermark, logo, shop name, or text overlay. "
        "The output must contain no branding of any kind."
    )


def _logo_label_from_index(logo_index: int | None) -> str | None:
    if logo_index is None:
        return None
    return f"[IMAGE_{logo_index}: LOGO]"


def build_execution_parts(
    *,
    has_reference: bool,
    has_logo: bool,
    environment: str | None = None,
    logo_index: int | None = None,
) -> tuple[list[PromptPart], ExecutionModeName, dict]:
    """Return Layer 3 PromptParts + mode name + debug snippet."""
    logo_label = _logo_label_from_index(logo_index) if has_logo else None
    branding = build_branding_clause(
        has_logo,
        mode="reference" if has_reference else "catalog",
        logo_image_label=logo_label,
    )

    if has_reference:
        text = (
            "EXECUTION MODE: REFERENCE MIRRORING\n"
            "1. ENVIRONMENT MIRRORING: Analyze [IMAGE_2: REFERENCE]. Extract and replicate its "
            "background architecture, surface material, lighting direction, shadow density, and "
            "color grading. Place the primary jewelry subject from [IMAGE_1] into this exact style "
            "of environment.\n"
            "2. SUBJECT ISOLATION: Ignore any jewelry, hands, or models shown in [IMAGE_2]. "
            "It is a style/environment reference only — never copy its subject matter.\n"
            f"{branding}"
        )
        parts = [
            PromptPart(
                key="exec_reference_mirror",
                text=text,
                priority="important",
                source="attachment",
            )
        ]
        return parts, "reference_mirroring", {"brandingHasLogo": has_logo}

    chosen = environment or ENVIRONMENT_POOL[0]
    branding_catalog = build_branding_clause(
        has_logo,
        mode="catalog",
        logo_image_label=logo_label,
    ).replace("3. BRAND", "4. BRAND", 1)
    text = (
        "EXECUTION MODE: MODERN DYNAMIC CATALOG\n"
        "1. MODERN LUXURY STANDARDS: Generate a fresh, ultra-modern editorial catalog setting. "
        "Strictly forbidden: velvet jewelry boxes, ring boxes, leather display stands, "
        "generic gradient studio backdrops, and any prop that resembles traditional retail packaging.\n"
        f"2. ASSIGNED ENVIRONMENT: {chosen}\n"
        "3. GROUNDING & PERSPECTIVE: The supporting surface plane must align with the jewelry's "
        "current resting orientation. Generate a deep, dense ambient-occlusion contact shadow "
        "anchoring the piece to the surface.\n"
        f"{branding_catalog}"
    )

    parts = [
        PromptPart(
            key="exec_modern_catalog",
            text=text,
            priority="important",
            source="attachment",
        )
    ]
    return parts, "modern_dynamic_catalog", {
        "brandingHasLogo": has_logo,
        "environmentChosen": chosen,
    }


def append_execution_mode(
    doc: PromptDocument,
    *,
    has_reference: bool,
    has_logo: bool,
    environment: str | None = None,
    logo_index: int | None = None,
) -> tuple[PromptDocument, ExecutionModeName, dict]:
    out = doc.clone()
    parts, mode, meta = build_execution_parts(
        has_reference=has_reference,
        has_logo=has_logo,
        environment=environment,
        logo_index=logo_index,
    )
    out.parts.extend(parts)
    out.debug["execution_mode"] = mode
    out.debug["execution_mode_version"] = EXECUTION_MODE_VERSION
    out.debug["execution_meta"] = meta
    return out, mode, meta
