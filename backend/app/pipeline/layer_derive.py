"""Derive dynamic prompt layers from raw text and merge structural insert points."""

from __future__ import annotations

import re
from typing import Any

from app.pipeline.layers import sort_layers

HEADER_LINE_RE = re.compile(r"^([A-Z][^:\n]{1,80}):\s*(.*)$", re.MULTILINE)

WORKFLOWS_WITH_VARIANT_INSERT = {
    "GEMSTONE_COLOR_CHANGE",
    "BACKGROUND_REPLACEMENT",
    "LUXURY_ENHANCEMENT",
    "REFERENCE_STYLE_MATCH",
}

DEFAULT_STRUCTURAL_LAYERS = [
    {
        "key": "subject_insert",
        "label": "Subject insert",
        "type": "insert_point",
        "priority": "critical",
        "enabled": True,
        "is_system": True,
        "after_key": None,
    },
    {
        "key": "variant_insert",
        "label": "Variant insert",
        "type": "variant_insert",
        "priority": "important",
        "enabled": True,
        "is_system": True,
        "after_key": "subject_insert",
    },
    {
        "key": "user_insert",
        "label": "User insert",
        "type": "user_insert",
        "priority": "optional",
        "enabled": False,
        "is_system": True,
        "after_key": None,
    },
]


def slugify_key(label: str) -> str:
    return re.sub(r"^_|_$", "", re.sub(r"[^a-z0-9]+", "_", label.lower().strip()))


def _is_negative_header(label: str) -> bool:
    normalized = label.strip().upper()
    return normalized == "AVOID" or normalized.startswith("AVOID ")


def _layer_type_for_header(label: str) -> str:
    return "negative" if _is_negative_header(label) else "text"


def _default_priority(layer_type: str) -> str:
    if layer_type in ("insert_point", "variant_insert"):
        return "critical" if layer_type == "insert_point" else "important"
    if layer_type == "negative":
        return "important"
    if layer_type == "user_insert":
        return "optional"
    return "important"


def parse_labeled_sections(block: str) -> tuple[str, list[dict[str, Any]]]:
    """Parse raw text block into verbatim text and dynamically detected header layers."""
    raw_text = block.strip()
    if not raw_text:
        return "", []

    lines = block.splitlines()
    layers: list[dict[str, Any]] = []
    current_label: str | None = None
    current_key: str | None = None
    current_type = "text"
    buffer: list[str] = []
    preamble: list[str] = []
    order = 1

    def flush() -> None:
        nonlocal order, current_label, current_key, current_type, buffer
        if current_key and current_label:
            content = "\n".join(buffer).strip()
            layers.append(
                {
                    "key": current_key,
                    "label": current_label,
                    "description": None,
                    "order": order,
                    "enabled": True,
                    "content": content or None,
                    "locked": False,
                    "type": current_type,
                    "priority": _default_priority(current_type),
                    "settings": None,
                    "is_system": False,
                }
            )
            order += 1
        elif buffer and not current_key:
            preamble.extend(buffer)
        buffer = []
        current_label = None
        current_key = None
        current_type = "text"

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_key:
                buffer.append("")
            elif preamble or not layers:
                buffer.append("")
            continue

        header_match = HEADER_LINE_RE.match(stripped)
        if header_match:
            flush()
            label = header_match.group(1).strip()
            rest = header_match.group(2).strip()
            current_label = label
            current_key = slugify_key(label)
            current_type = _layer_type_for_header(label)
            buffer = [rest] if rest else []
        elif current_key:
            buffer.append(stripped)
        else:
            buffer.append(stripped)

    flush()

    if preamble:
        note = "\n".join(preamble).strip()
        if note:
            layers.insert(
                0,
                {
                    "key": "preamble",
                    "label": "Preamble",
                    "description": None,
                    "order": 0,
                    "enabled": True,
                    "content": note,
                    "locked": False,
                    "type": "text",
                    "priority": "optional",
                    "settings": None,
                    "is_system": False,
                },
            )
            for i, layer in enumerate(layers):
                if layer["key"] != "preamble":
                    layer["order"] = i + 1

    return raw_text, layers


def default_structural_config(workflow: str) -> list[dict[str, Any]]:
    """Default structural layer config for a workflow."""
    layers = [dict(DEFAULT_STRUCTURAL_LAYERS[0])]
    if workflow in WORKFLOWS_WITH_VARIANT_INSERT:
        layers.append(dict(DEFAULT_STRUCTURAL_LAYERS[1]))
    return layers


