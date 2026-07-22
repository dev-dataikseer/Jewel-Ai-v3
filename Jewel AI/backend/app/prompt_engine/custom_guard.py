"""Custom-prompt jewelry-altering language soft guard.

Patterns can be overridden via the Admin fragment CUSTOM_ALTER_GUARD
(one regex alternative per line, or a single |‑joined pattern). Falls back
to a built-in list when the fragment is empty.
"""

from __future__ import annotations

import re
from functools import lru_cache

from sqlalchemy.orm import Session

# Phrases that fight the fidelity lock when left in free-form Change text.
_DEFAULT_ALTER_PATTERNS = re.compile(
    r"\b("
    r"resize|redesign|recolor|recolour|change\s+the\s+(metal|stone|gem|band)|"
    r"change\s+(metal|stone|gemstone)\s+color|make\s+it\s+(bigger|smaller)|"
    r"alter\s+the\s+(jewelry|piece|ring|necklace)|replace\s+the\s+(stone|gem)|"
    r"add\s+more\s+(stones|gems)|remove\s+(stones|gems|prongs)"
    r")\b",
    re.IGNORECASE,
)


def _compile_from_fragment(text: str | None) -> re.Pattern[str] | None:
    if not text or not text.strip():
        return None
    lines = [
        ln.strip()
        for ln in text.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if not lines:
        return None
    # Allow either one line per alternative or a single |‑joined pattern
    if len(lines) == 1 and "|" in lines[0] and not lines[0].startswith("("):
        body = lines[0]
    else:
        body = "|".join(f"(?:{ln})" for ln in lines)
    try:
        return re.compile(rf"\b({body})\b", re.IGNORECASE)
    except re.error:
        return None


@lru_cache(maxsize=8)
def _cached_pattern(fragment_text: str) -> re.Pattern[str]:
    compiled = _compile_from_fragment(fragment_text)
    return compiled or _DEFAULT_ALTER_PATTERNS


def _alter_pattern(db: Session | None = None) -> re.Pattern[str]:
    if db is None:
        return _DEFAULT_ALTER_PATTERNS
    try:
        from app.prompt_engine.fragment_defaults import CUSTOM_ALTER_GUARD
        from app.prompt_engine.fragment_store import get_fragment_text

        text = get_fragment_text(db, CUSTOM_ALTER_GUARD) or ""
        if text.strip():
            return _cached_pattern(text)
    except Exception:
        pass
    return _DEFAULT_ALTER_PATTERNS


def sanitize_custom_change(
    instruction: str | None,
    *,
    db: Session | None = None,
) -> tuple[str | None, list[str]]:
    """Return cleaned instruction + list of matched alter phrases (for debug/warn)."""
    if not instruction:
        return None, []
    text = instruction.strip()
    if not text:
        return None, []
    pattern = _alter_pattern(db)
    matches = [m.group(0) for m in pattern.finditer(text)]
    if not matches:
        return text, []
    cleaned = pattern.sub(
        lambda m: f"(do not apply jewelry-altering request: {m.group(0)})",
        text,
    )
    return cleaned.strip(), matches
