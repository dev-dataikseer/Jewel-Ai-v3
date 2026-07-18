"""Custom-prompt jewelry-altering language soft guard."""

from __future__ import annotations

import re

# Phrases that fight the fidelity lock when left in free-form Change text.
_ALTER_PATTERNS = re.compile(
    r"\b("
    r"resize|redesign|recolor|recolour|change\s+the\s+(metal|stone|gem|band)|"
    r"change\s+(metal|stone|gemstone)\s+color|make\s+it\s+(bigger|smaller)|"
    r"alter\s+the\s+(jewelry|piece|ring|necklace)|replace\s+the\s+(stone|gem)|"
    r"add\s+more\s+(stones|gems)|remove\s+(stones|gems|prongs)"
    r")\b",
    re.IGNORECASE,
)


def sanitize_custom_change(instruction: str | None) -> tuple[str | None, list[str]]:
    """Return cleaned instruction + list of matched alter phrases (for debug/warn)."""
    if not instruction:
        return None, []
    text = instruction.strip()
    if not text:
        return None, []
    matches = [m.group(0) for m in _ALTER_PATTERNS.finditer(text)]
    if not matches:
        return text, []
    # Soften: keep user intent but prefix a non-override reminder for the Change slot
    cleaned = _ALTER_PATTERNS.sub(
        lambda m: f"(do not apply jewelry-altering request: {m.group(0)})",
        text,
    )
    return cleaned.strip(), matches
