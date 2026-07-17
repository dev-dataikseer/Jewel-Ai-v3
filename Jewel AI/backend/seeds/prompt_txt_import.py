"""One-time import of data/seed-prompt-templates/*.txt library into DB as versioned layer arrays."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import (
    PromptMasterTemplate,
    PromptMasterVersion,
    PromptSubject,
    PromptSubjectVersion,
    PromptVariant,
    PromptVariantVersion,
    PromptWorkflowLayerConfig,
)
from app.pipeline.layer_derive import default_structural_config
from seeds.prompt_txt_parser import (
    child_raw_to_db_layers,
    library_content_hash,
    load_all_prompt_files,
    master_raw_to_db_layers,
)

logger = logging.getLogger(__name__)
IMPORT_SETTING_KEY = "prompt_txt_library_hash"


def _get_import_hash(db: Session) -> str | None:
    from app.models import AppSetting

    row = db.query(AppSetting).filter(AppSetting.key == IMPORT_SETTING_KEY).first()
    return row.value if row else None


def _set_import_hash(db: Session, value: str) -> None:
    from app.models import AppSetting

    row = db.query(AppSetting).filter(AppSetting.key == IMPORT_SETTING_KEY).first()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=IMPORT_SETTING_KEY, value=value))


def _ensure_workflow_layer_config(db: Session, workflow: str) -> list[dict]:
    row = db.query(PromptWorkflowLayerConfig).filter(PromptWorkflowLayerConfig.workflow == workflow).first()
    structural = default_structural_config(workflow)
    if not row:
        row = PromptWorkflowLayerConfig(workflow=workflow, structural_layers=structural)
        db.add(row)
        db.flush()
    return list(row.structural_layers or structural)


def _upsert_master(
    db: Session,
    workflow: str,
    prompt_text: str,
    layers: list[dict],
) -> bool:
    tmpl = db.query(PromptMasterTemplate).filter(PromptMasterTemplate.workflow == workflow).first()
    if not tmpl:
        tmpl = PromptMasterTemplate(workflow=workflow, name=workflow.replace("_", " ").title(), is_active=True)
        db.add(tmpl)
        db.flush()

    last = (
        db.query(PromptMasterVersion)
        .filter(PromptMasterVersion.template_id == tmpl.id)
        .order_by(PromptMasterVersion.version.desc())
        .first()
    )
    vnum = (last.version + 1) if last else 1
    db.query(PromptMasterVersion).filter(PromptMasterVersion.template_id == tmpl.id).update({"is_active": False})

    ver = PromptMasterVersion(
        template_id=tmpl.id,
        version=vnum,
        prompt_text=prompt_text,
        composition_mode="layered",
        layers=layers,
        raw_override=None,
        is_active=True,
        source="txt",
    )
    db.add(ver)
    db.flush()
    tmpl.active_version_id = ver.id
    tmpl.is_active = True
    return True


def _upsert_subject(
    db: Session,
    workflow: str,
    jewelry_type: str,
    prompt_text: str,
    layers: list[dict],
) -> bool:
    subj = (
        db.query(PromptSubject)
        .filter(PromptSubject.workflow == workflow, PromptSubject.jewelry_type == jewelry_type)
        .first()
    )
    if not subj:
        subj = PromptSubject(workflow=workflow, jewelry_type=jewelry_type, is_active=True)
        db.add(subj)
        db.flush()

    last = (
        db.query(PromptSubjectVersion)
        .filter(PromptSubjectVersion.subject_id == subj.id)
        .order_by(PromptSubjectVersion.version.desc())
        .first()
    )
    vnum = (last.version + 1) if last else 1
    db.query(PromptSubjectVersion).filter(PromptSubjectVersion.subject_id == subj.id).update({"is_active": False})

    ver = PromptSubjectVersion(
        subject_id=subj.id,
        version=vnum,
        prompt_text=prompt_text,
        composition_mode="layered",
        layers=layers,
        raw_override=None,
        is_active=True,
        source="txt",
    )
    db.add(ver)
    db.flush()
    subj.active_version_id = ver.id
    subj.is_active = True
    return True


def _upsert_variant(db: Session, workflow: str, variant_key: str, label: str, prompt_text: str, sort_order: int) -> None:
    var = (
        db.query(PromptVariant)
        .filter(PromptVariant.workflow == workflow, PromptVariant.variant_key == variant_key)
        .first()
    )
    if not var:
        var = PromptVariant(
            workflow=workflow,
            variant_key=variant_key,
            label=label,
            sort_order=sort_order,
            is_active=True,
        )
        db.add(var)
        db.flush()
    else:
        var.label = label
        var.sort_order = sort_order
        var.is_active = True

    last = (
        db.query(PromptVariantVersion)
        .filter(PromptVariantVersion.variant_id == var.id)
        .order_by(PromptVariantVersion.version.desc())
        .first()
    )
    vnum = (last.version + 1) if last else 1
    db.query(PromptVariantVersion).filter(PromptVariantVersion.variant_id == var.id).update({"is_active": False})

    vver = PromptVariantVersion(
        variant_id=var.id,
        version=vnum,
        prompt_text=prompt_text,
        is_active=True,
    )
    db.add(vver)
    db.flush()
    var.active_version_id = vver.id


def import_prompt_txt_library(
    db: Session,
    *,
    prompt_dir: Path | None = None,
    force: bool = False,
) -> dict:
    """Load data/seed-prompt-templates/*.txt into DB once. Skips if any master versions exist unless force=True."""
    existing = db.query(PromptMasterVersion).count()
    if not force and existing > 0:
        return {"imported": False, "reason": "already_seeded", "existing_versions": existing}

    content_hash = library_content_hash(prompt_dir)
    if not content_hash:
        return {"imported": False, "reason": "prompt library folder not found"}

    workflows = load_all_prompt_files(prompt_dir)
    if not workflows:
        return {"imported": False, "reason": "no prompt files parsed"}

    masters = 0
    subjects = 0
    variants = 0

    for wf in workflows:
        structural = _ensure_workflow_layer_config(db, wf.workflow)
        master_layers = master_raw_to_db_layers(wf.master_raw_text, wf.workflow, structural)
        if _upsert_master(db, wf.workflow, wf.master_raw_text, master_layers):
            masters += 1

        for idx, variant in enumerate(wf.variants):
            _upsert_variant(db, wf.workflow, variant.variant_key, variant.label, variant.prompt_text, idx)
            variants += 1

        for child in wf.children:
            child_layers = child_raw_to_db_layers(child.raw_text)
            if _upsert_subject(db, wf.workflow, child.jewelry_type, child.raw_text, child_layers):
                subjects += 1

    _set_import_hash(db, content_hash)
    db.commit()
    return {
        "imported": True,
        "hash": content_hash,
        "workflows": masters,
        "subjects": subjects,
        "variants": variants,
    }
