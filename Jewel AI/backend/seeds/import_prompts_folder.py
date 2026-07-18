"""Import prompt text from docs/Modals/Prompts/*.txt into DB.

Source of truth for seed content: Jewel AI/docs/Modals/Prompts/
Admin UI edits create new DB versions after import.

Usage:
  python -m seeds.import_prompts_folder
  python -m seeds.import_prompts_folder --force
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    PromptFragment,
    PromptFragmentVersion,
    PromptMasterTemplate,
    PromptMasterVersion,
    PromptSubject,
    PromptSubjectVersion,
)
from app.pipeline.layer_derive import derive_layers_from_raw_text, default_structural_config
from app.pipeline.layers import sort_layers
from app.prompt_engine.fragment_defaults import FRAGMENT_LABELS

logger = logging.getLogger(__name__)

# Resolve: backend/seeds → backend → Jewel AI → docs/Modals/Prompts
_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "docs" / "Modals" / "Prompts"

# File stem → fragment_key (runtime keys used by assembler)
FRAGMENT_FILE_MAP: dict[str, str] = {
    "RAW_JEWELRY_FIDELITY_LOCK": "RAW_JEWELRY_FIDELITY_LOCK",
    "EXEC_REFERENCE_MIRROR": "EXEC_REFERENCE_MIRROR",
    "EXEC_MODERN_CATALOG": "EXEC_MODERN_CATALOG",
    "EXEC_STYLE_MOOD": "EXEC_STYLE_MOOD",
    "BRAND_REF_LOGO": "BRAND_REF_WITH_LOGO",
    "BRAND_REF_NOLOGO": "BRAND_REF_NO_LOGO",
    "BRAND_NOREF_LOGO": "BRAND_CATALOG_WITH_LOGO",
    "BRAND_NOREF_NOLOGO": "BRAND_CATALOG_NO_LOGO",
    "ATTACH_PRIMARY_SUBJECT": "ATTACH_PRIMARY_SUBJECT",
    "ATTACH_ENVIRONMENT_REFERENCE": "ATTACH_ENVIRONMENT_REFERENCE",
    "ATTACH_LOGO": "ATTACH_LOGO",
    "ATTACH_TRYON_PERSON": "ATTACH_TRY_ON",
    "BACKGROUND_SOURCE_REF": "BACKGROUND_SOURCE_REF",
    "BACKGROUND_SOURCE_GENERATED": "BACKGROUND_SOURCE_GENERATED",
    "CUSTOM_PRESERVE": "CUSTOM_PRESERVE",
    "CUSTOM_REALISM": "CUSTOM_REALISM",
    "CUSTOM_ALTER_GUARD": "CUSTOM_ALTER_GUARD",
    "TRYON_CUSTOMER_PRESERVE": "TRYON_CUSTOMER_PRESERVE",
    "TRYON_PLACEMENT_ANATOMY": "TRYON_PLACEMENT_ANATOMY",
    "MULTI_ITEM_FRAME": "MULTI_ITEM_FRAME",
    "USER_ADDITION_WRAP": "USER_ADDITION_WRAP",
    "ENVIRONMENT_POOL": "ENVIRONMENT_POOL",
}

FRAGMENT_EXTRA_LABELS: dict[str, str] = {
    "ATTACH_PRIMARY_SUBJECT": "Attachment — Primary Subject (Image 1)",
    "ATTACH_ENVIRONMENT_REFERENCE": "Attachment — Environment Reference (Image 2)",
    "CUSTOM_ALTER_GUARD": "Custom Prompt — Alter Guard Patterns (not sent to model)",
    "TRYON_PLACEMENT_ANATOMY": "Try-On — Placement Anatomy Lookup",
}

MASTER_FILE_MAP: dict[str, str] = {
    "CATALOG_IMAGE_master": "CATALOG_IMAGE",
    "VIRTUAL_TRY_ON_master": "VIRTUAL_TRY_ON",
    "GEMSTONE_COLOR_CHANGE_master": "GEMSTONE_COLOR_CHANGE",
    "BACKGROUND_REPLACEMENT_master": "BACKGROUND_REPLACEMENT",
    "LUXURY_ENHANCEMENT_master": "LUXURY_ENHANCEMENT",
    "CUSTOM_PROMPT_master": "CUSTOM_PROMPT",
}

SUBJECT_FILE_MAP: dict[str, str] = {
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

# Subject text is shared across these workflows at import time
SUBJECT_WORKFLOWS = [
    "CATALOG_IMAGE",
    "VIRTUAL_TRY_ON",
    "GEMSTONE_COLOR_CHANGE",
    "BACKGROUND_REPLACEMENT",
    "LUXURY_ENHANCEMENT",
    "CUSTOM_PROMPT",
]


def prompts_dir() -> Path:
    return _PROMPTS_DIR


def _read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _upsert_fragment(
    db: Session,
    key: str,
    text: str,
    *,
    name: str | None = None,
    content_json: list | dict | None = None,
    force: bool = False,
) -> bool:
    """Create or bump fragment version. Returns True if a new version was written."""
    frag = db.query(PromptFragment).filter(PromptFragment.fragment_key == key).first()
    label = name or FRAGMENT_LABELS.get(key) or FRAGMENT_EXTRA_LABELS.get(key) or key

    if not frag:
        frag = PromptFragment(fragment_key=key, name=label, is_active=True)
        db.add(frag)
        db.flush()
    else:
        frag.name = label
        if not force and frag.active_version_id:
            ver = (
                db.query(PromptFragmentVersion)
                .filter(PromptFragmentVersion.id == frag.active_version_id)
                .first()
            )
            if ver and (ver.prompt_text or "").strip() == text.strip():
                return False

    last = (
        db.query(PromptFragmentVersion)
        .filter(PromptFragmentVersion.fragment_id == frag.id)
        .order_by(PromptFragmentVersion.version.desc())
        .first()
    )
    version_num = (last.version + 1) if last else 1
    if last and not force and (last.prompt_text or "").strip() == text.strip():
        if not frag.active_version_id:
            frag.active_version_id = last.id
        return False

    db.query(PromptFragmentVersion).filter(PromptFragmentVersion.fragment_id == frag.id).update(
        {"is_active": False}
    )
    ver = PromptFragmentVersion(
        fragment_id=frag.id,
        version=version_num,
        prompt_text=text,
        content_json=content_json,
        is_active=True,
        source="txt",
    )
    db.add(ver)
    db.flush()
    frag.active_version_id = ver.id
    return True


def _upsert_master(db: Session, workflow: str, text: str, *, force: bool = False) -> bool:
    tmpl = db.query(PromptMasterTemplate).filter(PromptMasterTemplate.workflow == workflow).first()
    if not tmpl:
        tmpl = PromptMasterTemplate(workflow=workflow, name=workflow.replace("_", " ").title(), is_active=True)
        db.add(tmpl)
        db.flush()

    if not force and tmpl.active_version_id:
        ver = (
            db.query(PromptMasterVersion)
            .filter(PromptMasterVersion.id == tmpl.active_version_id)
            .first()
        )
        if ver and (ver.prompt_text or "").strip() == text.strip():
            return False

    last = (
        db.query(PromptMasterVersion)
        .filter(PromptMasterVersion.template_id == tmpl.id)
        .order_by(PromptMasterVersion.version.desc())
        .first()
    )
    version_num = (last.version + 1) if last else 1
    structural = default_structural_config(workflow)
    layers = derive_layers_from_raw_text(text, workflow, scope="master", structural_config=structural)
    db.query(PromptMasterVersion).filter(PromptMasterVersion.template_id == tmpl.id).update(
        {"is_active": False}
    )
    ver = PromptMasterVersion(
        template_id=tmpl.id,
        version=version_num,
        prompt_text=text,
        composition_mode="layered",
        layers=sort_layers(layers),
        is_active=True,
        source="txt",
    )
    db.add(ver)
    db.flush()
    tmpl.active_version_id = ver.id
    return True


def _upsert_subject(
    db: Session,
    workflow: str,
    jewelry_type: str,
    text: str,
    *,
    force: bool = False,
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

    if not force and subj.active_version_id:
        ver = (
            db.query(PromptSubjectVersion)
            .filter(PromptSubjectVersion.id == subj.active_version_id)
            .first()
        )
        if ver and (ver.prompt_text or "").strip() == text.strip():
            return False

    last = (
        db.query(PromptSubjectVersion)
        .filter(PromptSubjectVersion.subject_id == subj.id)
        .order_by(PromptSubjectVersion.version.desc())
        .first()
    )
    version_num = (last.version + 1) if last else 1
    layers = derive_layers_from_raw_text(text, workflow, scope="subject", structural_config=[])
    db.query(PromptSubjectVersion).filter(PromptSubjectVersion.subject_id == subj.id).update(
        {"is_active": False}
    )
    ver = PromptSubjectVersion(
        subject_id=subj.id,
        version=version_num,
        prompt_text=text,
        composition_mode="layered",
        layers=sort_layers(layers) if layers else [{"key": "core", "type": "text", "content": text, "order": 1}],
        is_active=True,
        source="txt",
    )
    db.add(ver)
    db.flush()
    subj.active_version_id = ver.id
    return True


def _build_catalog_role_map(primary: str, theme: str, logo: str) -> str:
    """Compose ATTACH_CATALOG_ROLE_MAP template with optional theme/logo lines."""
    return (
        "ATTACHMENT ROLES & INSTRUCTIONS:\n"
        f"{primary.strip()}"
        "{{THEME_LINE}}"
        "{{LOGO_LINE}}"
    )


def import_prompts_folder(db: Session, *, force: bool = False, directory: Path | None = None) -> dict:
    """Import all .txt files. Returns counts of updated rows."""
    root = directory or prompts_dir()
    if not root.is_dir():
        raise FileNotFoundError(f"Prompts folder not found: {root}")

    stats = {"fragments": 0, "masters": 0, "subjects": 0, "skipped": 0, "dir": str(root)}

    # --- Fragments ---
    primary = theme = logo_attach = ""
    for stem, key in FRAGMENT_FILE_MAP.items():
        path = root / f"{stem}.txt"
        if not path.exists():
            logger.warning("Missing prompt file: %s", path.name)
            stats["skipped"] += 1
            continue
        raw = _read_txt(path)
        content_json = None
        text = raw

        if key == "ENVIRONMENT_POOL":
            lines = [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith("#")]
            content_json = lines
            text = json.dumps(lines, indent=2)
        elif key == "TRYON_PLACEMENT_ANATOMY":
            # Parse "type | clause" lines into JSON map
            mapping: dict[str, str] = {}
            for ln in raw.splitlines():
                ln = ln.strip()
                if not ln or ln.startswith("#"):
                    continue
                if "|" in ln:
                    k, v = ln.split("|", 1)
                    mapping[k.strip().lower()] = v.strip()
            content_json = mapping
            text = raw
        elif stem == "ATTACH_PRIMARY_SUBJECT":
            primary = raw
            continue
        elif stem == "ATTACH_ENVIRONMENT_REFERENCE":
            theme = raw
            continue
        elif stem == "ATTACH_LOGO" and key == "ATTACH_LOGO":
            logo_attach = raw
            # still upsert ATTACH_LOGO as standalone
            if _upsert_fragment(db, key, text, force=force):
                stats["fragments"] += 1
            continue

        if _upsert_fragment(db, key, text, content_json=content_json, force=force):
            stats["fragments"] += 1

    # Compose catalog role map from split attach files
    if primary:
        composed = _build_catalog_role_map(primary, theme, logo_attach)
        # Store theme/logo line templates as fragments too
        if theme:
            _upsert_fragment(
                db,
                "ATTACH_ENVIRONMENT_REFERENCE",
                theme,
                name=FRAGMENT_EXTRA_LABELS["ATTACH_ENVIRONMENT_REFERENCE"],
                force=force,
            )
            stats["fragments"] += 1
        _upsert_fragment(
            db,
            "ATTACH_PRIMARY_SUBJECT",
            primary,
            name=FRAGMENT_EXTRA_LABELS["ATTACH_PRIMARY_SUBJECT"],
            force=force,
        )
        if _upsert_fragment(
            db,
            "ATTACH_CATALOG_ROLE_MAP",
            composed,
            name="Attachment — Catalog Role Map",
            force=force,
        ):
            stats["fragments"] += 1

        # Theme/logo optional lines used by attachments.py
        if theme:
            _upsert_fragment(
                db,
                "ATTACH_THEME_LINE_TEMPLATE",
                f"\n{theme}",
                name="Attachment — Theme Line Template",
                force=True,
            )
        if logo_attach:
            _upsert_fragment(
                db,
                "ATTACH_LOGO_LINE_TEMPLATE",
                f"\n{logo_attach}",
                name="Attachment — Logo Line Template",
                force=True,
            )

    # --- Masters ---
    for stem, workflow in MASTER_FILE_MAP.items():
        path = root / f"{stem}.txt"
        if not path.exists():
            logger.warning("Missing master file: %s", path.name)
            stats["skipped"] += 1
            continue
        text = _read_txt(path)
        if _upsert_master(db, workflow, text, force=force):
            stats["masters"] += 1

    # --- Subjects (all jewelry types × canonical workflows) ---
    for stem, jewelry_type in SUBJECT_FILE_MAP.items():
        path = root / f"{stem}.txt"
        if not path.exists():
            logger.warning("Missing subject file: %s", path.name)
            stats["skipped"] += 1
            continue
        text = _read_txt(path)
        for workflow in SUBJECT_WORKFLOWS:
            if _upsert_subject(db, workflow, jewelry_type, text, force=force):
                stats["subjects"] += 1

    db.commit()
    return stats


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Import docs/Modals/Prompts into the database")
    parser.add_argument("--force", action="store_true", help="Always create new versions even if text matches")
    parser.add_argument("--dir", type=str, default=None, help="Override prompts directory")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        stats = import_prompts_folder(
            db,
            force=args.force,
            directory=Path(args.dir) if args.dir else None,
        )
        print(f"Imported from {stats['dir']}")
        print(
            f"  fragments={stats['fragments']} masters={stats['masters']} "
            f"subjects={stats['subjects']} skipped={stats['skipped']}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
