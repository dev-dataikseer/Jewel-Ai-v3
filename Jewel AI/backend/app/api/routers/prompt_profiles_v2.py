"""Prompt Profile V2 Admin API — JSON profiles, jewelry sections, image roles."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import RequireAdmin, RequireUser
from app.database import get_db
from app.models import (
    PromptImageRole,
    PromptJewelrySection,
    PromptJewelrySectionVersion,
    PromptProfile,
    PromptProfileVersion,
)
from app.prompt_engine.profile_compose import (
    DEFAULT_IMAGE_ROLES,
    REF_WITH,
    REF_WITHOUT,
    serialize_sections,
)

router = APIRouter(prefix="/prompts", tags=["prompt-profiles-v2"])

VALID_REF_MODES = {REF_WITHOUT, REF_WITH}
VALID_IMAGE_ROLES = set(DEFAULT_IMAGE_ROLES.keys())


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def _validate_content(content: dict[str, Any]) -> dict[str, str]:
    if not isinstance(content, dict):
        raise HTTPException(status_code=400, detail="content_json must be an object")
    import re

    out: dict[str, str] = {}
    for k, v in content.items():
        key = str(k).strip()
        if not key:
            continue
        # Strip legacy {{PLACEHOLDER}} tokens; V2 does not use them
        text = "" if v is None else str(v)
        text = re.sub(r"\{\{[A-Z0-9_]+\}\}", "", text).strip()
        out[key] = text
    return out


# ── Profiles ─────────────────────────────────────────────────────────────────


class ProfileUpsert(BaseModel):
    content_json: dict[str, Any] = Field(default_factory=dict)
    environment_pool: Optional[list[str]] = None
    name: Optional[str] = None
    is_active: bool = True


@router.get("/profiles")
def list_profiles(user: RequireUser, workflow: str | None = None, db: Session = Depends(get_db)):
    q = db.query(PromptProfile).order_by(PromptProfile.workflow.asc(), PromptProfile.reference_mode.asc())
    if workflow:
        q = q.filter(PromptProfile.workflow == workflow.upper())
    rows = q.all()
    active_ids = [r.active_version_id for r in rows if r.active_version_id]
    versions = {}
    if active_ids:
        versions = {
            v.id: v
            for v in db.query(PromptProfileVersion).filter(PromptProfileVersion.id.in_(active_ids)).all()
        }
    result = []
    for r in rows:
        ver = versions.get(r.active_version_id) if r.active_version_id else None
        result.append(
            {
                "id": r.id,
                "workflow": r.workflow,
                "reference_mode": r.reference_mode,
                "name": r.name,
                "is_active": r.is_active,
                "active_version_id": r.active_version_id,
                "content_json": ver.content_json if ver else {},
                "environment_pool": ver.environment_pool if ver else None,
                "version": ver.version if ver else None,
                "updated_at": _iso(r.updated_at),
            }
        )
    return result


@router.get("/profiles/{workflow}/{reference_mode}")
def get_profile(workflow: str, reference_mode: str, user: RequireUser, db: Session = Depends(get_db)):
    mode = reference_mode.lower()
    if mode not in VALID_REF_MODES:
        raise HTTPException(status_code=400, detail=f"reference_mode must be one of {sorted(VALID_REF_MODES)}")
    profile = (
        db.query(PromptProfile)
        .filter(PromptProfile.workflow == workflow.upper(), PromptProfile.reference_mode == mode)
        .first()
    )
    if not profile:
        return {
            "id": None,
            "workflow": workflow.upper(),
            "reference_mode": mode,
            "name": f"{workflow} ({mode})",
            "is_active": True,
            "active_version_id": None,
            "content_json": {},
            "environment_pool": None,
            "version": None,
            "versions": [],
        }
    versions = (
        db.query(PromptProfileVersion)
        .filter(PromptProfileVersion.profile_id == profile.id)
        .order_by(PromptProfileVersion.version.desc())
        .all()
    )
    active = next((v for v in versions if v.id == profile.active_version_id), versions[0] if versions else None)
    return {
        "id": profile.id,
        "workflow": profile.workflow,
        "reference_mode": profile.reference_mode,
        "name": profile.name,
        "is_active": profile.is_active,
        "active_version_id": profile.active_version_id,
        "content_json": active.content_json if active else {},
        "environment_pool": active.environment_pool if active else None,
        "version": active.version if active else None,
        "versions": [
            {
                "id": v.id,
                "version": v.version,
                "is_active": v.is_active,
                "source": v.source,
                "created_at": _iso(v.created_at),
                "content_json": v.content_json,
                "environment_pool": v.environment_pool,
            }
            for v in versions
        ],
    }


@router.put("/profiles/{workflow}/{reference_mode}")
def upsert_profile(
    workflow: str,
    reference_mode: str,
    body: ProfileUpsert,
    user: RequireAdmin,
    db: Session = Depends(get_db),
):
    mode = reference_mode.lower()
    if mode not in VALID_REF_MODES:
        raise HTTPException(status_code=400, detail=f"reference_mode must be one of {sorted(VALID_REF_MODES)}")
    wf = workflow.upper()
    content = _validate_content(body.content_json)

    profile = (
        db.query(PromptProfile)
        .filter(PromptProfile.workflow == wf, PromptProfile.reference_mode == mode)
        .first()
    )
    if not profile:
        profile = PromptProfile(
            workflow=wf,
            reference_mode=mode,
            name=body.name or f"{wf.replace('_', ' ').title()} — {mode.replace('_', ' ')}",
            is_active=True,
        )
        db.add(profile)
        db.flush()
    elif body.name:
        profile.name = body.name
    profile.is_active = body.is_active

    last = (
        db.query(PromptProfileVersion)
        .filter(PromptProfileVersion.profile_id == profile.id)
        .order_by(PromptProfileVersion.version.desc())
        .first()
    )
    version_num = (last.version + 1) if last else 1
    db.query(PromptProfileVersion).filter(PromptProfileVersion.profile_id == profile.id).update(
        {"is_active": False}
    )
    ver = PromptProfileVersion(
        profile_id=profile.id,
        version=version_num,
        content_json=content,
        environment_pool=body.environment_pool,
        is_active=True,
        source="admin",
    )
    db.add(ver)
    db.flush()
    profile.active_version_id = ver.id
    db.commit()
    return {
        "id": profile.id,
        "version_id": ver.id,
        "version": version_num,
        "workflow": wf,
        "reference_mode": mode,
    }


@router.post("/profiles/{profile_id}/activate/{version_id}")
def activate_profile_version(
    profile_id: str, version_id: str, user: RequireAdmin, db: Session = Depends(get_db)
):
    profile = db.query(PromptProfile).filter(PromptProfile.id == profile_id).first()
    ver = (
        db.query(PromptProfileVersion)
        .filter(PromptProfileVersion.id == version_id, PromptProfileVersion.profile_id == profile_id)
        .first()
    )
    if not profile or not ver:
        raise HTTPException(status_code=404)
    db.query(PromptProfileVersion).filter(PromptProfileVersion.profile_id == profile_id).update(
        {"is_active": False}
    )
    ver.is_active = True
    profile.active_version_id = ver.id
    db.commit()
    return {"success": True, "active_version_id": ver.id}


# ── Jewelry sections ─────────────────────────────────────────────────────────


class JewelryUpsert(BaseModel):
    content_json: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


@router.get("/jewelry")
def list_jewelry(user: RequireUser, workflow: str | None = None, db: Session = Depends(get_db)):
    q = db.query(PromptJewelrySection).order_by(
        PromptJewelrySection.workflow.asc(), PromptJewelrySection.jewelry_type.asc()
    )
    if workflow:
        q = q.filter(PromptJewelrySection.workflow == workflow.upper())
    rows = q.all()
    active_ids = [r.active_version_id for r in rows if r.active_version_id]
    versions = {}
    if active_ids:
        versions = {
            v.id: v
            for v in db.query(PromptJewelrySectionVersion)
            .filter(PromptJewelrySectionVersion.id.in_(active_ids))
            .all()
        }
    return [
        {
            "id": r.id,
            "workflow": r.workflow,
            "jewelry_type": r.jewelry_type,
            "is_active": r.is_active,
            "active_version_id": r.active_version_id,
            "content_json": versions[r.active_version_id].content_json
            if r.active_version_id and r.active_version_id in versions
            else {},
            "version": versions[r.active_version_id].version
            if r.active_version_id and r.active_version_id in versions
            else None,
        }
        for r in rows
    ]


@router.get("/jewelry/{workflow}/{jewelry_type}")
def get_jewelry(workflow: str, jewelry_type: str, user: RequireUser, db: Session = Depends(get_db)):
    section = (
        db.query(PromptJewelrySection)
        .filter(
            PromptJewelrySection.workflow == workflow.upper(),
            PromptJewelrySection.jewelry_type == jewelry_type,
        )
        .first()
    )
    if not section:
        return {
            "id": None,
            "workflow": workflow.upper(),
            "jewelry_type": jewelry_type,
            "content_json": {},
            "versions": [],
        }
    versions = (
        db.query(PromptJewelrySectionVersion)
        .filter(PromptJewelrySectionVersion.section_id == section.id)
        .order_by(PromptJewelrySectionVersion.version.desc())
        .all()
    )
    active = next(
        (v for v in versions if v.id == section.active_version_id),
        versions[0] if versions else None,
    )
    return {
        "id": section.id,
        "workflow": section.workflow,
        "jewelry_type": section.jewelry_type,
        "is_active": section.is_active,
        "active_version_id": section.active_version_id,
        "content_json": active.content_json if active else {},
        "version": active.version if active else None,
        "versions": [
            {
                "id": v.id,
                "version": v.version,
                "is_active": v.is_active,
                "source": v.source,
                "created_at": _iso(v.created_at),
                "content_json": v.content_json,
            }
            for v in versions
        ],
    }


@router.put("/jewelry/{workflow}/{jewelry_type}")
def upsert_jewelry(
    workflow: str,
    jewelry_type: str,
    body: JewelryUpsert,
    user: RequireAdmin,
    db: Session = Depends(get_db),
):
    wf = workflow.upper()
    content = _validate_content(body.content_json)
    section = (
        db.query(PromptJewelrySection)
        .filter(PromptJewelrySection.workflow == wf, PromptJewelrySection.jewelry_type == jewelry_type)
        .first()
    )
    if not section:
        section = PromptJewelrySection(workflow=wf, jewelry_type=jewelry_type, is_active=True)
        db.add(section)
        db.flush()
    section.is_active = body.is_active

    last = (
        db.query(PromptJewelrySectionVersion)
        .filter(PromptJewelrySectionVersion.section_id == section.id)
        .order_by(PromptJewelrySectionVersion.version.desc())
        .first()
    )
    version_num = (last.version + 1) if last else 1
    db.query(PromptJewelrySectionVersion).filter(
        PromptJewelrySectionVersion.section_id == section.id
    ).update({"is_active": False})
    ver = PromptJewelrySectionVersion(
        section_id=section.id,
        version=version_num,
        content_json=content,
        is_active=True,
        source="admin",
    )
    db.add(ver)
    db.flush()
    section.active_version_id = ver.id

    # Mirror into legacy PromptSubject layers so V1 compose also gets the jewelry prompt
    # (Admin Prompt Studio is the source of truth for per-type subject text).
    try:
        from app.models import PromptSubject, PromptSubjectVersion

        body_parts = [f"{k}: {v}" for k, v in content.items() if (v or "").strip()]
        subject_text = "\n\n".join(body_parts).strip()
        subj = (
            db.query(PromptSubject)
            .filter(PromptSubject.workflow == wf, PromptSubject.jewelry_type == jewelry_type)
            .first()
        )
        if not subj:
            subj = PromptSubject(workflow=wf, jewelry_type=jewelry_type, is_active=True)
            db.add(subj)
            db.flush()
        last_s = (
            db.query(PromptSubjectVersion)
            .filter(PromptSubjectVersion.subject_id == subj.id)
            .order_by(PromptSubjectVersion.version.desc())
            .first()
        )
        s_ver_num = (last_s.version + 1) if last_s else 1
        db.query(PromptSubjectVersion).filter(PromptSubjectVersion.subject_id == subj.id).update(
            {"is_active": False}
        )
        sver = PromptSubjectVersion(
            subject_id=subj.id,
            version=s_ver_num,
            composition_mode="layered",
            layers=[
                {
                    "key": "jewelry_prompt",
                    "label": "Jewelry prompt",
                    "order": 1,
                    "content": subject_text,
                    "locked": False,
                    "type": "text",
                    "enabled": True,
                }
            ],
            prompt_text=subject_text,
            is_active=True,
            source="admin_jewelry_sync",
        )
        db.add(sver)
        db.flush()
        subj.active_version_id = sver.id
        subj.is_active = True
    except Exception:
        pass

    db.commit()
    return {"id": section.id, "version_id": ver.id, "version": version_num}


@router.post("/jewelry/{section_id}/activate/{version_id}")
def activate_jewelry_version(
    section_id: str, version_id: str, user: RequireAdmin, db: Session = Depends(get_db)
):
    section = db.query(PromptJewelrySection).filter(PromptJewelrySection.id == section_id).first()
    ver = (
        db.query(PromptJewelrySectionVersion)
        .filter(
            PromptJewelrySectionVersion.id == version_id,
            PromptJewelrySectionVersion.section_id == section_id,
        )
        .first()
    )
    if not section or not ver:
        raise HTTPException(status_code=404)
    db.query(PromptJewelrySectionVersion).filter(
        PromptJewelrySectionVersion.section_id == section_id
    ).update({"is_active": False})
    ver.is_active = True
    section.active_version_id = ver.id
    db.commit()
    return {"success": True, "active_version_id": ver.id}


# ── Image roles ──────────────────────────────────────────────────────────────


class ImageRoleUpsert(BaseModel):
    role: str
    instruction: str
    name: Optional[str] = None
    workflow: Optional[str] = None  # null = global
    is_active: bool = True


@router.get("/image-roles")
def list_image_roles(user: RequireUser, workflow: str | None = None, db: Session = Depends(get_db)):
    rows = db.query(PromptImageRole).order_by(PromptImageRole.role.asc()).all()
    # Prefer workflow-specific when requested
    by_role: dict[str, Any] = {}
    for r in rows:
        if workflow and r.workflow and r.workflow != workflow.upper():
            continue
        if workflow and r.workflow is None and r.role in by_role:
            continue  # keep workflow override
        if r.role not in by_role or (r.workflow and workflow):
            by_role[r.role] = r

    result = []
    for role, (default_name, default_inst) in DEFAULT_IMAGE_ROLES.items():
        r = by_role.get(role)
        if r:
            result.append(
                {
                    "id": r.id,
                    "role": r.role,
                    "workflow": r.workflow,
                    "name": r.name,
                    "instruction": r.instruction,
                    "is_active": r.is_active,
                    "version": r.version,
                }
            )
        else:
            result.append(
                {
                    "id": None,
                    "role": role,
                    "workflow": None,
                    "name": default_name,
                    "instruction": default_inst,
                    "is_active": True,
                    "version": None,
                }
            )
    # Include any extra roles
    for r in rows:
        if r.role not in DEFAULT_IMAGE_ROLES:
            result.append(
                {
                    "id": r.id,
                    "role": r.role,
                    "workflow": r.workflow,
                    "name": r.name,
                    "instruction": r.instruction,
                    "is_active": r.is_active,
                    "version": r.version,
                }
            )
    return result


@router.put("/image-roles")
def upsert_image_role(body: ImageRoleUpsert, user: RequireAdmin, db: Session = Depends(get_db)):
    role = body.role.strip().lower()
    if role not in VALID_IMAGE_ROLES and role not in {"product", "theme", "portrait", "logo"}:
        raise HTTPException(status_code=400, detail=f"Unknown role: {role}")
    if "{{" in body.instruction and "{index}" not in body.instruction and "{{index}}" not in body.instruction:
        # allow {index} only
        pass
    wf = body.workflow.upper() if body.workflow else None
    q = db.query(PromptImageRole).filter(PromptImageRole.role == role)
    if wf:
        q = q.filter(PromptImageRole.workflow == wf)
    else:
        q = q.filter(PromptImageRole.workflow.is_(None))
    row = q.first()
    default_name = DEFAULT_IMAGE_ROLES.get(role, (role, ""))[0]
    if not row:
        row = PromptImageRole(
            role=role,
            workflow=wf,
            name=body.name or default_name,
            instruction=body.instruction,
            is_active=body.is_active,
            version=1,
            source="admin",
        )
        db.add(row)
    else:
        row.instruction = body.instruction
        row.name = body.name or row.name
        row.is_active = body.is_active
        row.version = (row.version or 1) + 1
        row.source = "admin"
    db.commit()
    return {"id": row.id, "role": row.role, "workflow": row.workflow, "version": row.version}


# ── Assemble preview ─────────────────────────────────────────────────────────


class AssembleBody(BaseModel):
    workflow: str = "CATALOG_IMAGE"
    jewelry_type: str = "Ring"
    prompt_text: Optional[str] = None
    metal_type: Optional[str] = None
    gemstone_target_color: Optional[str] = None
    background_style: Optional[str] = None
    catalog_mode: Optional[str] = None
    try_on_mode: Optional[str] = None
    style_preset_addon: Optional[str] = None
    simulate_images: dict[str, bool] = Field(
        default_factory=lambda: {"product": True, "theme": False, "portrait": False, "logo": False}
    )
    # When set, force reference mode for preview (ignore simulate for mode pick)
    reference_mode: Optional[str] = None


@router.post("/assemble")
def assemble_preview(body: AssembleBody, user: RequireAdmin, db: Session = Depends(get_db)):
    """Live compose preview for Prompt Studio (V2 path when profiles exist / flag on)."""
    from app.pipeline.composer import ComposeInput
    from app.prompt_engine.attachments import ImageContext
    from app.prompt_engine.engine import build_final_prompt
    from app.prompt_engine.profile_compose import (
        compose_from_profiles,
        resolve_reference_mode,
    )

    sim = body.simulate_images or {}
    has_theme = bool(sim.get("theme"))
    has_portrait = bool(sim.get("portrait"))
    has_logo = bool(sim.get("logo"))
    has_product = bool(sim.get("product", True))

    roles = []
    idx = 1
    if has_product:
        roles.append({"index": idx, "role": "product"})
        idx += 1
    if has_theme:
        roles.append({"index": idx, "role": "theme"})
        idx += 1
    if has_portrait:
        roles.append({"index": idx, "role": "portrait"})
        idx += 1
    if has_logo:
        roles.append({"index": idx, "role": "logo"})

    ctx = ImageContext(
        has_product=has_product,
        has_style_reference=has_theme,
        has_portrait=has_portrait,
        has_logo=has_logo,
        image_count=len(roles) or 1,
        roles=roles,
    )

    # Force mode for studio preview of a specific page
    if body.reference_mode in VALID_REF_MODES:
        if body.reference_mode == REF_WITH and not (has_theme or has_portrait or has_logo):
            # Ensure secondary flag so resolve picks with_reference
            ctx = ImageContext(
                has_product=has_product,
                has_style_reference=True,
                has_portrait=False,
                has_logo=False,
                image_count=2 if has_product else 1,
                roles=(
                    [{"index": 1, "role": "product"}, {"index": 2, "role": "theme"}]
                    if has_product
                    else [{"index": 1, "role": "theme"}]
                ),
            )
        elif body.reference_mode == REF_WITHOUT:
            ctx = ImageContext(
                has_product=has_product,
                has_style_reference=False,
                has_portrait=False,
                has_logo=False,
                image_count=1 if has_product else 0,
                roles=[{"index": 1, "role": "product"}] if has_product else [],
            )

    inp = ComposeInput(
        workflow=body.workflow,
        jewelry_type=body.jewelry_type,
        prompt_text=body.prompt_text,
        metal_type=body.metal_type,
        gemstone_target_color=body.gemstone_target_color,
        background_style=body.background_style,
        catalog_mode=body.catalog_mode,
        try_on_mode=body.try_on_mode,
        style_preset_addon=body.style_preset_addon,
    )

    from app.prompt_engine.profile_compose import should_use_profile_v2_compose

    use_v2 = should_use_profile_v2_compose(
        db,
        workflow=body.workflow,
        jewelry_type=body.jewelry_type,
        has_reference=bool(ctx and ctx.has_style_reference),
    )

    if use_v2:
        result = compose_from_profiles(db, inp, image_ctx=ctx)
        text, negatives = serialize_sections(result.sections)
        return {
            "final_prompt": text,
            "prompt": text,
            "negative_prompt": "\n".join(negatives) if negatives else None,
            "reference_mode": result.reference_mode,
            "sections": result.sections,
            "debug": result.debug,
            "composePath": "profile_v2",
        }

    final = build_final_prompt(db, inp, image_ctx=ctx)
    return {
        "final_prompt": final.text,
        "prompt": final.text,
        "negative_prompt": final.negative_prompt or None,
        "reference_mode": resolve_reference_mode(ctx),
        "debug": final.debug,
        "composePath": "legacy_v1",
    }
