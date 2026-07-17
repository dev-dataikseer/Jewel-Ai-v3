"""Structured prompt document types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromptPart:
    """One ordered fragment of the final prompt."""

    key: str
    text: str
    priority: str = "important"  # critical | important | optional
    source: str = "master"  # master | subject | variant | user | attachment | preset


@dataclass
class PromptDocument:
    """Composable prompt before model-specific packing."""

    parts: list[PromptPart] = field(default_factory=list)
    negative_parts: list[str] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)

    def clone(self) -> "PromptDocument":
        return PromptDocument(
            parts=[PromptPart(p.key, p.text, p.priority, p.source) for p in self.parts],
            negative_parts=list(self.negative_parts),
            debug=dict(self.debug),
        )


@dataclass
class FinalPrompt:
    """Ready-to-send prompt + negative for a specific model."""

    text: str
    negative_prompt: str
    char_count: int
    max_chars: int | None
    dropped_keys: list[str] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)
    master_version_id: str | None = None
    subject_version_id: str | None = None
    variant_version_id: str | None = None
