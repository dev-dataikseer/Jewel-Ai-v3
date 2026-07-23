from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import RequireAdmin, RequireUser
from app.database import get_db
from app.models import (
    PromptMasterTemplate,
    PromptMasterVersion,
    PromptSubject,
    PromptSubjectVersion,
    PromptVariant,
    PromptVariantVersion,
    PromptWorkflowLayerConfig,
    StylePreset,
)
from app.pipeline.layer_derive import (
    assemble_raw_text_from_layers,
    default_structural_config,
    derive_layers_from_raw_text,
)
from app.pipeline.layer_validate import validate_master_layers, validate_subject_layers
from app.pipeline.layers import sort_layers

router = APIRouter(prefix="/prompts", tags=["prompts"])


def _get_structural_config(db: Session, workflow: str) -> list[dict]:
    row = db.query(PromptWorkflowLayerConfig).filter(PromptWorkflowLayerConfig.workflow == workflow).first()
    if row and row.structural_layers:
        return list(row.structural_layers)
    return default_structural_config(workflow)


def _display_prompt_text(ver, layers: list[dict] | None) -> str | None:
    if ver and ver.prompt_text:
        return ver.prompt_text
    if layers:
        assembled = assemble_raw_text_from_layers(layers)
        return assembled or None
    return None


def _serialize_master_version(ver: PromptMasterVersion) -> dict:
    layers = sort_layers(ver.layers) if ver.layers else []
    return {
        "id": ver.id,
        "version": ver.version,
        "is_active": ver.is_active,
        "created_at": ver.created_at.isoformat() if ver.created_at else None,
        "prompt_text": _display_prompt_text(ver, layers),
        "composition_mode": ver.composition_mode,
        "layers": layers,
        "source": ver.source,
    }


def _serialize_subject_version(ver: PromptSubjectVersion) -> dict:
    layers = sort_layers(ver.layers) if ver.layers else []
    return {
        "id": ver.id,
        "version": ver.version,
        "is_active": ver.is_active,
        "created_at": ver.created_at.isoformat() if ver.created_at else None,
        "prompt_text": _display_prompt_text(ver, layers),
        "composition_mode": ver.composition_mode,
        "layers": layers,
        "source": ver.source,
    }


def _versions_by_ids(db: Session, model, ids: list[str | None]) -> dict:
    clean = [i for i in ids if i]
    if not clean:
        return {}
    return {row.id: row for row in db.query(model).filter(model.id.in_(clean)).all()}


class PromptTemplateUpsert(BaseModel):
    workflow: str
    name: Optional[str] = None
    prompt_text: Optional[str] = None
    layers: Optional[list[Any]] = None
    composition_mode: str = "layered"
    raw_override: Optional[str] = None
    is_active: bool = True


class PromptSubjectUpsert(BaseModel):
    jewelry_type: str
    workflow: str = "CATALOG_IMAGE"
    prompt_text: Optional[str] = None
    layers: Optional[list[Any]] = None
    composition_mode: str = "layered"
    raw_override: Optional[str] = None
    is_active: bool = True


class PromptVariantUpsert(BaseModel):
    workflow: str
    variant_key: str
    label: Optional[str] = None
    sort_order: int = 0
    prompt_text: str
    negative_addon: Optional[str] = None
    is_active: bool = True


class PromptFragmentUpsert(BaseModel):
    fragment_key: Optional[str] = None
    key: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    prompt_text: Optional[str] = None
    content_json: Optional[Any] = None
    is_active: bool = True


class PromptValidateBody(BaseModel):
    prompt_text: str = ""
    scope: str = "master"  # master | subject | variant | fragment | preset
    workflow: Optional[str] = None


class StylePresetUpdate(BaseModel):
    name: Optional[str] = None
    workflow: Optional[str] = None
    description: Optional[str] = None
    prompt_addon: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/templates")
