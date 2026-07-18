"""Image-role attachment instructions (replaces ad-hoc prompt_augment concat)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.prompt_engine.document import PromptDocument, PromptPart


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


def _role_index(ctx: ImageContext, role: str) -> int | None:
    for item in ctx.roles or []:
        if item.get("role") == role:
            try:
                return int(item["index"])
            except (KeyError, TypeError, ValueError):
                return None
    return None


def _logo_instruction(ctx: ImageContext) -> PromptPart | None:
    if not ctx.has_logo:
        return None
    idx = _role_index(ctx, "logo")
    label = f"Image {idx}" if idx else "the shop logo reference image"
    return PromptPart(
        key="attach_logo",
        text=(
            f"ATTACHED LOGO: {label} is the shop brand logo. "
            "Place it naturally in a tasteful position (corner, signage, tag, or subtle brand mark area). "
            "Do not stretch it across the frame, do not invent a different mark, "
            "and do not obscure the jewelry product."
        ),
        priority="important",
        source="attachment",
    )


def attachment_parts(workflow: str, ctx: ImageContext) -> list[PromptPart]:
    """Return short, non-duplicative attachment hints as optional/important parts."""
    parts: list[PromptPart] = []
    wf = workflow or ""

    product_idx = _role_index(ctx, "product") or 1
    theme_idx = _role_index(ctx, "theme")
    portrait_idx = _role_index(ctx, "portrait")

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
    elif wf in ("CATALOG_IMAGE", "BULK_GENERATION") and ctx.has_style_reference:
        t_idx = theme_idx or 2
        parts.append(
            PromptPart(
                key="attach_catalog_theme",
                text=(
                    f"ATTACHED IMAGES: Image {product_idx} is the jewelry product — preserve geometry and materials. "
                    f"Image {t_idx} is the theme reference — match white/black studio presentation and framing consistency."
                ),
                priority="important",
                source="attachment",
            )
        )
    elif ctx.has_product and ctx.image_count >= 1 and not ctx.has_style_reference and not ctx.has_portrait:
        # Generic product-only hint when other workflow-specific blocks do not apply
        if wf not in ("JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON", "REFERENCE_STYLE_MATCH"):
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

    logo_part = _logo_instruction(ctx)
    if logo_part:
        parts.append(logo_part)

    # Watermark scrub only when catalog/bulk and not already covered by master text
    if wf in ("CATALOG_IMAGE", "BULK_GENERATION"):
        parts.append(
            PromptPart(
                key="artifact_scrub",
                text="Exclude source watermarks, weight labels, price tags, and burned-in overlay text.",
                priority="optional",
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
