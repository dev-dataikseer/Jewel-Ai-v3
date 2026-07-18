"""Canonical workflow IDs + aliases for consolidated Studio surface.

Canonical generation workflows:
  CATALOG_IMAGE, VIRTUAL_TRY_ON, GEMSTONE_COLOR_CHANGE,
  BACKGROUND_REPLACEMENT, LUXURY_ENHANCEMENT, CUSTOM_PROMPT

Aliases (compat):
  BULK_GENERATION → CATALOG_IMAGE
  REFERENCE_STYLE_MATCH → CATALOG_IMAGE + catalogMode=style_mood
  JEWELRY_ON_MODEL → VIRTUAL_TRY_ON + tryOnMode=studio
  CUSTOMER_TRY_ON → VIRTUAL_TRY_ON + tryOnMode=customer
  VIRTUAL_TRY_ON (UI) → VIRTUAL_TRY_ON + tryOnMode from payload
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

CatalogMode = Literal["modern", "reference_mirror", "style_mood"]
TryOnMode = Literal["studio", "customer"]

CANONICAL_GENERATION_WORKFLOWS = frozenset(
    {
        "CATALOG_IMAGE",
        "VIRTUAL_TRY_ON",
        "GEMSTONE_COLOR_CHANGE",
        "BACKGROUND_REPLACEMENT",
        "LUXURY_ENHANCEMENT",
        "CUSTOM_PROMPT",
    }
)

# Legacy IDs still accepted on ingest; resolved before compose / allowlists.
LEGACY_WORKFLOW_ALIASES = frozenset(
    {
        "BULK_GENERATION",
        "REFERENCE_STYLE_MATCH",
        "JEWELRY_ON_MODEL",
        "CUSTOMER_TRY_ON",
    }
)

CATALOG_EXEC_WORKFLOWS = frozenset({"CATALOG_IMAGE", "BULK_GENERATION"})
TRY_ON_WORKFLOWS = frozenset({"VIRTUAL_TRY_ON", "JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"})
VTON_GARMENT_WORKFLOWS = TRY_ON_WORKFLOWS  # allowlist key for garment VTON models


@dataclass(frozen=True)
class ResolvedWorkflow:
    workflow: str
    catalog_mode: CatalogMode | None = None
    try_on_mode: TryOnMode | None = None
    legacy_workflow: str | None = None


def resolve_workflow(
    workflow: str | None,
    *,
    catalog_mode: str | None = None,
    try_on_mode: str | None = None,
    has_reference: bool | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> ResolvedWorkflow:
    """Map UI/legacy workflow + flags to a canonical ResolvedWorkflow."""
    raw = (workflow or "CATALOG_IMAGE").strip().upper()
    payload = raw_payload or {}

    # Explicit flags win over legacy ID inference
    cm = (catalog_mode or payload.get("catalog_mode") or payload.get("catalogMode") or "").strip().lower()
    tm = (try_on_mode or payload.get("try_on_mode") or payload.get("tryOnMode") or "").strip().lower()

    if raw in ("BULK_GENERATION", ""):
        return ResolvedWorkflow(
            workflow="CATALOG_IMAGE",
            catalog_mode=_infer_catalog_mode(cm, has_reference),
            legacy_workflow=raw or "BULK_GENERATION",
        )

    if raw == "REFERENCE_STYLE_MATCH":
        return ResolvedWorkflow(
            workflow="CATALOG_IMAGE",
            catalog_mode="style_mood",
            legacy_workflow=raw,
        )

    if raw == "JEWELRY_ON_MODEL":
        return ResolvedWorkflow(
            workflow="VIRTUAL_TRY_ON",
            try_on_mode="studio",
            legacy_workflow=raw,
        )

    if raw == "CUSTOMER_TRY_ON":
        return ResolvedWorkflow(
            workflow="VIRTUAL_TRY_ON",
            try_on_mode="customer",
            legacy_workflow=raw,
        )

    if raw == "VIRTUAL_TRY_ON":
        mode: TryOnMode = "customer" if tm == "customer" else "studio"
        return ResolvedWorkflow(workflow="VIRTUAL_TRY_ON", try_on_mode=mode)

    if raw == "CATALOG_IMAGE":
        return ResolvedWorkflow(
            workflow="CATALOG_IMAGE",
            catalog_mode=_infer_catalog_mode(cm, has_reference),
        )

    return ResolvedWorkflow(workflow=raw)


def _infer_catalog_mode(explicit: str, has_reference: bool | None) -> CatalogMode:
    if explicit in ("modern", "reference_mirror", "style_mood"):
        return explicit  # type: ignore[return-value]
    if has_reference:
        return "reference_mirror"
    return "modern"


def prompt_lookup_workflow(resolved: ResolvedWorkflow) -> str:
    """DB master/subject lookup key — prefers canonical; falls back to legacy if shells exist."""
    return resolved.workflow


def is_try_on(workflow: str | None) -> bool:
    return (workflow or "") in TRY_ON_WORKFLOWS


def is_catalog_exec(workflow: str | None) -> bool:
    return (workflow or "") in CATALOG_EXEC_WORKFLOWS
