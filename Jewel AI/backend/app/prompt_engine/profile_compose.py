"""Prompt Profile V2 compose: JSON key→value sections, two pages (with/without reference).

No {{PLACEHOLDERS}}. No shared fragments. Image roles are labeled instructions.
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    PromptImageRole,
    PromptJewelrySection,
    PromptJewelrySectionVersion,
    PromptProfile,
    PromptProfileVersion,
    PromptVariant,
    PromptVariantVersion,
    StylePreset,
)
from app.pipeline.composer import VARIANT_FIELD_MAP, ComposeInput, slugify
from app.pipeline.validator import normalize_jewelry_types, parse_jewelry_types, sanitize_user_prompt
from app.prompt_engine.attachments import ImageContext, role_index
from app.prompt_engine.document import FinalPrompt, PromptDocument, PromptPart
from app.prompt_engine.workflow_resolve import resolve_workflow

REF_WITHOUT = "without_reference"
REF_WITH = "with_reference"

# Keys dropped when the matching image is not attached
CONDITIONAL_KEYS = {
    "REFERENCE_USE": "theme",
    "STYLE_REFERENCE": "theme",
    "PORTRAIT_USE": "portrait",
    "LOGO_USE": "logo",
    "BRANDING": "logo",
}

IMAGE_ROLE_ORDER = ("product", "theme", "portrait", "logo")

DEFAULT_IMAGE_ROLES: dict[str, tuple[str, str]] = {
    "product": (
        "Product",
        "Image {index} is the primary jewelry subject. Extract only the jewelry. "
        "Preserve structure, metal, gemstones, and proportions exactly.",
    ),
    "theme": (
        "Style / environment reference",
        "Image {index} is the environment and lighting reference. Style only — "
        "do not copy jewelry or subjects from it.",
    ),
    "portrait": (
        "Portrait / person",
        "Image {index} is the person for virtual try-on. Preserve face, skin, hair, "
        "and body identity. Place the jewelry naturally on the correct anatomy.",
    ),
    "logo": (
        "Logo",
        "Image {index} is the company logo. Apply as a small discreet watermark. "
        "Never overlap the jewelry. Never invent a logo if none is provided.",
    ),
}

NEGATIVE_KEY_RE = re.compile(r"^NEGATIVE(\s+PROMPT)?$", re.I)


@dataclass
class ProfileComposeResult:
    document: PromptDocument
    profile_version_id: str | None = None
    jewelry_version_id: str | None = None
    variant_version_id: str | None = None
    reference_mode: str = REF_WITHOUT
    sections: dict[str, str] = field(default_factory=dict)
    debug: dict[str, Any] = field(default_factory=dict)


def has_secondary_images(ctx: ImageContext) -> bool:
    """True when a theme/style or portrait reference is attached (logo alone is branding, not reference)."""
    return bool(ctx.has_style_reference or ctx.has_portrait)


def resolve_reference_mode(ctx: ImageContext) -> str:
    return REF_WITH if has_secondary_images(ctx) else REF_WITHOUT


def serialize_sections(sections: dict[str, str]) -> tuple[str, list[str]]:
    """Serialize KEY: value blocks. Returns (prompt_text, negative_parts)."""
    positives: list[str] = []
    negatives: list[str] = []
    for key, value in sections.items():
        text = (value or "").strip()
        if not text:
            continue
        if NEGATIVE_KEY_RE.match(key.strip()):
            negatives.append(text)
            continue
        positives.append(f"{key}: {text}" if not text.upper().startswith(key.upper() + ":") else text)
    return "\n\n".join(positives).strip(), negatives


def parse_header_text(raw: str) -> dict[str, str]:
    """Parse 'HEADER: body' multi-line blocks into an ordered dict."""
    text = (raw or "").strip()
    if not text:
        return {}
    # Already JSON-like single blob?
    sections: dict[str, str] = {}
    header_re = re.compile(r"^([A-Z][A-Z0-9 /_\-]{0,80}):\s*(.*)$")
    current_key: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal current_key, buf
        if current_key is not None:
            sections[current_key] = "\n".join(buf).strip()
        current_key = None
        buf = []

    for line in text.splitlines():
        m = header_re.match(line.strip()) if line.strip() else None
        if m and len(m.group(1)) <= 80:
            flush()
            current_key = m.group(1).strip()
            rest = m.group(2) or ""
            buf = [rest] if rest else []
        else:
            if current_key is None:
                current_key = "BODY"
                buf = []
            buf.append(line)
    flush()
    return sections


def load_profile(
    db: Session,
    workflow: str,
    reference_mode: str,
) -> tuple[PromptProfile | None, PromptProfileVersion | None]:
    profile = (
        db.query(PromptProfile)
        .filter(
            PromptProfile.workflow == workflow,
            PromptProfile.reference_mode == reference_mode,
            PromptProfile.is_active.is_(True),
        )
        .first()
    )
    if not profile or not profile.active_version_id:
        return profile, None
    ver = (
        db.query(PromptProfileVersion)
        .filter(PromptProfileVersion.id == profile.active_version_id)
        .first()
    )
    return profile, ver


def load_jewelry(
    db: Session,
    workflow: str,
    jewelry_type: str,
) -> tuple[PromptJewelrySection | None, PromptJewelrySectionVersion | None]:
    section = (
        db.query(PromptJewelrySection)
        .filter(
            PromptJewelrySection.workflow == workflow,
            PromptJewelrySection.jewelry_type == jewelry_type,
            PromptJewelrySection.is_active.is_(True),
        )
        .first()
    )
    if not section or not section.active_version_id:
        # Fall back to CATALOG_IMAGE jewelry if workflow-specific missing
        if workflow != "CATALOG_IMAGE":
            return load_jewelry(db, "CATALOG_IMAGE", jewelry_type)
        return section, None
    ver = (
        db.query(PromptJewelrySectionVersion)
        .filter(PromptJewelrySectionVersion.id == section.active_version_id)
        .first()
    )
    return section, ver


def jewelry_content_nonempty(content_json: dict | None) -> bool:
    if not content_json or not isinstance(content_json, dict):
        return False
    return any(str(v).strip() for v in content_json.values() if v is not None)


def jewelry_type_has_prompt(db: Session, workflow: str, jewelry_type: str) -> bool:
    _sec, jver = load_jewelry(db, workflow, jewelry_type)
    return bool(jver and jewelry_content_nonempty(jver.content_json))


def should_use_profile_v2_compose(
    db: Session,
    *,
    workflow: str,
    jewelry_type: str | None = None,
    has_reference: bool = False,
    prompt_profile_v2_flag: bool | None = None,
) -> bool:
    """Match job compose and Admin preview: V2 when flag, profile, or non-empty jewelry."""
    from app.config import get_settings

    if prompt_profile_v2_flag is None:
        prompt_profile_v2_flag = get_settings().prompt_profile_v2
    if prompt_profile_v2_flag:
        return True

    wf = workflow.upper()
    mode = REF_WITH if has_reference else REF_WITHOUT
    row = (
        db.query(PromptProfile)
        .filter(
            PromptProfile.workflow == wf,
            PromptProfile.reference_mode == mode,
            PromptProfile.is_active.is_(True),
        )
        .first()
    )
    if row and row.active_version_id:
        return True

    if jewelry_type:
        for jt in normalize_jewelry_types(parse_jewelry_types(jewelry_type)):
            if jewelry_type_has_prompt(db, wf, jt):
                return True
    return False


def load_variant(
    db: Session,
    workflow: str,
    variant_value: str | None,
) -> tuple[PromptVariant | None, PromptVariantVersion | None]:
    if not variant_value:
        return None, None
    key = slugify(variant_value)
    var = (
        db.query(PromptVariant)
        .filter(
            PromptVariant.workflow == workflow,
            PromptVariant.variant_key == key,
            PromptVariant.is_active.is_(True),
        )
        .first()
    )
    if not var or not var.active_version_id:
        return var, None
    ver = (
        db.query(PromptVariantVersion)
        .filter(PromptVariantVersion.id == var.active_version_id)
        .first()
    )
    return var, ver


def get_image_role_instruction(
    db: Session,
    role: str,
    workflow: str | None = None,
) -> str:
    row = None
    if workflow:
        row = (
            db.query(PromptImageRole)
            .filter(
                PromptImageRole.role == role,
                PromptImageRole.workflow == workflow,
                PromptImageRole.is_active.is_(True),
            )
            .first()
        )
    if not row:
        row = (
            db.query(PromptImageRole)
            .filter(
                PromptImageRole.role == role,
                PromptImageRole.workflow.is_(None),
                PromptImageRole.is_active.is_(True),
            )
            .first()
        )
    if row and row.instruction:
        return row.instruction
    return DEFAULT_IMAGE_ROLES.get(role, (role, f"Image {{index}} is the {role}."))[1]


def filter_conditional_keys(sections: dict[str, str], ctx: ImageContext) -> dict[str, str]:
    """Drop keys that require an image role that is not present."""
    role_present = {
        "product": ctx.has_product,
        "theme": ctx.has_style_reference,
        "portrait": ctx.has_portrait,
        "logo": ctx.has_logo,
    }
    out: dict[str, str] = {}
    for key, value in sections.items():
        needed = CONDITIONAL_KEYS.get(key.upper()) or CONDITIONAL_KEYS.get(key)
        if needed and not role_present.get(needed, False):
            continue
        out[key] = value
    return out


def merge_sections(*maps: dict[str, str] | None) -> dict[str, str]:
    """Merge maps left-to-right; later keys override earlier. Preserve order."""
    result: dict[str, str] = {}
    for m in maps:
        if not m:
            continue
        for k, v in m.items():
            if v is None:
                continue
            text = str(v).strip()
            if not text:
                continue
            result[k] = text
    return result


def append_image_role_sections(
    sections: dict[str, str],
    ctx: ImageContext,
    db: Session,
    workflow: str,
) -> dict[str, str]:
    """Append IMAGE ROLES block built from attached slots."""
    out = dict(sections)
    lines: list[str] = []
    role_flags = {
        "product": ctx.has_product,
        "theme": ctx.has_style_reference,
        "portrait": ctx.has_portrait,
        "logo": ctx.has_logo,
    }
    for role in IMAGE_ROLE_ORDER:
        if not role_flags.get(role):
            continue
        idx = role_index(ctx, role)
        if idx is None:
            # Fallback ordering
            defaults = {"product": 1, "theme": 2, "portrait": 2, "logo": 3 if ctx.has_style_reference or ctx.has_portrait else 2}
            idx = defaults.get(role, 1)
        tpl = get_image_role_instruction(db, role, workflow)
        line = tpl.replace("{index}", str(idx)).replace("{{index}}", str(idx))
        # Also rewrite "Image N" patterns if template uses a fixed number
        lines.append(f"- {line}" if not line.lstrip().startswith("-") else line)
    if lines:
        out["IMAGE ROLES"] = "\n".join(lines)
    return out


def _variant_value_for(inp: ComposeInput) -> str | None:
    field_name = VARIANT_FIELD_MAP.get(inp.workflow)
    if not field_name:
        return None
    return getattr(inp, field_name, None)


def compose_from_profiles(
    db: Session,
    inp: ComposeInput,
    *,
    image_ctx: ImageContext | None = None,
    user_id: str | None = None,
    job_id: str | None = None,
) -> ProfileComposeResult:
    """Compose a PromptDocument from V2 JSON profiles."""
    ctx = image_ctx or ImageContext()
    resolved = resolve_workflow(
        inp.workflow,
        catalog_mode=getattr(inp, "catalog_mode", None),
        try_on_mode=getattr(inp, "try_on_mode", None),
        has_reference=bool(ctx.has_style_reference),
    )
    workflow = resolved.workflow
    reference_mode = resolve_reference_mode(ctx)

    # REFERENCE_STYLE_MATCH always needs with_reference
    if (inp.workflow or "").upper() == "REFERENCE_STYLE_MATCH" or resolved.legacy_workflow == "REFERENCE_STYLE_MATCH":
        reference_mode = REF_WITH

    _profile, profile_ver = load_profile(db, workflow, reference_mode)
    # Fallback: if with_reference missing, try without (and vice versa)
    if not profile_ver:
        alt = REF_WITHOUT if reference_mode == REF_WITH else REF_WITH
        _profile, profile_ver = load_profile(db, workflow, alt)
        if profile_ver:
            reference_mode = alt

    base_sections: dict[str, str] = {}
    environment_chosen: str | None = None
    if profile_ver and isinstance(profile_ver.content_json, dict):
        base_sections = {str(k): str(v) for k, v in profile_ver.content_json.items() if v is not None}

    # Environment rotation for without_reference catalog
    if reference_mode == REF_WITHOUT and workflow in ("CATALOG_IMAGE", "BACKGROUND_REPLACEMENT"):
        pool = None
        if profile_ver and isinstance(profile_ver.environment_pool, list) and profile_ver.environment_pool:
            pool = [str(x).strip() for x in profile_ver.environment_pool if str(x).strip()]
        from app.prompt_engine.environment_rotation import choose_environment

        environment_chosen = choose_environment(user_id, job_id, db=db, pool=pool)
        if environment_chosen:
            # Inject or replace ASSIGNED_ENVIRONMENT
            if "ASSIGNED_ENVIRONMENT" in base_sections or "ASSIGNED ENVIRONMENT" in base_sections:
                key = "ASSIGNED_ENVIRONMENT" if "ASSIGNED_ENVIRONMENT" in base_sections else "ASSIGNED ENVIRONMENT"
                base_sections[key] = environment_chosen
            else:
                base_sections["ASSIGNED_ENVIRONMENT"] = environment_chosen

    # Jewelry sections (multi-type supported)
    jewelry_types = normalize_jewelry_types(parse_jewelry_types(inp.jewelry_type))
    jewelry_version_id: str | None = None
    jewelry_merged: dict[str, str] = {}
    for jt in jewelry_types or ([] if not inp.jewelry_type else [inp.jewelry_type]):
        _sec, jver = load_jewelry(db, workflow, jt)
        if jver and isinstance(jver.content_json, dict) and jewelry_content_nonempty(jver.content_json):
            jewelry_version_id = jver.id
            for k, v in jver.content_json.items():
                if v is None:
                    continue
                text = str(v).strip()
                if not text:
                    continue
                key = k if len(jewelry_types) <= 1 else f"{jt.upper()}_{k}"
                jewelry_merged[key] = text

    # Variant
    variant_value = _variant_value_for(inp)
    _var, var_ver = load_variant(db, workflow, variant_value)
    variant_sections: dict[str, str] = {}
    if var_ver:
        # Legacy variants store prompt_text; V2 may store JSON later
        text = (var_ver.prompt_text or "").strip()
        if text:
            variant_sections["VARIANT"] = text

    # User / custom instruction
    user_sections: dict[str, str] = {}
    user_raw = sanitize_user_prompt(inp.prompt_text) if inp.prompt_text else None
    if user_raw and workflow == "CUSTOM_PROMPT":
        from app.prompt_engine.custom_guard import sanitize_custom_change

        cleaned, _alter_hits = sanitize_custom_change(user_raw, db=db)
        user_raw = cleaned or None
    if user_raw:
        user_sections["USER_INSTRUCTION"] = user_raw

    # Style preset addon
    preset_sections: dict[str, str] = {}
    addon = inp.style_preset_addon
    if not addon and inp.style_preset_id:
        preset = db.query(StylePreset).filter(StylePreset.id == inp.style_preset_id).first()
        if preset and preset.prompt_addon:
            addon = preset.prompt_addon
    if addon:
        preset_sections["STYLE_PRESET"] = addon.strip()

    sections = merge_sections(base_sections, jewelry_merged, variant_sections, user_sections, preset_sections)
    sections = filter_conditional_keys(sections, ctx)
    sections = append_image_role_sections(sections, ctx, db, workflow)

    prompt_text, negatives = serialize_sections(sections)
    if not (prompt_text or "").strip() and not negatives:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail=(
                f"No prompt content for workflow={workflow} "
                f"reference_mode={reference_mode} jewelry_type={inp.jewelry_type!r}. "
                "Save a workflow profile and/or jewelry-type prompt in Admin → Prompts."
            ),
        )
    parts = [
        PromptPart(key=slugify(k) or "section", text=f"{k}: {v}", priority="critical", source="profile")
        for k, v in sections.items()
        if v and not NEGATIVE_KEY_RE.match(k.strip())
    ]
    # Prefer single packed text part for adapter simplicity when many sections
    if parts:
        doc = PromptDocument(
            parts=[PromptPart(key="profile", text=prompt_text, priority="critical", source="profile")],
            negative_parts=negatives,
            debug={},
        )
    else:
        doc = PromptDocument(parts=[], negative_parts=negatives, debug={})

    return ProfileComposeResult(
        document=doc,
        profile_version_id=profile_ver.id if profile_ver else None,
        jewelry_version_id=jewelry_version_id,
        variant_version_id=var_ver.id if var_ver else None,
        reference_mode=reference_mode,
        sections=deepcopy(sections),
        debug={
            "composePath": "profile_v2",
            "workflow": workflow,
            "legacyWorkflow": resolved.legacy_workflow,
            "catalogMode": resolved.catalog_mode,
            "tryOnMode": resolved.try_on_mode,
            "referenceMode": reference_mode,
            "environmentChosen": environment_chosen,
            "sectionKeys": list(sections.keys()),
            "profileVersionId": profile_ver.id if profile_ver else None,
            "jewelryVersionId": jewelry_version_id,
            "variantVersionId": var_ver.id if var_ver else None,
        },
    )


def build_final_prompt_v2(
    db: Session,
    inp: ComposeInput,
    *,
    model_spec=None,
    model_endpoint_id: str | None = None,
    image_ctx: ImageContext | None = None,
    user_id: str | None = None,
    job_id: str | None = None,
) -> FinalPrompt:
    """V2 entry: profile compose → model adapt."""
    from app.prompt_engine.model_adapter import adapt_document
    from app.providers.model_catalog.registry import get_spec

    if model_spec is None and model_endpoint_id:
        model_spec = get_spec(model_endpoint_id)

    ctx = image_ctx or ImageContext()
    result = compose_from_profiles(db, inp, image_ctx=ctx, user_id=user_id, job_id=job_id)
    final = adapt_document(
        result.document,
        model_spec=model_spec,
        master_version_id=result.profile_version_id,
        subject_version_id=result.jewelry_version_id,
        variant_version_id=result.variant_version_id,
    )
    subtypes = normalize_jewelry_types(parse_jewelry_types(inp.jewelry_type))
    final.debug = {
        **final.debug,
        **result.debug,
        "jewelry_type": inp.jewelry_type,
        "model_endpoint_id": model_endpoint_id or (model_spec.endpoint_id if model_spec else None),
        "image_context": {
            "has_product": ctx.has_product,
            "has_style_reference": ctx.has_style_reference,
            "has_portrait": ctx.has_portrait,
            "has_logo": ctx.has_logo,
            "image_count": ctx.image_count,
            "roles": list(ctx.roles or []),
        },
        "hasReference": bool(ctx.has_style_reference),
        "hasLogo": bool(ctx.has_logo),
        "subtypesIncluded": subtypes,
        "sections": result.sections,
    }
    return final
