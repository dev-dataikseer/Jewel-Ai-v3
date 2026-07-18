"""Image-role attachment instructions — fragment-backed (Admin-editable)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.prompt_engine.document import PromptDocument, PromptPart
from app.prompt_engine.fragment_defaults import (
    ATTACH_ARTIFACT_SCRUB,
    ATTACH_CATALOG_ROLE_MAP,
    ATTACH_LOGO,
    ATTACH_PRODUCT,
    ATTACH_TRY_ON,
)
from app.prompt_engine.fragment_store import get_fragment_text
from app.prompt_engine.workflow_resolve import CATALOG_EXEC_WORKFLOWS, TRY_ON_WORKFLOWS

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


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


def build_catalog_attachment_mapping(
    ctx: ImageContext,
    db: "Session | None" = None,
) -> PromptPart:
    """Layer 4 — Image N lines only for slots that are actually attached."""
    from app.prompt_engine.fragment_defaults import (
        ATTACH_ENVIRONMENT_REFERENCE,
        ATTACH_LOGO,
        ATTACH_PRIMARY_SUBJECT,
    )

    primary = get_fragment_text(db, ATTACH_PRIMARY_SUBJECT) or get_fragment_text(
        db, ATTACH_CATALOG_ROLE_MAP
    )
    theme_line = ""
    logo_line = ""
    if ctx.has_style_reference:
        idx = role_index(ctx, "theme") or 2
        theme_tpl = get_fragment_text(db, ATTACH_ENVIRONMENT_REFERENCE)
        if theme_tpl:
            # Rewrite Image 2 → actual index if needed
            theme_line = "\n" + theme_tpl.replace("Image 2", f"Image {idx}")
        else:
            theme_line = (
                f"\n- Image {idx}: ENVIRONMENT REFERENCE. Background, lighting, "
                "and material style source only. Not a subject reference."
            )
    if ctx.has_logo:
        idx = role_index(ctx, "logo")
        if idx is None:
            idx = 3 if ctx.has_style_reference else 2
        logo_tpl = get_fragment_text(db, ATTACH_LOGO, {"LOGO_IMAGE_INDEX": idx, "LOGO_LABEL": f"Image {idx}"})
        if logo_tpl:
            logo_line = "\n" + logo_tpl
        else:
            logo_line = (
                f"\n- Image {idx}: LOGO. Brand mark to apply as a small watermark. "
                "Never a subject or environment reference."
            )

    # Prefer composed catalog map if present
    text = get_fragment_text(
        db,
        ATTACH_CATALOG_ROLE_MAP,
        {"THEME_LINE": theme_line, "LOGO_LINE": logo_line},
    )
    if not text or "PRIMARY" not in text.upper():
        header = "ATTACHMENT ROLES & INSTRUCTIONS:"
        body = primary if primary.startswith("-") or primary.startswith("Image") else primary
        text = f"{header}\n{body}{theme_line}{logo_line}".strip()

    return PromptPart(
        key="attach_role_map",
        text=text,
        priority="important",
        source="attachment",
    )


def attachment_parts(
    workflow: str,
    ctx: ImageContext,
    db: "Session | None" = None,
) -> list[PromptPart]:
    """Return short, non-duplicative attachment hints as optional/important parts."""
    parts: list[PromptPart] = []
    wf = workflow or ""

    product_idx = role_index(ctx, "product") or 1
    theme_idx = role_index(ctx, "theme")
    portrait_idx = role_index(ctx, "portrait")

    if wf in CATALOG_EXEC_WORKFLOWS or wf == "REFERENCE_STYLE_MATCH":
        # REFERENCE_STYLE_MATCH is a legacy alias of catalog style_mood
        parts.append(build_catalog_attachment_mapping(ctx, db=db))
        parts.append(
            PromptPart(
                key="artifact_scrub",
                text=get_fragment_text(db, ATTACH_ARTIFACT_SCRUB),
                priority="optional",
                source="attachment",
            )
        )
        return parts

    if wf in TRY_ON_WORKFLOWS and ctx.has_product and ctx.has_portrait:
        p_idx = portrait_idx or 2
        parts.append(
            PromptPart(
                key="attach_try_on",
                text=get_fragment_text(
                    db,
                    ATTACH_TRY_ON,
                    {"PRODUCT_INDEX": product_idx, "PORTRAIT_INDEX": p_idx},
                ),
                priority="important",
                source="attachment",
            )
        )
    elif ctx.has_product and ctx.image_count >= 1 and not ctx.has_style_reference and not ctx.has_portrait:
        parts.append(
            PromptPart(
                key="attach_product",
                text=get_fragment_text(
                    db,
                    ATTACH_PRODUCT,
                    {"PRODUCT_INDEX": product_idx},
                ),
                priority="optional",
                source="attachment",
            )
        )
    elif ctx.has_style_reference and ctx.has_product and wf == "CATALOG_IMAGE":
        # style_mood catalog attachments covered by catalog role map when in CATALOG_EXEC
        pass

    if ctx.has_logo and wf not in CATALOG_EXEC_WORKFLOWS:
        idx = role_index(ctx, "logo")
        label = f"Image {idx}" if idx else "the shop logo reference image"
        parts.append(
            PromptPart(
                key="attach_logo",
                text=get_fragment_text(db, ATTACH_LOGO, {"LOGO_LABEL": label}),
                priority="important",
                source="attachment",
            )
        )

    return parts


def append_attachments(
    doc: PromptDocument,
    workflow: str,
    ctx: ImageContext,
    db: "Session | None" = None,
) -> PromptDocument:
    out = doc.clone()
    existing = " ".join(p.text for p in out.parts).lower()
    built = attachment_parts(workflow, ctx, db=db)
    for part in built:
        if part.key == "artifact_scrub":
            if "watermark" in existing and (
                "artifact" in existing or "overlay" in existing or "exclude" in existing
            ):
                continue
        out.parts.append(part)
    out.debug["attachments"] = [p.key for p in built]
    return out
