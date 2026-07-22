"""Orchestrate compose → fidelity lock → execution mode → attachments → model-adapted final prompt."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.prompt_engine.attachments import ImageContext, append_attachments, role_index
from app.prompt_engine.document import FinalPrompt
from app.prompt_engine.execution_mode import (
    EXECUTION_MODE_VERSION,
    append_execution_mode,
    bookend_fidelity_lock,
)
from app.prompt_engine.model_adapter import adapt_document
from app.prompt_engine.workflow_resolve import (
    CATALOG_EXEC_WORKFLOWS,
    resolve_workflow,
)

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
    """Build a model-ready prompt from Admin layers + fragments + image roles.

    When Settings.prompt_profile_v2 is true, OR when V2 profiles exist for the
    workflow, uses JSON profile compose (two pages).
    """
    from app.prompt_engine.workflow_resolve import resolve_workflow as _resolve

    ctx_early = image_ctx
    has_ref = bool(ctx_early and (ctx_early.has_style_reference or ctx_early.has_portrait or ctx_early.has_logo))
    resolved_early = _resolve(
        inp.workflow,
        catalog_mode=getattr(inp, "catalog_mode", None),
        try_on_mode=getattr(inp, "try_on_mode", None),
        has_reference=bool(ctx_early.has_style_reference) if ctx_early else False,
    )
    use_v2 = get_settings().prompt_profile_v2
    if not use_v2:
        from app.models import PromptProfile

        mode = "with_reference" if has_ref else "without_reference"
        row = (
            db.query(PromptProfile)
            .filter(
                PromptProfile.workflow == resolved_early.workflow,
                PromptProfile.reference_mode == mode,
                PromptProfile.is_active.is_(True),
            )
            .first()
        )
        use_v2 = bool(row and row.active_version_id)

    if use_v2:
        from app.prompt_engine.profile_compose import build_final_prompt_v2

        return build_final_prompt_v2(
            db,
            inp,
            model_spec=model_spec,
            model_endpoint_id=model_endpoint_id,
            image_ctx=image_ctx,
            user_id=user_id,
            job_id=job_id,
        )

    from app.pipeline.composer import compose_prompt_document
    from app.pipeline.validator import normalize_jewelry_types, parse_jewelry_types

    if model_spec is None and model_endpoint_id:
        from app.providers.model_catalog.registry import get_spec

        model_spec = get_spec(model_endpoint_id)

    ctx = image_ctx or ImageContext()
    resolved = resolve_workflow(
        inp.workflow,
        catalog_mode=getattr(inp, "catalog_mode", None),
        try_on_mode=getattr(inp, "try_on_mode", None),
        has_reference=bool(ctx.has_style_reference),
    )
    inp_resolved = inp
    if resolved.workflow != (inp.workflow or ""):
        from dataclasses import replace

        try:
            inp_resolved = replace(
                inp,
                workflow=resolved.workflow,
                catalog_mode=resolved.catalog_mode or getattr(inp, "catalog_mode", None),
                try_on_mode=resolved.try_on_mode or getattr(inp, "try_on_mode", None),
            )
        except TypeError:
            inp.workflow = resolved.workflow  # type: ignore[misc]
            inp_resolved = inp

    composed = compose_prompt_document(db, inp_resolved)
    workflow = resolved.workflow
    doc = composed.document

    environment_chosen: str | None = None
    execution_mode: str | None = None
    execution_meta: dict[str, Any] = {}
    fragment_versions: dict[str, Any] = {}

    doc, fidelity_meta = bookend_fidelity_lock(doc, db=db)
    fragment_versions.update({k: v for k, v in fidelity_meta.items() if v})

    if workflow in CATALOG_EXEC_WORKFLOWS or workflow == "CATALOG_IMAGE":
        has_reference = bool(ctx.has_style_reference)
        has_logo = bool(ctx.has_logo)
        logo_index = role_index(ctx, "logo") if has_logo else None
        catalog_mode = resolved.catalog_mode or (
            "style_mood"
            if getattr(inp, "catalog_mode", None) == "style_mood"
            else ("reference_mirror" if has_reference else "modern")
        )
        if catalog_mode == "modern" and not has_reference:
            from app.prompt_engine.environment_rotation import choose_environment

            environment_chosen = choose_environment(user_id, job_id, db=db)
        doc, execution_mode, execution_meta = append_execution_mode(
            doc,
            has_reference=has_reference,
            has_logo=has_logo,
            environment=environment_chosen,
            logo_index=logo_index,
            catalog_mode=catalog_mode,
            db=db,
        )
        if environment_chosen is None and execution_meta.get("environmentChosen"):
            environment_chosen = execution_meta.get("environmentChosen")
        fragment_versions.update(execution_meta.get("fragmentVersions") or {})

    if workflow == "VIRTUAL_TRY_ON" and (resolved.try_on_mode or getattr(inp, "try_on_mode", None)) == "customer":
        from app.prompt_engine.fragment_defaults import TRYON_CUSTOMER_PRESERVE
        from app.prompt_engine.fragment_store import get_fragment_meta
        from app.prompt_engine.document import PromptPart

        meta = get_fragment_meta(db, TRYON_CUSTOMER_PRESERVE)
        if meta.get("text"):
            doc = doc.clone()
            doc.parts.append(
                PromptPart(
                    key="tryon_customer_preserve",
                    text=meta["text"],
                    priority="important",
                    source="attachment",
                )
            )
            fragment_versions[TRYON_CUSTOMER_PRESERVE] = meta.get("version_id")

    if workflow == "CUSTOM_PROMPT":
        from app.prompt_engine.custom_guard import sanitize_custom_change
        from app.prompt_engine.fragment_defaults import CUSTOM_PRESERVE, CUSTOM_REALISM
        from app.prompt_engine.fragment_store import get_fragment_meta
        from app.prompt_engine.document import PromptPart

        user_raw = inp.prompt_text
        cleaned, alter_hits = sanitize_custom_change(user_raw, db=db)
        if cleaned:
            doc = doc.clone()
            doc.parts.append(
                PromptPart(
                    key="custom_change",
                    text=f"CHANGE: {cleaned}",
                    priority="important",
                    source="user",
                )
            )
        for key in (CUSTOM_PRESERVE, CUSTOM_REALISM):
            meta = get_fragment_meta(db, key)
            if meta.get("text"):
                doc = doc.clone() if key == CUSTOM_PRESERVE else doc
                doc.parts.append(
                    PromptPart(
                        key=key.lower(),
                        text=meta["text"],
                        priority="critical",
                        source="attachment",
                    )
                )
                fragment_versions[key] = meta.get("version_id")
        execution_meta["customAlterHits"] = alter_hits

    if workflow == "BACKGROUND_REPLACEMENT":
        from app.prompt_engine.fragment_defaults import (
            BACKGROUND_SOURCE_GENERATED,
            BACKGROUND_SOURCE_REF,
        )
        from app.prompt_engine.fragment_store import get_fragment_text
        from app.prompt_engine.document import PromptPart

        if ctx.has_style_reference:
            src = get_fragment_text(db, BACKGROUND_SOURCE_REF)
        else:
            from app.prompt_engine.environment_rotation import choose_environment

            environment_chosen = choose_environment(user_id, job_id, db=db)
            src = get_fragment_text(
                db, BACKGROUND_SOURCE_GENERATED, {"CHOSEN_ENVIRONMENT": environment_chosen}
            )
        doc = doc.clone()
        doc.parts.append(
            PromptPart(
                key="background_source",
                text=f"INSTRUCTION background source: {src}",
                priority="important",
                source="attachment",
            )
        )

    doc = append_attachments(doc, workflow, ctx, db=db)
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
        "workflow": workflow,
        "legacyWorkflow": resolved.legacy_workflow,
        "catalogMode": resolved.catalog_mode,
        "tryOnMode": resolved.try_on_mode,
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
        "fragmentVersions": fragment_versions,
        "composePath": "legacy_v1",
    }
    return final
