"""Backward-compatible prompt augment — delegates to prompt_engine attachments."""

from __future__ import annotations

from app.prompt_engine.attachments import ImageContext, append_attachments
from app.prompt_engine.document import PromptDocument, PromptPart
from app.prompt_engine.model_adapter import adapt_document


from app.prompt_engine.workflow_resolve import is_try_on


def augment_prompt_for_workflow(workflow: str, prompt: str, *, has_style_reference: bool = False) -> str:
    """Legacy string API used by older callers; prefer ``build_final_prompt``."""
    doc = PromptDocument(parts=[PromptPart(key="body", text=prompt, priority="critical", source="master")])
    try_on = is_try_on(workflow)
    ctx = ImageContext(
        has_product=True,
        has_style_reference=has_style_reference,
        has_portrait=try_on,
        image_count=2 if (has_style_reference or try_on) else 1,
    )
    doc = append_attachments(doc, workflow, ctx)
    return adapt_document(doc).text
