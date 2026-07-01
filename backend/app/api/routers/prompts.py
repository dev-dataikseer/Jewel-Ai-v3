from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import RequireAdmin, RequireOperator
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
from app.pipeline.composer import ComposeInput, compose_prompt
from app.pipeline.layer_derive import (
    assemble_raw_text_from_layers,
    default_structural_config,
    derive_layers_from_raw_text,
)
from app.pipeline.layer_validate import validate_master_layers, validate_subject_layers
from app.pipeline.layers import sort_layers
from app.providers.prompt_augment import augment_prompt_for_workflow
from app.providers.model_validate import validate_generation_request, validate_model_params
from app.providers.registry import get_model_definition
from app.providers.router import route_generation
from app.providers.types import GenerationRequest
from app.schemas.common import PromptTestRequest, PromptTestResponse
from app.storage.local import storage
from app.tasks.generate import process_image_job

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


@router.get("/templates")
def list_templates(db: Session = Depends(get_db)):
    rows = db.query(PromptMasterTemplate).all()
    result = []
    for t in rows:
        ver = (
            db.query(PromptMasterVersion).filter(PromptMasterVersion.id == t.active_version_id).first()
            if t.active_version_id
            else None
        )
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
def upsert_template(body: dict, user: RequireAdmin, db: Session = Depends(get_db)):
    workflow = body["workflow"]
    tmpl = db.query(PromptMasterTemplate).filter(PromptMasterTemplate.workflow == workflow).first()
    if not tmpl:
        tmpl = PromptMasterTemplate(workflow=workflow, name=body.get("name", workflow), is_active=True)
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
    if body.get("layers"):
        layers = sort_layers(body["layers"])
        validate_master_layers(layers)
        prompt_text = body.get("prompt_text") or assemble_raw_text_from_layers(layers)
    else:
        prompt_text = body.get("prompt_text") or ""
        layers = derive_layers_from_raw_text(prompt_text, workflow, scope="master", structural_config=structural)
        validate_master_layers(layers)

    ver = PromptMasterVersion(
        template_id=tmpl.id,
        version=version_num,
        prompt_text=prompt_text,
        composition_mode=body.get("composition_mode", "layered"),
        layers=layers,
        raw_override=body.get("raw_override"),
        is_active=True,
        source="admin",
    )
    db.add(ver)
    db.flush()
    tmpl.active_version_id = ver.id
    tmpl.is_active = body.get("is_active", True)
    db.commit()
    return {"id": tmpl.id, "version_id": ver.id, "version": version_num}


@router.get("/subjects")
def list_subjects(workflow: str | None = None, db: Session = Depends(get_db)):
    q = db.query(PromptSubject)
    if workflow:
        q = q.filter(PromptSubject.workflow == workflow)
    rows = q.all()
    result = []
    for s in rows:
        ver = (
            db.query(PromptSubjectVersion).filter(PromptSubjectVersion.id == s.active_version_id).first()
            if s.active_version_id
            else None
        )
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
def upsert_subject(body: dict, user: RequireAdmin, db: Session = Depends(get_db)):
    jt = body["jewelry_type"]
    workflow = body.get("workflow", "CATALOG_IMAGE")
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

    if body.get("layers"):
        layers = sort_layers(body["layers"])
        validate_subject_layers(layers)
        prompt_text = body.get("prompt_text") or assemble_raw_text_from_layers(layers)
    else:
        prompt_text = body.get("prompt_text") or ""
        layers = derive_layers_from_raw_text(prompt_text, workflow, scope="subject")
        validate_subject_layers(layers)

    ver = PromptSubjectVersion(
        subject_id=subj.id,
        version=vnum,
        prompt_text=prompt_text,
        composition_mode=body.get("composition_mode", "layered"),
        layers=layers,
        raw_override=body.get("raw_override"),
        is_active=True,
        source="admin",
    )
    db.add(ver)
    db.flush()
    subj.active_version_id = ver.id
    subj.is_active = body.get("is_active", True)
    db.commit()
    return {"id": subj.id, "version_id": ver.id}


@router.get("/variants")
def list_variants(workflow: str | None = None, db: Session = Depends(get_db)):
    q = db.query(PromptVariant)
    if workflow:
        q = q.filter(PromptVariant.workflow == workflow)
    rows = q.order_by(PromptVariant.sort_order).all()
    result = []
    for v in rows:
        ver = (
            db.query(PromptVariantVersion).filter(PromptVariantVersion.id == v.active_version_id).first()
            if v.active_version_id
            else None
        )
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
def upsert_variant(body: dict, user: RequireAdmin, db: Session = Depends(get_db)):
    var = db.query(PromptVariant).filter(
        PromptVariant.workflow == body["workflow"],
        PromptVariant.variant_key == body["variant_key"],
    ).first()
    if not var:
        var = PromptVariant(
            workflow=body["workflow"],
            variant_key=body["variant_key"],
            label=body.get("label", body["variant_key"]),
            sort_order=body.get("sort_order", 0),
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
        prompt_text=body["prompt_text"],
        negative_addon=body.get("negative_addon"),
        is_active=True,
    )
    db.add(ver)
    db.flush()
    var.active_version_id = ver.id
    db.commit()
    return {"id": var.id, "version_id": ver.id}


@router.get("/workflows/{workflow}/layer-config")
def get_layer_config(workflow: str, db: Session = Depends(get_db)):
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
def list_presets(db: Session = Depends(get_db)):
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


@router.post("/test", response_model=PromptTestResponse)
def test_prompt(body: PromptTestRequest, user: RequireAdmin, db: Session = Depends(get_db)):
    composed = compose_prompt(db, ComposeInput(**body.model_dump()))
    return PromptTestResponse(prompt=composed.text, negative_prompt=composed.negative_prompt, debug=composed.debug)


@router.post("/test/generate")
async def test_generate(body: PromptTestRequest, user: RequireAdmin, db: Session = Depends(get_db)):
    composed = compose_prompt(db, ComposeInput(**body.model_dump(exclude={"model_endpoint_id", "model_params"})))
    prompt = augment_prompt_for_workflow(body.workflow, composed.text)
    endpoint = body.model_endpoint_id
    model_def = get_model_definition(db, endpoint) if endpoint else None
    if endpoint and not model_def:
        raise HTTPException(status_code=400, detail=f"Unknown model: {endpoint}")
    params = validate_model_params(model_def, body.model_params)
    request = GenerationRequest(
        prompt=prompt,
        negative_prompt=composed.negative_prompt,
        workflow=body.workflow,
        model_endpoint_id=endpoint,
        model_params=params,
    )
    validate_generation_request(model_def, request)
    result, chain = await route_generation(db, request)
    url = storage.save_bytes(result.image_bytes, filename=f"test_{body.workflow}.png")
    return {
        "output_url": url,
        "prompt": prompt,
        "provider": result.provider,
        "model": result.model,
        "chain": chain,
        "debug": composed.debug,
        "version_ids": {
            "master": composed.master_version_id,
            "subject": composed.subject_version_id,
            "variant": composed.variant_version_id,
        },
    }
