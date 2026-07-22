"""Migrate legacy masters/subjects/fragments → Prompt Profile V2 tables.

Sources (in order):
  1. Live DB (prompt_master_*, prompt_subjects, prompt_fragments) — preferred
  2. Optional Prompts_Store/txt directory (--dir)

Usage:
  cd backend
  $env:DATABASE_URL = ...
  $env:PYTHONPATH = '.'
  python scripts/migrate_to_prompt_profiles.py
  python scripts/migrate_to_prompt_profiles.py --dir "../Prompts_Store"
  python scripts/migrate_to_prompt_profiles.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    PromptFragment,
    PromptFragmentVersion,
    PromptImageRole,
    PromptJewelrySection,
    PromptJewelrySectionVersion,
    PromptMasterTemplate,
    PromptMasterVersion,
    PromptProfile,
    PromptProfileVersion,
    PromptSubject,
    PromptSubjectVersion,
)
from app.pipeline.layer_derive import assemble_raw_text_from_layers
from app.pipeline.layers import sort_layers
from app.prompt_engine.profile_compose import (
    DEFAULT_IMAGE_ROLES,
    REF_WITH,
    REF_WITHOUT,
    parse_header_text,
)
from seeds.prompts_data import CANONICAL_WORKFLOWS, JEWELRY_TYPES

logger = logging.getLogger(__name__)

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")

FRAGMENT_KEYS = {
    "exec_modern": "EXEC_MODERN_CATALOG",
    "exec_ref": "EXEC_REFERENCE_MIRROR",
    "exec_style": "EXEC_STYLE_MOOD",
    "brand_cat_logo": "BRAND_CATALOG_WITH_LOGO",
    "brand_cat_nologo": "BRAND_CATALOG_NO_LOGO",
    "brand_ref_logo": "BRAND_REF_WITH_LOGO",
    "brand_ref_nologo": "BRAND_REF_NO_LOGO",
    "fidelity": "RAW_JEWELRY_FIDELITY_LOCK",
    "attach_product": "ATTACH_PRIMARY_SUBJECT",
    "attach_theme": "ATTACH_ENVIRONMENT_REFERENCE",
    "attach_logo": "ATTACH_LOGO",
    "attach_tryon": "ATTACH_TRY_ON",
    "env_pool": "ENVIRONMENT_POOL",
    "bg_ref": "BACKGROUND_SOURCE_REF",
    "bg_gen": "BACKGROUND_SOURCE_GENERATED",
    "custom_preserve": "CUSTOM_PRESERVE",
    "custom_realism": "CUSTOM_REALISM",
    "tryon_preserve": "TRYON_CUSTOMER_PRESERVE",
}

SUBJECT_STEM_MAP = {
    "ring": "Ring",
    "necklace": "Necklace",
    "bangle": "Bangles",
    "bracelet": "Bracelet",
    "kara": "Kara",
    "earring_stud": "Earrings (Studs)",
    "earring_drop": "Earrings (Drops)",
    "earring_hoop": "Earrings (Hoops)",
    "pendant": "Pendant",
    "watch": "Watch",
    "brooch": "Brooch",
    "anklet": "Anklet",
    "cufflinks": "Cufflinks",
    "multiple_items": "Multiple Items",
}


def _strip_placeholders(text: str) -> str:
    """Remove empty/legacy {{TOKEN}} lines from master text."""
    lines = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if PLACEHOLDER_RE.fullmatch(stripped):
            continue
        # Drop lines that are only a placeholder with optional punctuation
        cleaned = PLACEHOLDER_RE.sub("", line).rstrip()
        if cleaned.strip() or not stripped:
            lines.append(cleaned if PLACEHOLDER_RE.search(line) else line)
    return "\n".join(lines).strip()


def _display_master_text(ver: PromptMasterVersion | None) -> str:
    if not ver:
        return ""
    if ver.prompt_text:
        return ver.prompt_text.strip()
    if ver.layers:
        return (assemble_raw_text_from_layers(sort_layers(ver.layers)) or "").strip()
    return ""


def _fragment_text(db: Session, key: str) -> str:
    frag = db.query(PromptFragment).filter(PromptFragment.fragment_key == key).first()
    if not frag or not frag.active_version_id:
        return ""
    ver = db.query(PromptFragmentVersion).filter(PromptFragmentVersion.id == frag.active_version_id).first()
    return (ver.prompt_text or "").strip() if ver else ""


def _fragment_pool(db: Session) -> list[str]:
    frag = db.query(PromptFragment).filter(PromptFragment.fragment_key == "ENVIRONMENT_POOL").first()
    if not frag or not frag.active_version_id:
        return []
    ver = db.query(PromptFragmentVersion).filter(PromptFragmentVersion.id == frag.active_version_id).first()
    if not ver:
        return []
    if isinstance(ver.content_json, list):
        return [str(x).strip() for x in ver.content_json if str(x).strip()]
    try:
        parsed = json.loads(ver.prompt_text or "[]")
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except json.JSONDecodeError:
        pass
    return [ln.strip() for ln in (ver.prompt_text or "").splitlines() if ln.strip()]


def _merge_sections(*texts: str) -> dict[str, str]:
    merged: dict[str, str] = {}
    for text in texts:
        if not text:
            continue
        cleaned = _strip_placeholders(text)
        sections = parse_header_text(cleaned)
        if not sections and cleaned:
            sections = {"BODY": cleaned}
        for k, v in sections.items():
            if v.strip():
                merged[k] = v.strip()
    return merged


def _upsert_profile(
    db: Session,
    workflow: str,
    reference_mode: str,
    content: dict[str, str],
    *,
    environment_pool: list[str] | None = None,
    dry_run: bool = False,
) -> bool:
    if not content:
        return False
    if dry_run:
        logger.info("[dry-run] profile %s/%s keys=%s", workflow, reference_mode, list(content.keys()))
        return True

    profile = (
        db.query(PromptProfile)
        .filter(PromptProfile.workflow == workflow, PromptProfile.reference_mode == reference_mode)
        .first()
    )
    name = f"{workflow.replace('_', ' ').title()} — {reference_mode.replace('_', ' ')}"
    if not profile:
        profile = PromptProfile(
            id=str(uuid.uuid4()),
            workflow=workflow,
            reference_mode=reference_mode,
            name=name,
            is_active=True,
        )
        db.add(profile)
        db.flush()

    last = (
        db.query(PromptProfileVersion)
        .filter(PromptProfileVersion.profile_id == profile.id)
        .order_by(PromptProfileVersion.version.desc())
        .first()
    )
    # Skip if identical
    if last and last.content_json == content and (last.environment_pool or None) == (environment_pool or None):
        if not profile.active_version_id:
            profile.active_version_id = last.id
        return False

    version_num = (last.version + 1) if last else 1
    db.query(PromptProfileVersion).filter(PromptProfileVersion.profile_id == profile.id).update(
        {"is_active": False}
    )
    ver = PromptProfileVersion(
        id=str(uuid.uuid4()),
        profile_id=profile.id,
        version=version_num,
        content_json=content,
        environment_pool=environment_pool,
        is_active=True,
        source="migration",
    )
    db.add(ver)
    db.flush()
    profile.active_version_id = ver.id
    profile.name = name
    return True


def _upsert_jewelry(
    db: Session,
    workflow: str,
    jewelry_type: str,
    content: dict[str, str],
    *,
    dry_run: bool = False,
) -> bool:
    if not content:
        return False
    if dry_run:
        logger.info("[dry-run] jewelry %s/%s keys=%s", workflow, jewelry_type, list(content.keys()))
        return True

    section = (
        db.query(PromptJewelrySection)
        .filter(
            PromptJewelrySection.workflow == workflow,
            PromptJewelrySection.jewelry_type == jewelry_type,
        )
        .first()
    )
    if not section:
        section = PromptJewelrySection(
            id=str(uuid.uuid4()),
            workflow=workflow,
            jewelry_type=jewelry_type,
            is_active=True,
        )
        db.add(section)
        db.flush()

    last = (
        db.query(PromptJewelrySectionVersion)
        .filter(PromptJewelrySectionVersion.section_id == section.id)
        .order_by(PromptJewelrySectionVersion.version.desc())
        .first()
    )
    if last and last.content_json == content:
        if not section.active_version_id:
            section.active_version_id = last.id
        return False

    version_num = (last.version + 1) if last else 1
    db.query(PromptJewelrySectionVersion).filter(
        PromptJewelrySectionVersion.section_id == section.id
    ).update({"is_active": False})
    ver = PromptJewelrySectionVersion(
        id=str(uuid.uuid4()),
        section_id=section.id,
        version=version_num,
        content_json=content,
        is_active=True,
        source="migration",
    )
    db.add(ver)
    db.flush()
    section.active_version_id = ver.id
    return True


def _upsert_image_role(
    db: Session,
    role: str,
    instruction: str,
    *,
    name: str | None = None,
    dry_run: bool = False,
) -> bool:
    if not instruction.strip():
        return False
    if dry_run:
        logger.info("[dry-run] image-role %s len=%d", role, len(instruction))
        return True
    row = (
        db.query(PromptImageRole)
        .filter(PromptImageRole.role == role, PromptImageRole.workflow.is_(None))
        .first()
    )
    default_name = DEFAULT_IMAGE_ROLES.get(role, (role, ""))[0]
    if not row:
        db.add(
            PromptImageRole(
                id=str(uuid.uuid4()),
                role=role,
                workflow=None,
                name=name or default_name,
                instruction=instruction.strip(),
                is_active=True,
                version=1,
                source="migration",
            )
        )
        return True
    if row.instruction.strip() == instruction.strip():
        return False
    row.instruction = instruction.strip()
    row.version = (row.version or 1) + 1
    row.source = "migration"
    return True


def _master_from_db(db: Session, workflow: str) -> str:
    tmpl = db.query(PromptMasterTemplate).filter(PromptMasterTemplate.workflow == workflow).first()
    if not tmpl or not tmpl.active_version_id:
        return ""
    ver = db.query(PromptMasterVersion).filter(PromptMasterVersion.id == tmpl.active_version_id).first()
    return _display_master_text(ver)


def _master_from_dir(directory: Path, workflow: str) -> str:
    path = directory / f"{workflow}_master.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def _frag_from_dir(directory: Path, stem: str) -> str:
    path = directory / f"{stem}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def build_catalog_profiles(db: Session, directory: Path | None) -> tuple[dict[str, str], dict[str, str], list[str]]:
    master = _master_from_db(db, "CATALOG_IMAGE")
    if not master and directory:
        master = _master_from_dir(directory, "CATALOG_IMAGE")

    def frag(key: str, file_stem: str | None = None) -> str:
        text = _fragment_text(db, key)
        if not text and directory and file_stem:
            text = _frag_from_dir(directory, file_stem)
        return text

    fidelity = frag("RAW_JEWELRY_FIDELITY_LOCK", "RAW_JEWELRY_FIDELITY_LOCK")
    exec_modern = frag("EXEC_MODERN_CATALOG", "EXEC_MODERN_CATALOG")
    exec_ref = frag("EXEC_REFERENCE_MIRROR", "EXEC_REFERENCE_MIRROR")
    brand_no = frag("BRAND_CATALOG_NO_LOGO", "BRAND_NOREF_NOLOGO")
    brand_ref = frag("BRAND_REF_NO_LOGO", "BRAND_REF_NOLOGO")

    without = _merge_sections(fidelity, master, exec_modern, brand_no)
    with_ref = _merge_sections(fidelity, master, exec_ref, brand_ref)
    if "REFERENCE_USE" not in with_ref and exec_ref:
        with_ref.setdefault("REFERENCE_USE", "Use the style/environment reference image for background and lighting only.")

    pool = _fragment_pool(db)
    if not pool and directory:
        env_path = directory / "ENVIRONMENT_POOL.txt"
        if env_path.exists():
            pool = [ln.strip() for ln in env_path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    return without, with_ref, pool


def build_workflow_profiles(
    db: Session,
    workflow: str,
    directory: Path | None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Generic: master text → both pages; inject workflow-specific fragments."""
    master = _master_from_db(db, workflow)
    if not master and directory:
        master = _master_from_dir(directory, workflow)

    fidelity = _fragment_text(db, "RAW_JEWELRY_FIDELITY_LOCK")
    if not fidelity and directory:
        fidelity = _frag_from_dir(directory, "RAW_JEWELRY_FIDELITY_LOCK")

    without = _merge_sections(fidelity, master)
    with_ref = dict(without)

    if workflow == "BACKGROUND_REPLACEMENT":
        bg_gen = _fragment_text(db, "BACKGROUND_SOURCE_GENERATED")
        bg_ref = _fragment_text(db, "BACKGROUND_SOURCE_REF")
        if bg_gen:
            without["BACKGROUND_SOURCE"] = bg_gen.replace("{{CHOSEN_ENVIRONMENT}}", "").strip() or bg_gen
        if bg_ref:
            with_ref["BACKGROUND_SOURCE"] = bg_ref
            with_ref["REFERENCE_USE"] = bg_ref

    if workflow == "CUSTOM_PROMPT":
        preserve = _fragment_text(db, "CUSTOM_PRESERVE")
        realism = _fragment_text(db, "CUSTOM_REALISM")
        if preserve:
            without["PRESERVE"] = preserve
            with_ref["PRESERVE"] = preserve
        if realism:
            without["REALISM"] = realism
            with_ref["REALISM"] = realism

    if workflow == "VIRTUAL_TRY_ON":
        tryon = _fragment_text(db, "TRYON_CUSTOMER_PRESERVE")
        if tryon:
            with_ref["CUSTOMER_PRESERVE"] = tryon
        with_ref.setdefault(
            "PORTRAIT_USE",
            "Use the portrait image for the person. Preserve identity. Place jewelry on correct anatomy.",
        )

    if workflow == "REFERENCE_STYLE_MATCH":
        style = _fragment_text(db, "EXEC_STYLE_MOOD")
        if style:
            with_ref = _merge_sections(fidelity, master, style)
        without = {}  # N/A — requires reference

    return without, with_ref


