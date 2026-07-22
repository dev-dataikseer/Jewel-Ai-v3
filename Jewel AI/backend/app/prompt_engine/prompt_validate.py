"""Admin save-time prompt validation (placeholders + Jinja hygiene)."""

from __future__ import annotations

import re
from typing import Any, Literal

from app.prompt_engine.fragment_defaults import PROMPT_PLACEHOLDERS

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
_JINJA_BLOCK_RE = re.compile(r"\{%.*?%\}", re.DOTALL)

Scope = Literal["master", "subject", "variant", "fragment", "preset"]

# Soft recommendations — missing these is a warning, not a hard error.
RECOMMENDED_BY_SCOPE: dict[str, frozenset[str]] = {
    "master": frozenset({"SUBTYPE_BLOCK"}),
    "subject": frozenset(),
    "variant": frozenset(),
    "fragment": frozenset(),
    "preset": frozenset(),
}


def extract_placeholders(text: str) -> list[str]:
    if not text:
        return []
    return list(dict.fromkeys(_PLACEHOLDER_RE.findall(text)))


def validate_prompt_text(
    text: str | None,
    *,
    scope: Scope = "master",
    workflow: str | None = None,
) -> dict[str, Any]:
    """Return validation payload for Admin UI (errors block save; warnings do not)."""
    content = text or ""
    errors: list[str] = []
    warnings: list[str] = []

    if _JINJA_BLOCK_RE.search(content):
        errors.append("Jinja control blocks ({% %}) are not allowed in stored prompts")

    found = extract_placeholders(content)
    unknown = [p for p in found if p not in PROMPT_PLACEHOLDERS]
    if unknown:
        errors.append(f"Unknown placeholder(s): {', '.join('{{' + u + '}}' for u in unknown)}")

    recommended = RECOMMENDED_BY_SCOPE.get(scope, frozenset())
    missing = sorted(recommended - set(found))
    if missing and scope == "master":
        warnings.append(
            "Recommended master placeholders missing: "
            + ", ".join("{{" + m + "}}" for m in missing)
            + " — engine may leave subtype empty unless insert_point is used"
        )

    # Rough char estimate vs typical Nano Banana / catalog budgets
    char_count = len(content)
    word_count = len(content.split()) if content.strip() else 0
    if word_count > 1200:
        warnings.append(f"Prompt is long ({word_count} words); model adapter may drop optional parts")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "placeholders_found": found,
        "unknown_placeholders": unknown,
        "char_count": char_count,
        "word_count": word_count,
        "scope": scope,
        "workflow": workflow,
        "allowed_placeholders": sorted(PROMPT_PLACEHOLDERS),
    }
