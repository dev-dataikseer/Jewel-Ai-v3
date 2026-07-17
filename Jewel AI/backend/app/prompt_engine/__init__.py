"""
Prompt Engine — production prompt assembly for Jewel AI.

## Design decision (review outcome)

Keep Admin-managed layered master / subject / variant text (header → JSON layers).
That UX is correct for jewelry workflows: shared studio locks + per-SKU anatomy.

Replace model-blind string concatenation with:

1. Structured ``PromptDocument`` (ordered parts with priority + source)
2. Attachment layers from image roles (product / reference / portrait)
3. ``ModelAdapter`` that packs parts to each fal model's char budget and family rules

Prompt budgets are split into:
- **Official capacity** (``capacity.py``) — from provider docs when published
- **PromptProfile recommended** (``profiles.py``) — engineering packing heuristic

Backward compatible: ``compose_prompt`` and Admin TXT/header parsing stay;
generation goes through ``build_final_prompt``.

Note: ``build_final_prompt`` is lazy-imported to avoid a circular import with
``app.pipeline.composer`` (composer imports document types from this package).
"""

from __future__ import annotations

from typing import Any

from app.prompt_engine.document import FinalPrompt, PromptDocument, PromptPart

__all__ = [
    "FinalPrompt",
    "PromptDocument",
    "PromptPart",
    "build_final_prompt",
]


def __getattr__(name: str) -> Any:
    if name == "build_final_prompt":
        from app.prompt_engine.engine import build_final_prompt

        return build_final_prompt
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