def migrate_image_roles(db: Session, directory: Path | None, *, dry_run: bool) -> int:
    mapping = {
        "product": ("ATTACH_PRIMARY_SUBJECT", "ATTACH_PRIMARY_SUBJECT"),
        "theme": ("ATTACH_ENVIRONMENT_REFERENCE", "ATTACH_ENVIRONMENT_REFERENCE"),
        "logo": ("ATTACH_LOGO", "ATTACH_LOGO"),
        "portrait": ("ATTACH_TRY_ON", "ATTACH_TRYON_PERSON"),
    }
    count = 0
    for role, (key, stem) in mapping.items():
        text = _fragment_text(db, key)
        if not text and directory:
            text = _frag_from_dir(directory, stem)
        if not text:
            text = DEFAULT_IMAGE_ROLES[role][1]
        # Normalize Image N → Image {index}
        text = re.sub(r"Image\s+\d+", "Image {index}", text, flags=re.I)
        if _upsert_image_role(db, role, text, dry_run=dry_run):
            count += 1
    return count


def migrate_jewelry(db: Session, directory: Path | None, *, dry_run: bool) -> int:
    count = 0
    # Prefer CATALOG_IMAGE subjects; copy to all canonical workflows
    subjects = (
        db.query(PromptSubject)
        .filter(PromptSubject.workflow == "CATALOG_IMAGE")
        .all()
    )
    by_type: dict[str, str] = {}
    for subj in subjects:
        ver = None
        if subj.active_version_id:
            ver = (
                db.query(PromptSubjectVersion)
                .filter(PromptSubjectVersion.id == subj.active_version_id)
                .first()
            )
        text = ""
        if ver:
            text = (ver.prompt_text or "").strip()
            if not text and ver.layers:
                text = (assemble_raw_text_from_layers(sort_layers(ver.layers)) or "").strip()
        if text:
            by_type[subj.jewelry_type] = text

    if directory:
        for stem, jt in SUBJECT_STEM_MAP.items():
            if jt in by_type:
                continue
            path = directory / f"{stem}.txt"
            if path.exists():
                by_type[jt] = path.read_text(encoding="utf-8").strip()

    for jt in JEWELRY_TYPES:
        text = by_type.get(jt, "")
        if not text:
            continue
        content = parse_header_text(text) or {"SUBJECT": text}
        for workflow in CANONICAL_WORKFLOWS:
            if _upsert_jewelry(db, workflow, jt, content, dry_run=dry_run):
                count += 1
    return count


