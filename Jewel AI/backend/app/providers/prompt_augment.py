"""Backward-compatible prompt augment — delegates to prompt_engine attachments."""

from __future__ import annotations

from app.prompt_engine.attachments import ImageContext, append_attachments
from app.prompt_engine.document import PromptDocument, PromptPart
from app.prompt_engine.model_adapter import adapt_document


def augment_prompt_for_workflow(workflow: str, prompt: str, *, has_style_reference: bool = False) -> str:
    """Legacy string API used by older callers; prefer ``build_final_prompt``."""
    doc = PromptDocument(parts=[PromptPart(key="body", text=prompt, priority="critical", source="master")])
    ctx = ImageContext(
        has_product=True,
        has_style_reference=has_style_reference,
        has_portrait=workflow in ("JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"),
        image_count=2 if (has_style_reference or workflow in ("JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON")) else 1,
    )
    doc = append_attachments(doc, workflow, ctx)
    return adapt_document(doc).text
