"""Image-role attachment instructions (replaces ad-hoc prompt_augment concat)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.prompt_engine.document import PromptDocument, PromptPart
from app.prompt_engine.execution_mode import CATALOG_EXEC_WORKFLOWS


@dataclass(frozen=True)
class ImageContext:
    """Which assets are attached to the fal request."""

    has_product: bool = True
    has_style_reference: bool = False
    has_portrait: bool = False
    has_logo: bool = False
    image_count: int = 1
    # Optional explicit slot map: [{"index": 1, "role": "product"}, ...]
    roles: list[dict[str, Any]] = field(default_factory=list)


def role_index(ctx: ImageContext, role: str) -> int | None:
    for item in ctx.roles or []:
        if item.get("role") == role:
            try:
                return int(item["index"])
            except (KeyError, TypeError, ValueError):
                return None
    return None


def build_catalog_attachment_mapping(ctx: ImageContext) -> PromptPart:
    """Layer 4 — IMAGE_N lines only for slots that are actually attached."""
    lines = [
        "ATTACHMENT ROLES & INSTRUCTIONS:",
        "- [IMAGE_1]: PRIMARY SUBJECT. Extract ONLY the jewelry piece. "
        "Preserve 100% of its physical structure and pixels.",
    ]
    if ctx.has_style_reference:
        idx = role_index(ctx, "theme") or 2
        lines.append(
            f"- [IMAGE_{idx}]: REFERENCE ENVIRONMENT. Use ONLY for background, lighting, "
            "and style replication. Ignore any jewelry shown in this image."
        )
    if ctx.has_logo:
        idx = role_index(ctx, "logo")
        if idx is None:
            idx = 3 if ctx.has_style_reference else 2
        lines.append(
            f"- [IMAGE_{idx}]: COMPANY LOGO. Use solely as a clean, secondary watermark "
            "or brand overlay (bottom-right or top-center). Never invent a different mark "
            "and never overlap the jewelry subject."
        )
    return PromptPart(
        key="attach_role_map",
        text="\n".join(lines),
        priority="important",
        source="attachment",
    )


def attachment_parts(workflow: str, ctx: ImageContext) -> list[PromptPart]:
    """Return short, non-duplicative attachment hints as optional/important parts."""
    parts: list[PromptPart] = []
    wf = workflow or ""

    product_idx = role_index(ctx, "product") or 1
    theme_idx = role_index(ctx, "theme")
    portrait_idx = role_index(ctx, "portrait")

    if wf in CATALOG_EXEC_WORKFLOWS:
        parts.append(build_catalog_attachment_mapping(ctx))
        # Artifact scrub when master does not already cover it
        parts.append(
            PromptPart(
                key="artifact_scrub",
                text="Exclude source watermarks, weight labels, price tags, and burned-in overlay text.",
                priority="optional",
                source="attachment",
            )
        )
        return parts

    if wf == "REFERENCE_STYLE_MATCH" and ctx.has_product and ctx.has_style_reference:
        t_idx = theme_idx or 2
        parts.append(
            PromptPart(
                key="attach_style_ref",
                text=(
                    f"ATTACHED IMAGES: Image {product_idx} is the jewelry product — preserve its design exactly. "
                    f"Image {t_idx} is the style reference — match background, lighting, mood, and framing."
                ),
                priority="important",
                source="attachment",
            )
        )
    elif wf in ("JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON") and ctx.has_product and ctx.has_portrait:
        p_idx = portrait_idx or 2
        parts.append(
            PromptPart(
                key="attach_try_on",
                text=(
                    f"ATTACHED IMAGES: Image {product_idx} is the jewelry product. "
                    f"Image {p_idx} is the model or customer portrait. Place the jewelry naturally on the person."
                ),
                priority="important",
                source="attachment",
            )
        )
    elif ctx.has_product and ctx.image_count >= 1 and not ctx.has_style_reference and not ctx.has_portrait:
        parts.append(
            PromptPart(
                key="attach_product",
                text=(
                    f"ATTACHED IMAGES: Image {product_idx} is the jewelry product — "
                    "preserve geometry, materials, and design exactly."
                ),
                priority="optional",
                source="attachment",
            )
        )

    # Logo line for non-catalog workflows when logo is in the packet
    if ctx.has_logo and wf not in CATALOG_EXEC_WORKFLOWS:
        idx = role_index(ctx, "logo")
        label = f"[IMAGE_{idx}: LOGO]" if idx else "the shop logo reference image"
        parts.append(
            PromptPart(
                key="attach_logo",
                text=(
                    f"ATTACHED LOGO: {label} is the shop brand logo. "
                    "Place it as a discreet commercial watermark (bottom-right or top-center). "
                    "Do not stretch it, invent a different mark, or obscure the jewelry."
                ),
                priority="important",
                source="attachment",
            )
        )

    return parts


def append_attachments(doc: PromptDocument, workflow: str, ctx: ImageContext) -> PromptDocument:
    out = doc.clone()
    existing = " ".join(p.text for p in out.parts).lower()
    for part in attachment_parts(workflow, ctx):
        if part.key == "artifact_scrub":
            if "watermark" in existing and ("artifact" in existing or "overlay" in existing or "exclude" in existing):
                continue
        out.parts.append(part)
    out.debug["attachments"] = [p.key for p in attachment_parts(workflow, ctx)]
    return out