def list_templates(user: RequireUser, db: Session = Depends(get_db)):
    rows = db.query(PromptMasterTemplate).all()
    versions = _versions_by_ids(db, PromptMasterVersion, [t.active_version_id for t in rows])
    result = []
    for t in rows:
        ver = versions.get(t.active_version_id) if t.active_version_id else None
        layers = sort_layers(ver.layers) if ver and ver.layers else []
        result.append(
            {
                "id": t.id,
                "workflow": t.workflow,
                "name": t.name,
                "is_active": t.is_active,
                "prompt_text": _display_prompt_text(ver, layers),
                "composition_mode": ver.composition_mode if ver else "layered",
                "raw_override": ver.raw_override if ver else None,
                "layers": layers,
                "active_version_id": t.active_version_id,
            }
        )
    return result


@router.post("/templates")
def upsert_template(body: PromptTemplateUpsert, user: RequireAdmin, db: Session = Depends(get_db)):
    workflow = body.workflow
    tmpl = db.query(PromptMasterTemplate).filter(PromptMasterTemplate.workflow == workflow).first()
    if not tmpl:
        tmpl = PromptMasterTemplate(workflow=workflow, name=body.name or workflow, is_active=True)
        db.add(tmpl)
        db.flush()

    last_ver = (
        db.query(PromptMasterVersion)
        .filter(PromptMasterVersion.template_id == tmpl.id)
        .order_by(PromptMasterVersion.version.desc())
        .first()
    )
    version_num = (last_ver.version + 1) if last_ver else 1
    db.query(PromptMasterVersion).filter(PromptMasterVersion.template_id == tmpl.id).update({"is_active": False})

    structural = _get_structural_config(db, workflow)
    if body.layers:
        layers = sort_layers(body.layers)
        validate_master_layers(layers)
        prompt_text = body.prompt_text or assemble_raw_text_from_layers(layers)
    else:
        prompt_text = body.prompt_text or ""
        layers = derive_layers_from_raw_text(prompt_text, workflow, scope="master", structural_config=structural)
        validate_master_layers(layers)

    ver = PromptMasterVersion(
        template_id=tmpl.id,
        version=version_num,
        prompt_text=prompt_text,
        composition_mode=body.composition_mode,
        layers=layers,
        raw_override=body.raw_override,
        is_active=True,
        source="admin",
    )
    db.add(ver)
    db.flush()
    tmpl.active_version_id = ver.id
    tmpl.is_active = body.is_active
    db.commit()
    return {"id": tmpl.id, "version_id": ver.id, "version": version_num}


@router.get("/subjects")
def list_subjects(user: RequireUser, workflow: str | None = None, db: Session = Depends(get_db)):
    q = db.query(PromptSubject)
    if workflow:
        q = q.filter(PromptSubject.workflow == workflow)
    rows = q.all()
    versions = _versions_by_ids(db, PromptSubjectVersion, [s.active_version_id for s in rows])
    result = []
    for s in rows:
        ver = versions.get(s.active_version_id) if s.active_version_id else None
        layers = sort_layers(ver.layers) if ver and ver.layers else []
        result.append(
            {
                "id": s.id,
                "workflow": s.workflow,
                "jewelry_type": s.jewelry_type,
                "is_active": s.is_active,
                "prompt_text": _display_prompt_text(ver, layers),
                "composition_mode": ver.composition_mode if ver else "layered",
                "raw_override": ver.raw_override if ver else None,
                "layers": layers,
                "active_version_id": s.active_version_id,
            }
        )
    return result


