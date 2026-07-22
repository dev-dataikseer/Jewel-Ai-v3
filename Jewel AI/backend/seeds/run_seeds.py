from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.config import get_settings
from app.models import (
    PromptMasterTemplate,
    PromptMasterVersion,
    PromptSubject,
    PromptSubjectVersion,
    User,
)
from app.pipeline.layers import (
    default_master_scaffold,
    default_subject_scaffold,
    layers_from_legacy_master,
    layers_from_legacy_subject,
)
from app.providers.registry import seed_model_definitions, seed_providers
from seeds.prompts_data import JEWELRY_TYPES, WORKFLOWS

settings = get_settings()


def seed_admin_user(db: Session) -> None:
    email = settings.admin_email.strip()
    password = settings.admin_password.strip()
    if not email or not password:
        return

    # Do not delete other admins on every boot — that is destructive.
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        existing.is_active = True
        existing.role = "admin"
        # Only reset password when explicitly forced.
        if settings.force_seed_passwords:
            existing.hashed_password = hash_password(password)
    else:
        db.add(
            User(
                email=email,
                hashed_password=hash_password(password),
                name="Admin",
                role="admin",
                credits=10000,
            )
        )
    db.commit()


def seed_default_user(db: Session) -> None:
    email = settings.default_user_email.strip()
    password = settings.default_user_password.strip()
    if not email or not password:
        return

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        existing.is_active = True
        if existing.role == "admin" and email != settings.admin_email.strip():
            existing.role = "user"
        if settings.force_seed_passwords:
            existing.hashed_password = hash_password(password)
    else:
        db.add(
            User(
                email=email,
                hashed_password=hash_password(password),
                name="Studio User",
                role="user",
                credits=500,
            )
        )
    db.commit()


def _ensure_master_template(db: Session, wf_id: str, wf_label: str) -> None:
    tmpl = db.query(PromptMasterTemplate).filter(PromptMasterTemplate.workflow == wf_id).first()
    if tmpl:
        return
    tmpl = PromptMasterTemplate(workflow=wf_id, name=wf_label, is_active=True)
    db.add(tmpl)
    db.flush()
    ver = PromptMasterVersion(
        template_id=tmpl.id,
        version=1,
        composition_mode="layered",
        layers=default_master_scaffold(),
        raw_override=None,
        is_active=True,
    )
    db.add(ver)
    db.flush()
    tmpl.active_version_id = ver.id


def _ensure_subject(db: Session, workflow: str, jewelry_type: str) -> None:
    subj = (
        db.query(PromptSubject)
        .filter(PromptSubject.workflow == workflow, PromptSubject.jewelry_type == jewelry_type)
        .first()
    )
    if subj:
        return
    subj = PromptSubject(workflow=workflow, jewelry_type=jewelry_type, is_active=True)
    db.add(subj)
    db.flush()
    sver = PromptSubjectVersion(
        subject_id=subj.id,
        version=1,
        composition_mode="layered",
        layers=default_subject_scaffold(),
        raw_override=None,
        is_active=True,
    )
    db.add(sver)
    db.flush()
    subj.active_version_id = sver.id


def _backfill_layers(db: Session) -> None:
    """One-time migration for rows that predate layer JSON — never overwrites existing layers."""
    for ver in db.query(PromptMasterVersion).filter(PromptMasterVersion.is_active == True).all():  # noqa: E712
        if ver.layers is not None:
            continue
        ver.layers = layers_from_legacy_master(
            {
                "system_role": ver.system_role,
                "camera_settings": ver.camera_settings,
                "environment": ver.environment,
                "lighting_and_physics": ver.lighting_and_physics,
                "preservation_lock": ver.preservation_lock,
                "negative_prompt": ver.negative_prompt,
            }
        )
        ver.composition_mode = ver.composition_mode or "layered"
    for ver in db.query(PromptSubjectVersion).filter(PromptSubjectVersion.is_active == True).all():  # noqa: E712
        if ver.layers is not None:
            continue
        ver.layers = layers_from_legacy_subject(
            {
                "core_description": ver.core_description,
                "anatomy_interaction": ver.anatomy_interaction,
                "physics_and_gravity": ver.physics_and_gravity,
                "placement_rules": ver.placement_rules,
            }
        )
        ver.composition_mode = ver.composition_mode or "layered"


def seed_prompts(db: Session) -> None:
    """Create empty master/subject shells + fragment shells.

    Prompt *content* is authored in Admin UI (or explicit Admin import-from-files).
    Boot no longer auto-imports docs/Modals/Prompts — that caused Railway path noise
    and bypassed Admin as the source of truth.
    """
    for wf in WORKFLOWS:
        _ensure_master_template(db, wf["id"], wf.get("label", wf["id"]))

    for wf in WORKFLOWS:
        for jt in JEWELRY_TYPES:
            _ensure_subject(db, wf["id"], jt)

    _backfill_layers(db)
    db.commit()

    from app.prompt_engine.fragment_store import seed_prompt_fragments

    seed_prompt_fragments(db)

    # Explicit opt-in only (ALLOW_PROMPT_RESEED=true). Never run silently in production.
    from app.config import get_settings

    if get_settings().effective_allow_prompt_reseed:
        try:
            from seeds.import_prompts_folder import import_prompts_folder

            stats = import_prompts_folder(db, force=False)
            import logging

            logging.getLogger(__name__).info(
                "prompts folder import (ALLOW_PROMPT_RESEED): fragments=%s masters=%s subjects=%s",
                stats.get("fragments"),
                stats.get("masters"),
                stats.get("subjects"),
            )
        except Exception:
            import logging

            logging.getLogger(__name__).exception("prompts folder import skipped")


def run_all_seeds(db: Session) -> None:
    seed_admin_user(db)
    seed_default_user(db)
    seed_prompts(db)
    seed_providers(db)
    seed_model_definitions(db)
