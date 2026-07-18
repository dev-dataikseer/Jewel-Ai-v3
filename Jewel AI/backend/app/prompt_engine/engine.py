"""Orchestrate compose → execution mode → attachments → model-adapted final prompt."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from app.prompt_engine.attachments import ImageContext, append_attachments, role_index
from app.prompt_engine.document import FinalPrompt
from app.prompt_engine.execution_mode import (
    CATALOG_EXEC_WORKFLOWS,
    EXECUTION_MODE_VERSION,
    append_execution_mode,
)
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
    user_id: str | None = None,
    job_id: str | None = None,
) -> FinalPrompt:
    """Build a model-ready prompt from Admin layers + execution mode + image roles."""
    # Local import avoids circular import: composer → prompt_engine.document → (package)
    from app.pipeline.composer import compose_prompt_document
    from app.pipeline.validator import normalize_jewelry_types, parse_jewelry_types

    if model_spec is None and model_endpoint_id:
        from app.providers.model_catalog.registry import get_spec

        model_spec = get_spec(model_endpoint_id)

    composed = compose_prompt_document(db, inp)
    ctx = image_ctx or ImageContext()
    workflow = inp.workflow or "CATALOG_IMAGE"
    doc = composed.document

    environment_chosen: str | None = None
    execution_mode: str | None = None
    execution_meta: dict[str, Any] = {}

    if workflow in CATALOG_EXEC_WORKFLOWS:
        has_reference = bool(ctx.has_style_reference)
        has_logo = bool(ctx.has_logo)
        logo_index = role_index(ctx, "logo") if has_logo else None
        if not has_reference:
            from app.prompt_engine.environment_rotation import choose_environment

            environment_chosen = choose_environment(user_id, job_id)
        doc, execution_mode, execution_meta = append_execution_mode(
            doc,
            has_reference=has_reference,
            has_logo=has_logo,
            environment=environment_chosen,
            logo_index=logo_index,
        )
        if environment_chosen is None and execution_meta.get("environmentChosen"):
            environment_chosen = execution_meta.get("environmentChosen")

    doc = append_attachments(doc, workflow, ctx)
    final = adapt_document(
        doc,
        model_spec=model_spec,
        master_version_id=composed.master_version_id,
        subject_version_id=composed.subject_version_id,
        variant_version_id=composed.variant_version_id,
    )

    subtypes = normalize_jewelry_types(parse_jewelry_types(inp.jewelry_type))
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
        "hasReference": bool(ctx.has_style_reference),
        "hasLogo": bool(ctx.has_logo),
        "environmentChosen": environment_chosen,
        "subtypesIncluded": subtypes,
        "executionMode": execution_mode,
        "executionModeVersion": EXECUTION_MODE_VERSION if execution_mode else None,
    }
    return final
