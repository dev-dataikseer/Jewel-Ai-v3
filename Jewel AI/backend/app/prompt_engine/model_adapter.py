"""Pack a PromptDocument for a specific fal ModelSpec."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.prompt_engine.document import FinalPrompt, PromptDocument, PromptPart
from app.prompt_engine.profiles import resolve_prompt_profile

if TYPE_CHECKING:
    from app.providers.model_catalog.spec import ModelSpec

PRIORITY_RANK = {"optional": 0, "important": 1, "critical": 2}


def _char_count(parts: list[PromptPart]) -> int:
    return len(" ".join(p.text for p in parts if p.text).strip())


def pack_parts(parts: list[PromptPart], max_chars: int | None) -> tuple[list[PromptPart], list[str]]:
    """Drop optional then important parts until under max_chars; never drop critical if alone."""
    if not max_chars or max_chars <= 0:
        return list(parts), []

    kept = [p for p in parts if p.text and p.text.strip()]
    dropped: list[str] = []

    while _char_count(kept) > max_chars:
        drop_idx = None
        for priority in ("optional", "important"):
            for i in range(len(kept) - 1, -1, -1):
                if kept[i].priority == priority:
                    drop_idx = i
                    break
            if drop_idx is not None:
                break
        if drop_idx is None:
            # Only critical left — hard truncate last critical text
            if not kept:
                break
            last = kept[-1]
            room = max_chars - _char_count(kept[:-1]) - 1
            if room < 40:
                dropped.append(last.key)
                kept.pop()
            else:
                cut = last.text[:room]
                for sep in (". ", "; ", "\n", " "):
                    idx = cut.rfind(sep)
                    if idx > room * 0.7:
                        cut = cut[: idx + len(sep)].rstrip()
                        break
                kept[-1] = PromptPart(last.key, cut.rstrip(".,; ") + "…", last.priority, last.source)
                dropped.append(f"{last.key}:truncated")
            break
        dropped.append(kept.pop(drop_idx).key)

    return kept, dropped


def adapt_document(
    doc: PromptDocument,
    *,
    model_spec: "ModelSpec | None" = None,
    omit_prompt: bool = False,
    master_version_id: str | None = None,
    subject_version_id: str | None = None,
    variant_version_id: str | None = None,
) -> FinalPrompt:
    """Produce the final prompt string for the selected model."""
    profile = resolve_prompt_profile(model_spec)

    if omit_prompt or (model_spec and model_spec.image.omit_prompt) or profile.omit_prompt:
        return FinalPrompt(
            text="",
            negative_prompt="",
            char_count=0,
            max_chars=0,
            dropped_keys=[p.key for p in doc.parts],
            debug={**doc.debug, "adapter": "omit_prompt", "profile": profile.name},
            master_version_id=master_version_id,
            subject_version_id=subject_version_id,
            variant_version_id=variant_version_id,
        )

    parts = list(doc.parts)
    if profile.prefer_short_subject:
        # Demote long master prose that isn't preservation/camera critical
        demoted: list[PromptPart] = []
        for p in parts:
            if p.source == "master" and p.priority == "important" and p.key not in (
                "preservation_lock",
                "preservation_lock_includes_composition_lock_read_carefully",
                "camera_rendering",
                "subject_insert",
            ):
                demoted.append(PromptPart(p.key, p.text, "optional", p.source))
            else:
                demoted.append(p)
        parts = demoted

    max_chars = profile.max_chars
    # Profile already clamps recommended vs official; do not double-clamp with raw seed max.

    kept, dropped = pack_parts(parts, max_chars)
    text = " ".join(p.text.strip() for p in kept if p.text).strip()
    negative = ". ".join(dict.fromkeys(filter(None, doc.negative_parts)))

    return FinalPrompt(
        text=text,
        negative_prompt=negative,
        char_count=len(text),
        max_chars=max_chars,
        dropped_keys=dropped,
        debug={
            **doc.debug,
            "adapter": "pack_parts",
            "profile": profile.name,
            "kept_keys": [p.key for p in kept],
            "dropped_keys": dropped,
            "char_count": len(text),
            "max_chars": max_chars,
            "recommended_max_chars": profile.max_chars,
            "official_max_chars": profile.official_max_chars,
            "official_status": profile.official_status,
            "official_note": profile.official_note,
        },
        master_version_id=master_version_id,
        subject_version_id=subject_version_id,
        variant_version_id=variant_version_id,
    )
