"""Image-role attachment instructions (replaces ad-hoc prompt_augment concat)."""

from __future__ import annotations

from dataclasses import dataclass

from app.prompt_engine.document import PromptDocument, PromptPart


@dataclass(frozen=True)
class ImageContext:
    """Which assets are attached to the fal request."""

    has_product: bool = True
    has_style_reference: bool = False
    has_portrait: bool = False
    image_count: int = 1


def attachment_parts(workflow: str, ctx: ImageContext) -> list[PromptPart]:
    """Return short, non-duplicative attachment hints as optional/important parts."""
    parts: list[PromptPart] = []
    wf = workflow or ""

    if wf == "REFERENCE_STYLE_MATCH" and ctx.has_product and ctx.has_style_reference:
        parts.append(
            PromptPart(
                key="attach_style_ref",
                text=(
                    "ATTACHED IMAGES: Image 1 is the jewelry product — preserve its design exactly. "
                    "Image 2 is the style reference — match background, lighting, mood, and framing."
                ),
                priority="important",
                source="attachment",
            )
        )
    elif wf in ("JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON") and ctx.has_product and ctx.has_portrait:
        parts.append(
            PromptPart(
                key="attach_try_on",
                text=(
                    "ATTACHED IMAGES: Image 1 is the jewelry product. "
                    "Image 2 is the model or customer portrait. Place the jewelry naturally on the person."
                ),
                priority="important",
                source="attachment",
            )
        )
    elif wf in ("CATALOG_IMAGE", "BULK_GENERATION") and ctx.has_style_reference:
        parts.append(
            PromptPart(
                key="attach_catalog_theme",
                text=(
                    "ATTACHED IMAGES: Image 1 is the jewelry product — preserve geometry and materials. "
                    "Image 2 is the theme reference — match white/black studio presentation and framing consistency."
                ),
                priority="important",
                source="attachment",
            )
        )

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