def merge_structural_layers(
    content_layers: list[dict[str, Any]],
    structural_config: list[dict[str, Any]] | None,
    *,
    scope: str = "master",
) -> list[dict[str, Any]]:
    """Inject enabled structural layers into content layers at configured positions."""
    if scope != "master":
        return sort_layers(content_layers)

    config = structural_config or [dict(DEFAULT_STRUCTURAL_LAYERS[0])]
    enabled_structural = [dict(s) for s in config if s.get("enabled", True)]
    if not enabled_structural:
        enabled_structural = [dict(DEFAULT_STRUCTURAL_LAYERS[0])]

    negative_layers = [layer for layer in content_layers if layer.get("type") == "negative"]
    text_layers = [layer for layer in content_layers if layer.get("type") not in ("negative",)]

    result: list[dict[str, Any]] = []
    order = 1

    def append_structural(layer_def: dict[str, Any]) -> None:
        nonlocal order
        result.append(
            {
                "key": layer_def["key"],
                "label": layer_def.get("label", layer_def["key"]),
                "description": layer_def.get("description"),
                "order": order,
                "enabled": layer_def.get("enabled", True),
                "content": None,
                "locked": True,
                "type": layer_def.get("type", "insert_point"),
                "priority": layer_def.get("priority") or _default_priority(layer_def.get("type", "insert_point")),
                "settings": layer_def.get("settings"),
                "is_system": True,
            }
        )
        order += 1

    # Place subject_insert after first two text layers when possible, else after first
    split_at = min(2, len(text_layers)) if text_layers else 0
    subject_insert = next((s for s in enabled_structural if s.get("type") == "insert_point"), None)
    variant_insert = next((s for s in enabled_structural if s.get("type") == "variant_insert"), None)
    user_insert = next((s for s in enabled_structural if s.get("type") == "user_insert"), None)
    other_structural = [
        s
        for s in enabled_structural
        if s.get("type") not in ("insert_point", "variant_insert", "user_insert")
    ]

    for i, layer in enumerate(text_layers):
        copied = dict(layer)
        copied["order"] = order
        copied.setdefault("enabled", True)
        copied.setdefault("is_system", False)
        result.append(copied)
        order += 1
        if subject_insert and i == split_at - 1:
            append_structural(subject_insert)
            if variant_insert:
                append_structural(variant_insert)

    if subject_insert and split_at == 0:
        append_structural(subject_insert)
        if variant_insert:
            append_structural(variant_insert)
    elif subject_insert and split_at >= len(text_layers):
        append_structural(subject_insert)
        if variant_insert:
            append_structural(variant_insert)

    for layer_def in other_structural:
        append_structural(layer_def)

    if user_insert and user_insert.get("enabled", False):
        append_structural(user_insert)

    for layer in negative_layers:
        copied = dict(layer)
        copied["order"] = max(order, 99)
        copied.setdefault("enabled", True)
        copied.setdefault("is_system", False)
        result.append(copied)

    return sort_layers(result)


def derive_layers_from_raw_text(
    raw_text: str | None,
    workflow: str,
    *,
    scope: str = "master",
    structural_config: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Parse raw prompt text into validated layer arrays."""
    text = (raw_text or "").strip()
    if not text:
        if scope == "master":
            return merge_structural_layers([], structural_config, scope=scope)
        return []

    _, content_layers = parse_labeled_sections(text)
    if scope == "master":
        return merge_structural_layers(content_layers, structural_config, scope=scope)
    return sort_layers(content_layers)


def assemble_raw_text_from_layers(layers: list[dict[str, Any]] | None) -> str:
    """Rebuild raw prompt text from content layers (excludes structural insert points)."""
    if not layers:
        return ""
    parts: list[str] = []
    for layer in sort_layers(layers):
        if layer.get("is_system") or layer.get("type") in (
            "insert_point",
            "variant_insert",
            "user_insert",
        ):
            continue
        if layer.get("enabled") is False:
            continue
        content = layer.get("content")
        if not content:
            continue
        label = layer.get("label") or layer.get("key", "")
        layer_type = layer.get("type", "text")
        if layer_type == "negative":
            parts.append(f"{label}: {content}")
        else:
            parts.append(f"{label}: {content}")
    return "\n\n".join(parts)