@router.post("/subjects")
def upsert_subject(body: PromptSubjectUpsert, user: RequireAdmin, db: Session = Depends(get_db)):
    jt = body.jewelry_type
    workflow = body.workflow
    subj = (
        db.query(PromptSubject)
        .filter(PromptSubject.workflow == workflow, PromptSubject.jewelry_type == jt)
        .first()
    )
    if not subj:
        subj = PromptSubject(workflow=workflow, jewelry_type=jt, is_active=True)
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

    if body.layers:
        layers = sort_layers(body.layers)
        validate_subject_layers(layers)
        prompt_text = body.prompt_text or assemble_raw_text_from_layers(layers)
    else:
        prompt_text = body.prompt_text or ""
        layers = derive_layers_from_raw_text(prompt_text, workflow, scope="subject")
        validate_subject_layers(layers)

    ver = PromptSubjectVersion(
        subject_id=subj.id,
        version=vnum,
        prompt_text=prompt_text,
        composition_mode=body.composition_mode,
        layers=layers,
        raw_override=body.raw_override,
        is_active=True,
        source="admin",
    )
    db.add(ver)
    db.flush()
    subj.active_version_id = ver.id
    subj.is_active = body.is_active
    db.commit()
    return {"id": subj.id, "version_id": ver.id}


@router.get("/variants")
def list_variants(user: RequireUser, workflow: str | None = None, db: Session = Depends(get_db)):
    q = db.query(PromptVariant)
    if workflow:
        q = q.filter(PromptVariant.workflow == workflow)
    rows = q.order_by(PromptVariant.sort_order).all()
    versions = _versions_by_ids(db, PromptVariantVersion, [v.active_version_id for v in rows])
    result = []
    for v in rows:
        ver = versions.get(v.active_version_id) if v.active_version_id else None
        result.append(
            {
                "id": v.id,
                "workflow": v.workflow,
                "variant_key": v.variant_key,
                "label": v.label,
                "sort_order": v.sort_order,
                "is_active": v.is_active,
                "prompt_text": ver.prompt_text if ver else None,
            }
        )
    return result


@router.post("/variants")
def upsert_variant(body: PromptVariantUpsert, user: RequireAdmin, db: Session = Depends(get_db)):
    var = db.query(PromptVariant).filter(
        PromptVariant.workflow == body.workflow,
        PromptVariant.variant_key == body.variant_key,
    ).first()
    if not var:
        var = PromptVariant(
            workflow=body.workflow,
            variant_key=body.variant_key,
            label=body.label or body.variant_key,
            sort_order=body.sort_order,
            is_active=True,
        )
        db.add(var)
        db.flush()
    last = (
        db.query(PromptVariantVersion)
        .filter(PromptVariantVersion.variant_id == var.id)
        .order_by(PromptVariantVersion.version.desc())
        .first()
    )
    vnum = (last.version + 1) if last else 1
    db.query(PromptVariantVersion).filter(PromptVariantVersion.variant_id == var.id).update({"is_active": False})
    ver = PromptVariantVersion(
        variant_id=var.id,
        version=vnum,
        prompt_text=body.prompt_text,
        negative_addon=body.negative_addon,
        is_active=True,
    )
    db.add(ver)
    db.flush()
    var.active_version_id = ver.id
    db.commit()
    return {"id": var.id, "version_id": ver.id}


@router.get("/workflows/{workflow}/layer-config")
def get_layer_config(workflow: str, user: RequireUser, db: Session = Depends(get_db)):
    row = db.query(PromptWorkflowLayerConfig).filter(PromptWorkflowLayerConfig.workflow == workflow).first()
    structural = list(row.structural_layers) if row and row.structural_layers else default_structural_config(workflow)
    return {"workflow": workflow, "structural_layers": structural}


@router.put("/workflows/{workflow}/layer-config")
def update_layer_config(workflow: str, body: dict, user: RequireAdmin, db: Session = Depends(get_db)):
    structural = body.get("structural_layers")
    if not structural:
        raise HTTPException(status_code=400, detail="structural_layers required")

    row = db.query(PromptWorkflowLayerConfig).filter(PromptWorkflowLayerConfig.workflow == workflow).first()
    if not row:
        row = PromptWorkflowLayerConfig(workflow=workflow, structural_layers=structural)
        db.add(row)
    else:
        row.structural_layers = structural
    db.commit()
    return {"workflow": workflow, "structural_layers": structural}


