import re
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import (
    PromptMasterTemplate,
    PromptMasterVersion,
    PromptSubject,
    PromptSubjectVersion,
    PromptVariant,
    PromptVariantVersion,
    StylePreset,
)
from app.pipeline.layer_derive import derive_layers_from_raw_text
from app.pipeline.layers import (
    PromptCompositionError,
    assemble_layer_parts,
    assert_no_jinja_leaks,
    default_master_scaffold,
    default_subject_scaffold,
    layers_from_legacy_master,
    layers_from_legacy_subject,
    sort_layers,
)
from app.pipeline.validator import sanitize_user_prompt
from app.pipeline.validator import normalize_jewelry_types, parse_jewelry_types
from app.prompt_engine.document import PromptDocument, PromptPart


def slugify(value: str) -> str:
    return re.sub(r"^_|_$", "", re.sub(r"[^a-z0-9]+", "_", value.lower().strip()))


VARIANT_FIELD_MAP = {
    "GEMSTONE_COLOR_CHANGE": "gemstone_target_color",
    "BACKGROUND_REPLACEMENT": "background_style",
    "LUXURY_ENHANCEMENT": "metal_type",
    "REFERENCE_STYLE_MATCH": "background_style",  # legacy
    "CATALOG_IMAGE": "background_style",  # style_mood optional variant
}


@dataclass
class ComposeInput:
    workflow: str = "CATALOG_IMAGE"
    jewelry_type: str | None = None
    prompt_text: str | None = None
    metal_type: str | None = None
    gemstone_type: str | None = None
    gemstone_target_color: str | None = None
    background_style: str | None = None
    lighting_style: str | None = None
    style_preset_id: str | None = None
    style_preset_addon: str | None = None
    catalog_mode: str | None = None  # modern | reference_mirror | style_mood
    try_on_mode: str | None = None  # studio | customer


@dataclass
class ComposedPrompt:
    text: str
    negative_prompt: str
    debug: dict[str, Any] = field(default_factory=dict)
    master_version_id: str | None = None
    subject_version_id: str | None = None
    variant_version_id: str | None = None


@dataclass
class ComposedDocument:
    """Structured compose result before model-specific packing."""

    document: PromptDocument
    master_version_id: str | None = None
    subject_version_id: str | None = None
    variant_version_id: str | None = None
    debug: dict[str, Any] = field(default_factory=dict)


def _pick_variant_value(inp: ComposeInput) -> str | None:
    field_name = VARIANT_FIELD_MAP.get(inp.workflow)
    if not field_name:
        return None
    if field_name == "gemstone_target_color":
        return inp.gemstone_target_color or inp.gemstone_type
    if field_name == "background_style":
        return inp.background_style
    if field_name == "metal_type":
        return inp.metal_type
    return None


def _get_active_master(db: Session, workflow: str) -> tuple[PromptMasterTemplate | None, PromptMasterVersion | None]:
    tmpl = db.query(PromptMasterTemplate).filter(PromptMasterTemplate.workflow == workflow).first()
    if not tmpl or not tmpl.is_active:
        return tmpl, None
    if tmpl.active_version_id:
        ver = db.query(PromptMasterVersion).filter(PromptMasterVersion.id == tmpl.active_version_id).first()
        if ver and ver.is_active:
            return tmpl, ver
    ver = (
        db.query(PromptMasterVersion)
        .filter(PromptMasterVersion.template_id == tmpl.id, PromptMasterVersion.is_active == True)  # noqa: E712
        .order_by(PromptMasterVersion.version.desc())
        .first()
    )
    return tmpl, ver


def _get_active_subject(
    db: Session, workflow: str, jewelry_type: str
) -> tuple[PromptSubject | None, PromptSubjectVersion | None]:
    subj = (
        db.query(PromptSubject)
        .filter(PromptSubject.workflow == workflow, PromptSubject.jewelry_type == jewelry_type)
        .first()
    )
    if not subj or not subj.is_active:
        return subj, None
    if subj.active_version_id:
        ver = db.query(PromptSubjectVersion).filter(PromptSubjectVersion.id == subj.active_version_id).first()
        if ver and ver.is_active:
            return subj, ver
    ver = (
        db.query(PromptSubjectVersion)
        .filter(PromptSubjectVersion.subject_id == subj.id, PromptSubjectVersion.is_active == True)  # noqa: E712
        .order_by(PromptSubjectVersion.version.desc())
        .first()
    )
    return subj, ver


def _get_active_variant(
    db: Session, workflow: str, variant_key: str
) -> tuple[PromptVariant | None, PromptVariantVersion | None]:
    key = slugify(variant_key)
    var = db.query(PromptVariant).filter(PromptVariant.workflow == workflow, PromptVariant.variant_key == key).first()
    if not var or not var.is_active:
        return var, None
    if var.active_version_id:
        ver = db.query(PromptVariantVersion).filter(PromptVariantVersion.id == var.active_version_id).first()
        if ver and ver.is_active:
            return var, ver
    ver = (
        db.query(PromptVariantVersion)
        .filter(PromptVariantVersion.variant_id == var.id, PromptVariantVersion.is_active == True)  # noqa: E712
        .order_by(PromptVariantVersion.version.desc())
        .first()
    )
    return var, ver


