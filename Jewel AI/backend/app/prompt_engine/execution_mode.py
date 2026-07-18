"""Catalog Layer 3 execution modes — loads fragment text from DB (Admin-editable).

Python only routes has_reference × has_logo × catalog_mode and substitutes placeholders.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from app.prompt_engine.document import PromptDocument, PromptPart
from app.prompt_engine.fragment_defaults import (
    BRAND_CATALOG_NO_LOGO,
    BRAND_CATALOG_WITH_LOGO,
    BRAND_REF_NO_LOGO,
    BRAND_REF_WITH_LOGO,
    DEFAULT_ENVIRONMENT_POOL,
    EXEC_MODERN_CATALOG,
    EXEC_REFERENCE_MIRROR,
    EXEC_STYLE_MOOD,
    FIDELITY_LOCK,
    substitute,
)
from app.prompt_engine.fragment_store import get_environment_pool, get_fragment_meta, get_fragment_text
from app.prompt_engine.workflow_resolve import CATALOG_EXEC_WORKFLOWS, CatalogMode

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

EXECUTION_MODE_VERSION = "v2.0.0"

# Re-export for environment_rotation / tests that still import the name
ENVIRONMENT_POOL = DEFAULT_ENVIRONMENT_POOL

ExecutionModeName = Literal["reference_mirroring", "modern_dynamic_catalog", "style_mood"]


def build_branding_clause(
    has_logo: bool,
    *,
    mode: Literal["reference", "catalog"],
    logo_image_label: str | None = None,
    db: "Session | None" = None,
) -> str:
    """Independent logo/reference branding text from Admin fragments."""
    label = logo_image_label or "Image LOGO"
    if mode == "reference":
        key = BRAND_REF_WITH_LOGO if has_logo else BRAND_REF_NO_LOGO
    else:
        key = BRAND_CATALOG_WITH_LOGO if has_logo else BRAND_CATALOG_NO_LOGO
    return get_fragment_text(db, key, {"LOGO_LABEL": label})


def _logo_label_from_index(logo_index: int | None) -> str | None:
    if logo_index is None:
        return None
    return f"Image {logo_index}"


def resolve_catalog_mode(
    *,
    catalog_mode: CatalogMode | str | None,
    has_reference: bool,
) -> CatalogMode:
    if catalog_mode in ("modern", "reference_mirror", "style_mood"):
        return catalog_mode  # type: ignore[return-value]
    return "reference_mirror" if has_reference else "modern"


def _with_branding(template: str, branding: str, extra: dict[str, Any] | None = None) -> str:
    """Substitute placeholders; if template has no {{BRANDING_CLAUSE}}, append branding."""
    vars_ = {"BRANDING_CLAUSE": branding, **(extra or {})}
    text = substitute(template, vars_)
    if branding and branding.strip() and branding.strip() not in text:
        text = f"{text.rstrip()}\n{branding.strip()}"
    return text


def build_execution_parts(
    *,
    has_reference: bool,
    has_logo: bool,
    environment: str | None = None,
    logo_index: int | None = None,
    catalog_mode: CatalogMode | str | None = None,
    db: "Session | None" = None,
) -> tuple[list[PromptPart], ExecutionModeName, dict[str, Any]]:
    """Return Layer 3 PromptParts + mode name + debug snippet."""
    mode = resolve_catalog_mode(catalog_mode=catalog_mode, has_reference=has_reference)
    logo_label = _logo_label_from_index(logo_index) if has_logo else None
    brand_mode: Literal["reference", "catalog"] = (
        "reference" if mode in ("reference_mirror", "style_mood") else "catalog"
    )
    branding = build_branding_clause(
        has_logo,
        mode=brand_mode,
        logo_image_label=logo_label,
        db=db,
    )
    fragment_versions: dict[str, Any] = {}

    if mode == "style_mood":
        meta = get_fragment_meta(db, EXEC_STYLE_MOOD)
        fragment_versions[EXEC_STYLE_MOOD] = meta.get("version_id")
        text = _with_branding(meta["text"], branding)
        parts = [
            PromptPart(
                key="exec_style_mood",
                text=text,
                priority="important",
                source="attachment",
            )
        ]
        return parts, "style_mood", {"brandingHasLogo": has_logo, "fragmentVersions": fragment_versions}

    if mode == "reference_mirror":
        meta = get_fragment_meta(db, EXEC_REFERENCE_MIRROR)
        fragment_versions[EXEC_REFERENCE_MIRROR] = meta.get("version_id")
        text = _with_branding(meta["text"], branding)
        parts = [
            PromptPart(
                key="exec_reference_mirror",
                text=text,
                priority="important",
                source="attachment",
            )
        ]
        return parts, "reference_mirroring", {
            "brandingHasLogo": has_logo,
            "fragmentVersions": fragment_versions,
        }

    pool = get_environment_pool(db)
    chosen = environment or (pool[0] if pool else DEFAULT_ENVIRONMENT_POOL[0])
    meta = get_fragment_meta(db, EXEC_MODERN_CATALOG)
    fragment_versions[EXEC_MODERN_CATALOG] = meta.get("version_id")
    text = _with_branding(meta["text"], branding, {"CHOSEN_ENVIRONMENT": chosen})
    parts = [
        PromptPart(
            key="exec_modern_catalog",
            text=text,
            priority="important",
            source="attachment",
        )
    ]
    return parts, "modern_dynamic_catalog", {
        "brandingHasLogo": has_logo,
        "environmentChosen": chosen,
        "fragmentVersions": fragment_versions,
    }


def bookend_fidelity_lock(
    doc: PromptDocument,
    db: "Session | None" = None,
) -> tuple[PromptDocument, dict[str, Any]]:
    """Inject fidelity lock as first and last paragraphs."""
    meta = get_fragment_meta(db, FIDELITY_LOCK)
    lock = (meta.get("text") or "").strip()
    if not lock:
        return doc, {}
    out = doc.clone()
    # Avoid duplicating if master already starts with the same lock
    existing = " ".join(p.text for p in out.parts)
    if lock[:80] not in existing:
        out.parts.insert(
            0,
            PromptPart(key="fidelity_lock_head", text=lock, priority="critical", source="attachment"),
        )
    out.parts.append(
        PromptPart(key="fidelity_lock_tail", text=lock, priority="critical", source="attachment")
    )
    return out, {"fidelityLockVersionId": meta.get("version_id")}


def append_execution_mode(
    doc: PromptDocument,
    *,
    has_reference: bool,
    has_logo: bool,
    environment: str | None = None,
    logo_index: int | None = None,
    catalog_mode: CatalogMode | str | None = None,
    db: "Session | None" = None,
) -> tuple[PromptDocument, ExecutionModeName, dict]:
    out = doc.clone()
    parts, mode, meta = build_execution_parts(
        has_reference=has_reference,
        has_logo=has_logo,
        environment=environment,
        logo_index=logo_index,
        catalog_mode=catalog_mode,
        db=db,
    )
    out.parts.extend(parts)
    out.debug["execution_mode"] = mode
    out.debug["execution_mode_version"] = EXECUTION_MODE_VERSION
    out.debug["execution_meta"] = meta
    return out, mode, meta
