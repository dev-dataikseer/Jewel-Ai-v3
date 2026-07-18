"""Orchestrate compose → attachments → model-adapted final prompt."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from app.prompt_engine.attachments import ImageContext, append_attachments
from app.prompt_engine.document import FinalPrompt
from app.prompt_engine.model_adapter import adapt_document

if TYPE_CHECKING:
    from app.pipeline.composer import ComposeInput
    from app.providers.model_catalog.spec import ModelSpec


def build_final_prompt(
    db: Session,
    inp: "ComposeInput",
    *,
    model_spec: "ModelSpec | None" = None,
    model_endpoint_id: str | None = None,
    image_ctx: ImageContext | None = None,
) -> FinalPrompt:
    """Build a model-ready prompt from Admin layers + image roles + ModelSpec budget."""
    # Local import avoids circular import: composer → prompt_engine.document → (package)
    from app.pipeline.composer import compose_prompt_document

    if model_spec is None and model_endpoint_id:
        from app.providers.model_catalog.registry import get_spec

        model_spec = get_spec(model_endpoint_id)

    composed = compose_prompt_document(db, inp)
    ctx = image_ctx or ImageContext()
    doc = append_attachments(composed.document, inp.workflow or "CATALOG_IMAGE", ctx)
    final = adapt_document(
        doc,
        model_spec=model_spec,
        master_version_id=composed.master_version_id,
        subject_version_id=composed.subject_version_id,
        variant_version_id=composed.variant_version_id,
    )
    final.debug = {
        **final.debug,
        "workflow": inp.workflow,
        "jewelry_type": inp.jewelry_type,
        "model_endpoint_id": model_endpoint_id or (model_spec.endpoint_id if model_spec else None),
        "image_context": {
            "has_product": ctx.has_product,
            "has_style_reference": ctx.has_style_reference,
            "has_portrait": ctx.has_portrait,
            "has_logo": ctx.has_logo,
            "image_count": ctx.image_count,
            "roles": list(ctx.roles or []),
        },
    }
    return final