def _resolve_master_layers(db: Session, master_ver: PromptMasterVersion | None, workflow: str) -> list[dict]:
    if master_ver and master_ver.layers:
        return list(master_ver.layers)
    if master_ver and master_ver.prompt_text:
        from app.models import PromptWorkflowLayerConfig
        from app.pipeline.layer_derive import default_structural_config

        row = db.query(PromptWorkflowLayerConfig).filter(PromptWorkflowLayerConfig.workflow == workflow).first()
        structural = list(row.structural_layers) if row and row.structural_layers else default_structural_config(workflow)
        return derive_layers_from_raw_text(
            master_ver.prompt_text,
            workflow,
            scope="master",
            structural_config=structural,
        )
    if master_ver:
        legacy = layers_from_legacy_master(
            {
                "system_role": master_ver.system_role,
                "camera_settings": master_ver.camera_settings,
                "environment": master_ver.environment,
                "lighting_and_physics": master_ver.lighting_and_physics,
                "preservation_lock": master_ver.preservation_lock,
                "negative_prompt": master_ver.negative_prompt,
            }
        )
        if legacy:
            return legacy
    return default_master_scaffold()


def _resolve_subject_layers(subject_ver: PromptSubjectVersion | None, workflow: str) -> list[dict]:
    if subject_ver and subject_ver.layers is not None:
        return list(subject_ver.layers)
    if subject_ver and subject_ver.prompt_text:
        return derive_layers_from_raw_text(subject_ver.prompt_text, workflow, scope="subject")
    if subject_ver:
        legacy = layers_from_legacy_subject(
            {
                "core_description": subject_ver.core_description,
                "anatomy_interaction": subject_ver.anatomy_interaction,
                "physics_and_gravity": subject_ver.physics_and_gravity,
                "placement_rules": subject_ver.placement_rules,
            }
        )
        if legacy:
            return legacy
    return default_subject_scaffold()


def _placement_anatomy(db: Session, jewelry_type: str | None) -> str:
    """Pick placement clause from TRYON_PLACEMENT_ANATOMY fragment for jewelry type."""
    from app.prompt_engine.fragment_defaults import TRYON_PLACEMENT_ANATOMY
    from app.prompt_engine.fragment_store import get_fragment_text

    raw = get_fragment_text(db, TRYON_PLACEMENT_ANATOMY) or ""
    if not jewelry_type or not raw:
        return ""
    key = jewelry_type.strip().lower().replace(" ", "_")
    # Also try first type if comma-separated
    key = key.split(",")[0].strip()
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        left, _, right = line.partition("|")
        if left.strip().lower().replace(" ", "_") == key:
            return right.strip()
    return ""


def _compose_engine_placeholders(db: Session, inp: ComposeInput, safe_prompt: str | None) -> dict[str, str]:
    """Jinja vars for {{KEY}} tokens in imported V2 masters (StrictUndefined-safe)."""
    from app.prompt_engine.fragment_defaults import (
        CUSTOM_PRESERVE,
        CUSTOM_REALISM,
        PROMPT_PLACEHOLDERS,
        TRYON_CUSTOMER_PRESERVE,
    )
    from app.prompt_engine.fragment_store import get_fragment_text

    vars_: dict[str, str] = {k: "" for k in PROMPT_PLACEHOLDERS}
    prompt = safe_prompt or ""
    vars_["USER_CUSTOM_INSTRUCTION"] = prompt
    vars_["USER_ADDITION_TEXT"] = prompt
    vars_["USER_INSTRUCTION"] = prompt
    vars_["TARGET_COLOR"] = inp.gemstone_target_color or inp.gemstone_type or ""
    vars_["PLACEMENT_ANATOMY"] = _placement_anatomy(db, inp.jewelry_type)

    if (inp.try_on_mode or "").lower() == "customer":
        vars_["TRYON_MODE_CLAUSE"] = get_fragment_text(db, TRYON_CUSTOMER_PRESERVE) or ""

    # Optional fills when masters still embed these (engine also appends fragments).
    if inp.workflow == "CUSTOM_PROMPT":
        vars_["CUSTOM_PRESERVE"] = get_fragment_text(db, CUSTOM_PRESERVE) or ""
        vars_["CUSTOM_REALISM"] = get_fragment_text(db, CUSTOM_REALISM) or ""

    return vars_


