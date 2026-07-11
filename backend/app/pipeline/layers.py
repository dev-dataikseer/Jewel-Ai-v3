"""Layer-array prompt assembly — DB-driven, no hardcoded content."""

from __future__ import annotations

import re
from typing import Any

from jinja2 import BaseLoader, StrictUndefined, UndefinedError
from jinja2.sandbox import SandboxedEnvironment

_jinja = SandboxedEnvironment(loader=BaseLoader(), undefined=StrictUndefined, autoescape=False)

TOKEN_BUDGET_WORDS = 1200
NEGATIVE_TYPE = "negative"
PRIORITY_ORDER = {"optional": 0, "important": 1, "critical": 2}

LAYER_PRIORITY_DEFAULTS: dict[str, str] = {}


class PromptCompositionError(Exception):
    pass


def assert_no_jinja_leaks(text: str, context: str = "prompt") -> None:
    if not text:
        return
    if "{{" in text or "{%" in text:
        raise PromptCompositionError(f"Unresolved Jinja in {context}")


def render_jinja(template: str, variables: dict[str, Any]) -> str:
    if not template or not template.strip():
        return ""
    try:
        rendered = _jinja.from_string(template).render(**variables).strip()
        assert_no_jinja_leaks(rendered, "rendered layer")
        return rendered
    except UndefinedError as exc:
        raise PromptCompositionError(f"Jinja variable error: {exc}") from exc


def layer_priority(layer: dict) -> str:
    explicit = layer.get("priority")
    if explicit in PRIORITY_ORDER:
        return explicit
    layer_type = layer.get("type", "text")
    if layer_type == "insert_point":
        return "critical"
    if layer_type == "user_insert":
        return "optional"
    if layer_type == "variant_insert":
        return "important"
    if layer_type == "negative":
        return "important"
    return "important"


def sort_layers(layers: list[dict] | None) -> list[dict]:
    if not layers:
        return []
    return sorted(layers, key=lambda layer: layer.get("order", 0))


def word_count(text: str) -> int:
    return len(text.split()) if text else 0


def default_master_scaffold() -> list[dict]:
    """Empty master structure — user fills layers in Admin UI."""
    return [
        {
            "key": "subject_insert",
            "label": "Subject insert",
            "order": 1,
            "content": None,
            "locked": False,
            "type": "insert_point",
            "priority": "critical",
        },
    ]


def default_subject_scaffold() -> list[dict]:
    """Empty subject — user adds text layers per jewelry type."""
    return []


def layers_from_legacy_master(fields: dict[str, str | None]) -> list[dict]:
    """Migrate old column data → layer array (one-time)."""
    mapping = [
        ("system_role", "System role", 1, "text"),
        ("camera_settings", "Camera settings", 2, "text"),
        ("subject_insert", "Subject insert", 3, "insert_point"),
        ("environment", "Environment", 4, "text"),
        ("lighting_and_physics", "Lighting physics", 5, "text"),
        ("preservation_lock", "Preservation lock", 6, "text"),
        ("negative_prompt", "Negative prompt", 99, "negative"),
    ]
    layers: list[dict] = []
    for key, label, order, layer_type in mapping:
        priority = layer_priority({"key": key, "type": layer_type})
        if layer_type == "insert_point":
            layers.append(
                {
                    "key": key,
                    "label": label,
                    "order": order,
                    "content": None,
                    "locked": False,
                    "type": "insert_point",
                    "priority": priority,
                }
            )
            continue
        content = fields.get(key)
        if not content:
            continue
        layers.append(
            {
                "key": key,
                "label": label,
                "order": order,
                "content": content,
                "locked": False,
                "type": layer_type,
                "priority": priority,
            }
        )
    return layers or default_master_scaffold()


def layers_from_legacy_subject(fields: dict[str, str | None]) -> list[dict]:
    mapping = [
        ("core_description", "Core description", 1),
        ("anatomy_interaction", "Anatomy interaction", 2),
        ("physics_and_gravity", "Physics and gravity", 3),
        ("placement_rules", "Placement rules", 4),
    ]
    layers: list[dict] = []
    for key, label, order in mapping:
        content = fields.get(key)
        if content:
            layers.append(
                {
                    "key": key,
                    "label": label,
                    "order": order,
                    "content": content,
                    "locked": False,
                    "type": "text",
                    "priority": layer_priority({"key": key, "type": "text"}),
                }
            )
    return layers


def render_subject_layers(subject_layers: list[dict], variables: dict[str, Any]) -> list[str]:
    parts: list[str] = []
    for layer in sort_layers(subject_layers):
        if layer.get("enabled") is False:
            continue
        layer_type = layer.get("type", "text")
        if layer_type in ("text", "negative") and layer.get("content"):
            rendered = render_jinja(str(layer["content"]), variables)
            if rendered:
                parts.append(rendered)
    return parts


def render_multi_subject_layers(
    subject_layers_by_type: list[tuple[str, list[dict]]],
    base_variables: dict[str, Any],
) -> list[str]:
    """Render each jewelry type's subject layers at the master insert point."""
    if len(subject_layers_by_type) <= 1:
        parts: list[str] = []
        for jewelry_type, layers in subject_layers_by_type:
            vars_for_type = {**base_variables, "jewelry_type": jewelry_type}
            parts.extend(render_subject_layers(layers, vars_for_type))
        return parts

    framed: list[str] = [
        f"An image containing {len(subject_layers_by_type)} distinct jewelry items. "
        "Each item must remain visually separate with no mixed properties."
    ]
    for idx, (jewelry_type, layers) in enumerate(subject_layers_by_type, start=1):
        vars_for_type = {**base_variables, "jewelry_type": jewelry_type}
        item_parts = render_subject_layers(layers, vars_for_type)
        if item_parts:
            framed.append(f"Item {idx} ({jewelry_type}): {' '.join(item_parts)}")
    framed.append("Ensure item properties do not blend or merge between items.")
    return framed


