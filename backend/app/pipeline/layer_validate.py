"""Validate prompt layer arrays before Admin save."""

from __future__ import annotations

import re

from fastapi import HTTPException
from jinja2 import meta

from app.pipeline.layers import _jinja, sort_layers

KNOWN_VARIABLES = {
    "workflow",
    "jewelry_type",
    "metal_type",
    "gemstone_type",
    "gemstone_target_color",
    "background_style",
    "lighting_style",
    "prompt_text",
    "variant_text",
}

INSERT_POINT_TYPES = {"insert_point"}


def _collect_layer_errors(layers: list[dict] | None, *, require_insert: bool) -> list[str]:
    errors: list[str] = []
    if not layers:
        if require_insert:
            errors.append("At least one layer is required")
        return errors

    sorted_layers = sort_layers(layers)
    keys: set[str] = set()
    orders: set[int] = set()
    has_insert = False

    for layer in sorted_layers:
        key = layer.get("key")
        if not key:
            errors.append("Layer missing key")
            continue
        if key in keys:
            errors.append(f"Duplicate layer key: {key}")
        keys.add(key)

        order = layer.get("order", 0)
        if order in orders:
            errors.append(f"Duplicate layer order: {order}")
        orders.add(order)

        layer_type = layer.get("type", "text")
        if layer_type in INSERT_POINT_TYPES:
            has_insert = True

        content = layer.get("content")
        if content and ("{{" in str(content) or "{%" in str(content)):
            try:
                ast = _jinja.parse(str(content))
                undefined = meta.find_undeclared_variables(ast) - KNOWN_VARIABLES
                if undefined:
                    errors.append(f"Unknown Jinja variable(s) in {key}: {', '.join(sorted(undefined))}")
            except Exception as exc:
                errors.append(f"Invalid Jinja syntax in {key}: {exc}")

    if require_insert and not has_insert:
        errors.append("Master template must include a subject insert_point layer")

    return errors


def validate_master_layers(layers: list[dict] | None) -> None:
    errors = _collect_layer_errors(layers, require_insert=True)
    if errors:
        raise HTTPException(status_code=400, detail={"layer_errors": errors})


def validate_subject_layers(layers: list[dict] | None) -> None:
    errors = _collect_layer_errors(layers, require_insert=False)
    if errors:
        raise HTTPException(status_code=400, detail={"layer_errors": errors})


def validate_no_jinja_leaks(text: str, label: str = "prompt") -> None:
    if text and (re.search(r"\{\{|\{%", text)):
        raise HTTPException(status_code=400, detail=f"Unresolved Jinja in {label}")