def run_migration(db: Session, directory: Path | None, *, dry_run: bool) -> dict:
    stats = {"profiles": 0, "jewelry": 0, "image_roles": 0}

    # Catalog (special handling with exec fragments)
    without, with_ref, pool = build_catalog_profiles(db, directory)
    if _upsert_profile(db, "CATALOG_IMAGE", REF_WITHOUT, without, environment_pool=pool or None, dry_run=dry_run):
        stats["profiles"] += 1
    if _upsert_profile(db, "CATALOG_IMAGE", REF_WITH, with_ref, dry_run=dry_run):
        stats["profiles"] += 1
    # BULK shares catalog
    if _upsert_profile(db, "BULK_GENERATION", REF_WITHOUT, without, environment_pool=pool or None, dry_run=dry_run):
        stats["profiles"] += 1
    if _upsert_profile(db, "BULK_GENERATION", REF_WITH, with_ref, dry_run=dry_run):
        stats["profiles"] += 1

    for workflow in CANONICAL_WORKFLOWS:
        if workflow == "CATALOG_IMAGE":
            continue
        w_without, w_with = build_workflow_profiles(db, workflow, directory)
        if w_without and _upsert_profile(db, workflow, REF_WITHOUT, w_without, dry_run=dry_run):
            stats["profiles"] += 1
        if w_with and _upsert_profile(db, workflow, REF_WITH, w_with, dry_run=dry_run):
            stats["profiles"] += 1

    # Legacy aliases that have their own masters
    for workflow in ("REFERENCE_STYLE_MATCH", "JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"):
        w_without, w_with = build_workflow_profiles(db, workflow, directory)
        if w_with and _upsert_profile(db, workflow, REF_WITH, w_with, dry_run=dry_run):
            stats["profiles"] += 1
        if w_without and _upsert_profile(db, workflow, REF_WITHOUT, w_without, dry_run=dry_run):
            stats["profiles"] += 1

    stats["jewelry"] = migrate_jewelry(db, directory, dry_run=dry_run)
    stats["image_roles"] = migrate_image_roles(db, directory, dry_run=dry_run)

    if not dry_run:
        db.commit()
    return stats


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Migrate prompts to Profile V2")
    parser.add_argument("--dir", type=str, default=None, help="Optional Prompts_Store/txt path")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    directory = Path(args.dir) if args.dir else None
    if directory and directory.name != "txt" and (directory / "txt").is_dir():
        directory = directory / "txt"
    if directory and not directory.is_dir():
        raise SystemExit(f"Directory not found: {directory}")

    db = SessionLocal()
    try:
        stats = run_migration(db, directory, dry_run=args.dry_run)
        print(json.dumps({"ok": True, "dry_run": args.dry_run, **stats}, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