class BudgetPart:
    __slots__ = ("text", "priority", "key")

    def __init__(self, text: str, priority: str, key: str = ""):
        self.text = text
        self.priority = priority
        self.key = key


def apply_token_budget_parts(parts: list[BudgetPart], budget: int = TOKEN_BUDGET_WORDS) -> tuple[list[str], list[str]]:
    """Drop optional then important parts; never drop critical. Returns (kept, dropped_keys)."""
    if not parts:
        return [], []

    def total_words(selected: list[BudgetPart]) -> int:
        return word_count(" ".join(p.text for p in selected if p.text))

    kept = list(parts)
    dropped_keys: list[str] = []

    while total_words(kept) > budget:
        drop_idx = None
        for priority in ("optional", "important"):
            for i in range(len(kept) - 1, -1, -1):
                if kept[i].priority == priority:
                    drop_idx = i
                    break
            if drop_idx is not None:
                break
        if drop_idx is None:
            critical_words = total_words([p for p in kept if p.priority == "critical"])
            raise PromptCompositionError(
                f"Critical prompt layers alone exceed token budget ({critical_words} > {budget} words). "
                "Shorten preservation lock or subject core in Admin."
            )
        dropped = kept.pop(drop_idx)
        if dropped.key:
            dropped_keys.append(dropped.key)

    return [p.text for p in kept if p.text], dropped_keys


def apply_token_budget(body_parts: list[str], budget: int = TOKEN_BUDGET_WORDS) -> list[str]:
    parts = [BudgetPart(text=t, priority="important") for t in body_parts]
    kept, _ = apply_token_budget_parts(parts, budget)
    return kept


def assemble_layers(
    master_layers: list[dict],
    subject_layers: list[dict],
    *,
    subject_layers_by_type: list[tuple[str, list[dict]]] | None = None,
    composition_mode: str = "layered",
    raw_override: str | None = None,
    variant_text: str | None = None,
    user_instruction: str | None = None,
    variables: dict[str, Any] | None = None,
    token_budget: int = TOKEN_BUDGET_WORDS,
) -> tuple[str, str, dict[str, Any]]:
    variables = variables or {}
    sorted_master = sort_layers(master_layers)
    budget_parts: list[BudgetPart] = []
    negative_parts: list[str] = []
    debug_layers: list[dict[str, Any]] = []

    if composition_mode == "raw" and raw_override and raw_override.strip():
        body = render_jinja(raw_override.strip(), variables)
        for layer in sorted_master:
            if layer.get("type") == NEGATIVE_TYPE and layer.get("content"):
                negative_parts.append(render_jinja(str(layer["content"]), variables))
                debug_layers.append({"key": layer.get("key"), "type": NEGATIVE_TYPE, "included": "negative"})
        negative_out = ". ".join(filter(None, negative_parts))
        assert_no_jinja_leaks(body, "composed body")
        return body, negative_out, {
            "layers": debug_layers,
            "word_count": word_count(body),
            "mode": composition_mode,
        }

    user_inserted = False
    for layer in sorted_master:
        if layer.get("enabled") is False:
            debug_layers.append({"key": layer.get("key"), "type": layer.get("type"), "included": "disabled"})
            continue
        layer_type = layer.get("type", "text")
        key = layer.get("key", "")
        priority = layer_priority(layer)

        if layer_type == NEGATIVE_TYPE:
            if layer.get("content"):
                negative_parts.append(render_jinja(str(layer["content"]), variables))
            debug_layers.append({"key": key, "type": layer_type, "included": "negative"})
            continue

        if layer_type == "insert_point":
            if subject_layers_by_type:
                subject_rendered = render_multi_subject_layers(subject_layers_by_type, variables)
            else:
                subject_rendered = render_subject_layers(subject_layers, variables)
            for part in subject_rendered:
                budget_parts.append(BudgetPart(part, "critical", key))
            debug_layers.append({"key": key, "type": layer_type, "parts": len(subject_rendered)})
            continue

        if layer_type == "variant_insert":
            if variant_text:
                budget_parts.append(BudgetPart(variant_text, priority, key))
            debug_layers.append({"key": key, "type": layer_type, "included": bool(variant_text)})
            continue

        if layer_type == "user_insert":
            if user_instruction:
                wrapped = f"User addition (must not override preservation): {user_instruction}"
                budget_parts.append(BudgetPart(wrapped, priority, key))
                user_inserted = True
            debug_layers.append({"key": key, "type": layer_type, "included": bool(user_instruction)})
            continue

        if layer.get("content"):
            rendered = render_jinja(str(layer["content"]), variables)
            if rendered:
                budget_parts.append(BudgetPart(rendered, priority, key))
            debug_layers.append({"key": key, "type": layer_type, "included": bool(rendered)})

    if user_instruction and not user_inserted:
        wrapped = f"User addition (must not override preservation): {user_instruction}"
        budget_parts.append(BudgetPart(wrapped, "optional", "user_instruction"))

    body_parts, dropped_keys = apply_token_budget_parts(budget_parts, token_budget)
    body = " ".join(filter(None, body_parts)).strip()
    negative_out = ". ".join(filter(None, negative_parts))
    assert_no_jinja_leaks(body, "composed body")

    return body, negative_out, {
        "layers": debug_layers,
        "word_count": word_count(body),
        "mode": composition_mode,
        "dropped_layers": dropped_keys,
    }