@router.get("/presets")
def list_presets(user: RequireUser, db: Session = Depends(get_db)):
    return db.query(StylePreset).filter(StylePreset.is_active == True).all()  # noqa: E712


@router.post("/presets")
def create_preset(body: dict, user: RequireAdmin, db: Session = Depends(get_db)):
    preset = StylePreset(
        name=body["name"],
        workflow=body.get("workflow"),
        description=body.get("description"),
        prompt_addon=body["prompt_addon"],
        is_active=True,
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset


@router.delete("/presets/{preset_id}")
def delete_preset(preset_id: str, user: RequireAdmin, db: Session = Depends(get_db)):
    preset = db.query(StylePreset).filter(StylePreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404)
    db.delete(preset)
    db.commit()
    return {"success": True}


@router.patch("/presets/{preset_id}")
def update_preset(
    preset_id: str,
    body: StylePresetUpdate,
    user: RequireAdmin,
    db: Session = Depends(get_db),
):
    preset = db.query(StylePreset).filter(StylePreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404)
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(preset, key, value)
    db.commit()
    db.refresh(preset)
    return preset


@router.post("/validate")
def validate_prompt(body: PromptValidateBody, user: RequireAdmin):
    """Save-time placeholder / Jinja lint for Admin editors."""
    from app.prompt_engine.prompt_validate import validate_prompt_text

    scope = body.scope if body.scope in ("master", "subject", "variant", "fragment", "preset") else "master"
    return validate_prompt_text(body.prompt_text, scope=scope, workflow=body.workflow)


@router.post("/templates/{template_id}/rollback/{version_id}")
def rollback_template(template_id: str, version_id: str, user: RequireAdmin, db: Session = Depends(get_db)):
    tmpl = db.query(PromptMasterTemplate).filter(PromptMasterTemplate.id == template_id).first()
    ver = db.query(PromptMasterVersion).filter(
        PromptMasterVersion.id == version_id,
        PromptMasterVersion.template_id == template_id,
    ).first()
    if not tmpl or not ver:
        raise HTTPException(status_code=404)
    db.query(PromptMasterVersion).filter(PromptMasterVersion.template_id == template_id).update({"is_active": False})
    ver.is_active = True
    tmpl.active_version_id = ver.id
    db.commit()
    return {"success": True, "active_version_id": ver.id}


@router.get("/templates/{template_id}/versions")
def list_template_versions(template_id: str, user: RequireAdmin, db: Session = Depends(get_db)):
    tmpl = db.query(PromptMasterTemplate).filter(PromptMasterTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404)
    versions = (
        db.query(PromptMasterVersion)
        .filter(PromptMasterVersion.template_id == template_id)
        .order_by(PromptMasterVersion.version.desc())
        .all()
    )
    return [_serialize_master_version(v) for v in versions]


@router.post("/templates/{template_id}/activate/{version_id}")
def activate_template_version(template_id: str, version_id: str, user: RequireAdmin, db: Session = Depends(get_db)):
    return rollback_template(template_id, version_id, user, db)


@router.get("/subjects/{subject_id}/versions")
def list_subject_versions(subject_id: str, user: RequireAdmin, db: Session = Depends(get_db)):
    subj = db.query(PromptSubject).filter(PromptSubject.id == subject_id).first()
    if not subj:
        raise HTTPException(status_code=404)
    versions = (
        db.query(PromptSubjectVersion)
        .filter(PromptSubjectVersion.subject_id == subject_id)
        .order_by(PromptSubjectVersion.version.desc())
        .all()
    )
    return [_serialize_subject_version(v) for v in versions]


@router.post("/subjects/{subject_id}/activate/{version_id}")
def activate_subject_version(subject_id: str, version_id: str, user: RequireAdmin, db: Session = Depends(get_db)):
    subj = db.query(PromptSubject).filter(PromptSubject.id == subject_id).first()
    ver = db.query(PromptSubjectVersion).filter(
        PromptSubjectVersion.id == version_id,
        PromptSubjectVersion.subject_id == subject_id,
    ).first()
    if not subj or not ver:
        raise HTTPException(status_code=404)
    db.query(PromptSubjectVersion).filter(PromptSubjectVersion.subject_id == subject_id).update({"is_active": False})
    ver.is_active = True
    subj.active_version_id = ver.id
    db.commit()
    return {"success": True, "active_version_id": ver.id}


@router.get("/variants/{variant_id}/versions")
def list_variant_versions(variant_id: str, user: RequireAdmin, db: Session = Depends(get_db)):
    var = db.query(PromptVariant).filter(PromptVariant.id == variant_id).first()
    if not var:
        raise HTTPException(status_code=404)
    versions = (
        db.query(PromptVariantVersion)
        .filter(PromptVariantVersion.variant_id == variant_id)
        .order_by(PromptVariantVersion.version.desc())
        .all()
    )
    return [{"id": v.id, "version": v.version, "is_active": v.is_active, "prompt_text": v.prompt_text} for v in versions]


@router.post("/variants/{variant_id}/activate/{version_id}")
def activate_variant_version(variant_id: str, version_id: str, user: RequireAdmin, db: Session = Depends(get_db)):
    var = db.query(PromptVariant).filter(PromptVariant.id == variant_id).first()
    ver = db.query(PromptVariantVersion).filter(
        PromptVariantVersion.id == version_id,
        PromptVariantVersion.variant_id == variant_id,
    ).first()
    if not var or not ver:
        raise HTTPException(status_code=404)
    db.query(PromptVariantVersion).filter(PromptVariantVersion.variant_id == variant_id).update({"is_active": False})
    ver.is_active = True
    var.active_version_id = ver.id
    db.commit()
    return {"success": True, "active_version_id": ver.id}


# ── Prompt fragments (shared Admin-editable blocks) ──────────────────────────


def _serialize_fragment_version(ver) -> dict:
    return {
        "id": ver.id,
        "version": ver.version,
        "is_active": ver.is_active,
        "created_at": ver.created_at.isoformat() if ver.created_at else None,
        "prompt_text": ver.prompt_text,
        "content_json": ver.content_json,
        "source": ver.source,
    }


@router.get("/fragments")
def list_fragments(user: RequireUser, db: Session = Depends(get_db)):
    from app.models import PromptFragment, PromptFragmentVersion
    from app.prompt_engine.fragment_defaults import FRAGMENT_KEYS, FRAGMENT_LABELS

    rows = db.query(PromptFragment).order_by(PromptFragment.fragment_key.asc()).all()
    by_key = {r.fragment_key: r for r in rows}
    versions = _versions_by_ids(db, PromptFragmentVersion, [r.active_version_id for r in rows])
    result = []
    for key in FRAGMENT_KEYS:
        t = by_key.get(key)
        if not t:
            result.append(
                {
                    "id": None,
                    "fragment_key": key,
                    "name": FRAGMENT_LABELS.get(key, key),
                    "is_active": False,
                    "prompt_text": None,
                    "content_json": None,
                    "active_version_id": None,
                }
            )
            continue
        ver = versions.get(t.active_version_id) if t.active_version_id else None
        result.append(
            {
                "id": t.id,
                "fragment_key": t.fragment_key,
                "name": t.name,
                "description": t.description,
                "is_active": t.is_active,
                "prompt_text": ver.prompt_text if ver else None,
                "content_json": ver.content_json if ver else None,
                "active_version_id": t.active_version_id,
            }
        )
    return result


@router.post("/fragments")
def upsert_fragment(body: PromptFragmentUpsert, user: RequireAdmin, db: Session = Depends(get_db)):
    import json

    from app.models import PromptFragment, PromptFragmentVersion
    from app.prompt_engine.fragment_defaults import ENVIRONMENT_POOL, FRAGMENT_LABELS

    key = body.fragment_key or body.key
    if not key:
        raise HTTPException(status_code=400, detail="fragment_key required")
    prompt_text = body.prompt_text
    content_json = body.content_json
    if key == ENVIRONMENT_POOL and content_json is None and prompt_text:
        try:
            content_json = json.loads(prompt_text)
        except json.JSONDecodeError:
            content_json = [ln.strip() for ln in prompt_text.splitlines() if ln.strip()]
            prompt_text = json.dumps(content_json, indent=2)
    if prompt_text is None and content_json is not None:
        prompt_text = json.dumps(content_json, indent=2) if not isinstance(content_json, str) else content_json
    if prompt_text is None:
        raise HTTPException(status_code=400, detail="prompt_text required")

    frag = db.query(PromptFragment).filter(PromptFragment.fragment_key == key).first()
    if not frag:
        frag = PromptFragment(
            fragment_key=key,
            name=body.name or FRAGMENT_LABELS.get(key, key),
            description=body.description,
            is_active=True,
        )
        db.add(frag)
        db.flush()

    last_ver = (
        db.query(PromptFragmentVersion)
        .filter(PromptFragmentVersion.fragment_id == frag.id)
        .order_by(PromptFragmentVersion.version.desc())
        .first()
    )
    version_num = (last_ver.version + 1) if last_ver else 1
    db.query(PromptFragmentVersion).filter(PromptFragmentVersion.fragment_id == frag.id).update(
        {"is_active": False}
    )
    ver = PromptFragmentVersion(
        fragment_id=frag.id,
        version=version_num,
        prompt_text=prompt_text,
        content_json=content_json,
        is_active=True,
        source="admin",
    )
    db.add(ver)
    db.flush()
    frag.active_version_id = ver.id
    frag.name = body.name or frag.name
    if body.description is not None:
        frag.description = body.description
    frag.is_active = body.is_active
    db.commit()
    return {"id": frag.id, "version_id": ver.id, "version": version_num}


@router.get("/fragments/{fragment_id}/versions")
def list_fragment_versions(fragment_id: str, user: RequireAdmin, db: Session = Depends(get_db)):
    from app.models import PromptFragmentVersion

    rows = (
        db.query(PromptFragmentVersion)
        .filter(PromptFragmentVersion.fragment_id == fragment_id)
        .order_by(PromptFragmentVersion.version.desc())
        .all()
    )
    return [_serialize_fragment_version(v) for v in rows]


@router.post("/fragments/{fragment_id}/activate/{version_id}")
def activate_fragment_version(
    fragment_id: str, version_id: str, user: RequireAdmin, db: Session = Depends(get_db)
):
    from app.models import PromptFragment, PromptFragmentVersion

    frag = db.query(PromptFragment).filter(PromptFragment.id == fragment_id).first()
    if not frag:
        raise HTTPException(status_code=404, detail="Fragment not found")
    ver = (
        db.query(PromptFragmentVersion)
        .filter(PromptFragmentVersion.id == version_id, PromptFragmentVersion.fragment_id == fragment_id)
        .first()
    )
    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")
    db.query(PromptFragmentVersion).filter(PromptFragmentVersion.fragment_id == fragment_id).update(
        {"is_active": False}
    )
    ver.is_active = True
    frag.active_version_id = ver.id
    db.commit()
    return {"id": frag.id, "active_version_id": ver.id}


@router.post("/import-from-files")
def import_prompts_from_files(user: RequireAdmin, db: Session = Depends(get_db), force: bool = True):
    """Migration / disaster recovery: re-import docs/Modals/Prompts/*.txt into DB.

    Prefer day-to-day edits via Admin UI. Rows with source=admin are skipped unless force=true.
    """
    from seeds.import_prompts_folder import import_prompts_folder

    try:
        stats = import_prompts_folder(db, force=force)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}") from exc
    return {
        "ok": True,
        "mode": "migration",
        "force": force,
        "note": "Admin-authored versions are preserved unless force=true overwrites.",
        **stats,
    }