def compose_prompt_document(db: Session, inp: ComposeInput) -> ComposedDocument:
    wf = inp.workflow or "CATALOG_IMAGE"
    jewelry_types = normalize_jewelry_types(parse_jewelry_types(inp.jewelry_type))
    jewelry_type_label = ", ".join(jewelry_types)

    _, master_ver = _get_active_master(db, wf)
    if not master_ver:
        raise HTTPException(
            status_code=404,
            detail=f"No master prompt configured for workflow '{wf}'. Add layers in Admin → Prompts.",
        )

    subject_layers_by_type: list[tuple[str, list[dict]]] = []
    subject_version_ids: list[str] = []
    subject_layer_keys: list[str] = []
    for jt in jewelry_types:
        _, subject_ver = _get_active_subject(db, wf, jt)
        layers = _resolve_subject_layers(subject_ver, wf)
        subject_layers_by_type.append((jt, layers))
        if subject_ver:
            subject_version_ids.append(subject_ver.id)
        subject_layer_keys.extend(layer.get("key") for layer in sort_layers(layers))

    master_layers = _resolve_master_layers(db, master_ver, wf)
    subject_layers = subject_layers_by_type[0][1] if len(subject_layers_by_type) == 1 else []

    composition_mode = master_ver.composition_mode or "layered"
    raw_override = master_ver.raw_override

    variant_value = _pick_variant_value(inp)
    variant_text = None
    variant_neg = ""
    variant_vid = None
    if variant_value:
        _, vver = _get_active_variant(db, wf, variant_value)
        if vver and vver.prompt_text:
            variant_text = vver.prompt_text
            variant_neg = vver.negative_addon or ""
            variant_vid = vver.id

    preset_addon = inp.style_preset_addon
    if not preset_addon and inp.style_preset_id:
        preset = db.query(StylePreset).filter(StylePreset.id == inp.style_preset_id, StylePreset.is_active == True).first()  # noqa: E712
        if preset and preset.prompt_addon:
            preset_addon = preset.prompt_addon

    safe_prompt = sanitize_user_prompt(inp.prompt_text)

    variables = {
        **_compose_engine_placeholders(db, inp, safe_prompt),
        "workflow": wf,
        "jewelry_type": jewelry_type_label,
        "metal_type": inp.metal_type or "",
        "gemstone_type": inp.gemstone_type or "",
        "gemstone_target_color": inp.gemstone_target_color or "",
        "background_style": inp.background_style or "",
        "lighting_style": inp.lighting_style or "",
        "prompt_text": safe_prompt or "",
        "variant_text": variant_text or "",
    }

    try:
        _body_parts, negative, layer_debug, budget_parts = assemble_layer_parts(
            master_layers,
            subject_layers,
            subject_layers_by_type=subject_layers_by_type if len(jewelry_types) > 1 else None,
            composition_mode=composition_mode,
            raw_override=raw_override,
            variant_text=variant_text,
            user_instruction=safe_prompt,
            variables=variables,
            db=db,
        )
    except PromptCompositionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    parts = [
        PromptPart(key=p.key or f"part_{i}", text=p.text, priority=p.priority, source=p.source)
        for i, p in enumerate(budget_parts)
        if p.text
    ]
    if inp.lighting_style:
        parts.append(
            PromptPart(
                key="lighting_style",
                text=f"Lighting style: {inp.lighting_style}.",
                priority="optional",
                source="preset",
            )
        )
    if preset_addon:
        parts.append(PromptPart(key="style_preset", text=preset_addon, priority="optional", source="preset"))

    neg_parts = [negative, variant_neg]
    for part in parts:
        assert_no_jinja_leaks(part.text, "composed prompt part")
    neg_out_parts = list(dict.fromkeys(filter(None, neg_parts)))
    for neg in neg_out_parts:
        assert_no_jinja_leaks(neg, "negative prompt")

    debug = {
        "workflow": wf,
        "jewelry_type": jewelry_type_label,
        "jewelry_types": jewelry_types,
        "subject_version_ids": subject_version_ids,
        "variant_key": slugify(variant_value) if variant_value else None,
        "variant_field": VARIANT_FIELD_MAP.get(wf),
        "composition_mode": composition_mode,
        "master_layers": [layer.get("key") for layer in sort_layers(master_layers)],
        "subject_layers": subject_layer_keys,
        "structured_parts": [{"key": p.key, "priority": p.priority, "source": p.source} for p in parts],
        **layer_debug,
    }

    return ComposedDocument(
        document=PromptDocument(parts=parts, negative_parts=neg_out_parts, debug=debug),
        master_version_id=master_ver.id,
        subject_version_id=",".join(subject_version_ids) if subject_version_ids else None,
        variant_version_id=variant_vid,
        debug=debug,
    )


def compose_prompt(db: Session, inp: ComposeInput) -> ComposedPrompt:
    """Backward-compatible flat string compose (Admin preview / legacy callers)."""
    composed = compose_prompt_document(db, inp)
    body = " ".join(p.text.strip() for p in composed.document.parts if p.text).strip()
    neg_out = ". ".join(composed.document.negative_parts)
    return ComposedPrompt(
        text=body,
        negative_prompt=neg_out,
        master_version_id=composed.master_version_id,
        subject_version_id=composed.subject_version_id,
        variant_version_id=composed.variant_version_id,
        debug=composed.debug,
    )
