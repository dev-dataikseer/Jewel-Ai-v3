"""Export active production prompt data from Postgres into Prompts_Store/.

Usage (production):
  cd backend
  $env:DATABASE_URL = (railway variables --service Postgres --kv | Select-String '^DATABASE_PUBLIC_URL=').Line.Split('=',2)[1]
  $env:PYTHONPATH = '.'
  python scripts/export_prompts_store.py

Writes:
  Prompts_Store/manifest.json
  Prompts_Store/txt/*.txt          — mirror of docs/Modals/Prompts for re-import
  Prompts_Store/json/*.json        — full metadata + version history
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    PromptFragment,
    PromptFragmentVersion,
    PromptMasterTemplate,
    PromptMasterVersion,
    PromptSubject,
    PromptSubjectVersion,
    PromptVariant,
    PromptVariantVersion,
    PromptWorkflowLayerConfig,
    StylePreset,
)
from app.pipeline.layer_derive import assemble_raw_text_from_layers
from app.pipeline.layers import sort_layers
from seeds.import_prompts_folder import (
    FRAGMENT_FILE_MAP,
    MASTER_FILE_MAP,
    SUBJECT_FILE_MAP,
    SUBJECT_WORKFLOWS,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = _REPO_ROOT / "Prompts_Store"

# fragment_key -> file stem (inverse of FRAGMENT_FILE_MAP)
_KEY_TO_FILE: dict[str, str] = {v: k for k, v in FRAGMENT_FILE_MAP.items()}
_WORKFLOW_TO_MASTER_STEM: dict[str, str] = {v: k for k, v in MASTER_FILE_MAP.items()}
_JEWELRY_TO_SUBJECT_STEM: dict[str, str] = {v: k for k, v in SUBJECT_FILE_MAP.items()}


def _iso(dt) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).isoformat()
    return dt.isoformat()


def _display_text(ver, layers: list[dict] | None) -> str:
    if ver and getattr(ver, "prompt_text", None):
        return (ver.prompt_text or "").strip()
    if layers:
        return (assemble_raw_text_from_layers(layers) or "").strip()
    return ""


def _fragment_txt(key: str, ver: PromptFragmentVersion | None) -> str:
    if not ver:
        return ""
    if key == "ENVIRONMENT_POOL":
        pool = ver.content_json
        if isinstance(pool, list):
            return "\n".join(str(x).strip() for x in pool if str(x).strip())
        if ver.prompt_text:
            try:
                parsed = json.loads(ver.prompt_text)
                if isinstance(parsed, list):
                    return "\n".join(str(x).strip() for x in parsed if str(x).strip())
            except json.JSONDecodeError:
                pass
        return (ver.prompt_text or "").strip()
    if key == "TRYON_PLACEMENT_ANATOMY":
        mapping = ver.content_json
        if isinstance(mapping, dict):
            return "\n".join(f"{k} | {v}" for k, v in mapping.items())
        return (ver.prompt_text or "").strip()
    return (ver.prompt_text or "").strip()


def _serialize_version(ver, *, include_layers: bool = True) -> dict[str, Any]:
    layers = sort_layers(ver.layers) if getattr(ver, "layers", None) else []
    row: dict[str, Any] = {
        "id": ver.id,
        "version": ver.version,
        "is_active": ver.is_active,
        "source": getattr(ver, "source", None),
        "created_at": _iso(ver.created_at),
        "prompt_text": _display_text(ver, layers),
        "composition_mode": getattr(ver, "composition_mode", None),
    }
    if include_layers:
        row["layers"] = layers
    if hasattr(ver, "negative_addon"):
        row["negative_addon"] = ver.negative_addon
    if hasattr(ver, "content_json"):
        row["content_json"] = ver.content_json
    return row


def _active_version(db: Session, model, active_id: str | None):
    if not active_id:
        return None
    return db.query(model).filter(model.id == active_id).first()


def export_prompts_store(db: Session, out_dir: Path) -> dict[str, Any]:
    txt_dir = out_dir / "txt"
    json_dir = out_dir / "json"
    txt_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    stats: dict[str, int] = {
        "fragments": 0,
        "masters": 0,
        "subjects": 0,
        "variants": 0,
        "style_presets": 0,
        "layer_configs": 0,
        "txt_files": 0,
    }

    # --- Fragments ---
    fragments_json: list[dict[str, Any]] = []
    extra_txt: list[str] = []
    for frag in db.query(PromptFragment).order_by(PromptFragment.fragment_key.asc()).all():
        active = _active_version(db, PromptFragmentVersion, frag.active_version_id)
        versions = (
            db.query(PromptFragmentVersion)
            .filter(PromptFragmentVersion.fragment_id == frag.id)
            .order_by(PromptFragmentVersion.version.desc())
            .all()
        )
        fragments_json.append(
            {
                "id": frag.id,
                "fragment_key": frag.fragment_key,
                "name": frag.name,
                "description": frag.description,
                "is_active": frag.is_active,
                "active_version_id": frag.active_version_id,
                "active": _serialize_version(active, include_layers=False) if active else None,
                "versions": [_serialize_version(v, include_layers=False) for v in versions],
            }
        )
        stats["fragments"] += 1

        stem = _KEY_TO_FILE.get(frag.fragment_key)
        text = _fragment_txt(frag.fragment_key, active)
        if stem:
            (txt_dir / f"{stem}.txt").write_text(text + ("\n" if text else ""), encoding="utf-8")
            stats["txt_files"] += 1
        elif text:
            extra_txt.append(frag.fragment_key)
            (txt_dir / f"{frag.fragment_key}.txt").write_text(text + "\n", encoding="utf-8")
            stats["txt_files"] += 1

    (json_dir / "fragments.json").write_text(json.dumps(fragments_json, indent=2), encoding="utf-8")

    # --- Masters ---
    masters_json: list[dict[str, Any]] = []
    for tmpl in db.query(PromptMasterTemplate).order_by(PromptMasterTemplate.workflow.asc()).all():
        active = _active_version(db, PromptMasterVersion, tmpl.active_version_id)
        versions = (
            db.query(PromptMasterVersion)
            .filter(PromptMasterVersion.template_id == tmpl.id)
            .order_by(PromptMasterVersion.version.desc())
            .all()
        )
        masters_json.append(
            {
                "id": tmpl.id,
                "workflow": tmpl.workflow,
                "name": tmpl.name,
                "is_active": tmpl.is_active,
                "active_version_id": tmpl.active_version_id,
                "active": _serialize_version(active) if active else None,
                "versions": [_serialize_version(v) for v in versions],
            }
        )
        stats["masters"] += 1
        stem = _WORKFLOW_TO_MASTER_STEM.get(tmpl.workflow) or f"{tmpl.workflow}_master"
        if active:
            text = _display_text(active, sort_layers(active.layers) if active.layers else [])
            (txt_dir / f"{stem}.txt").write_text(text + ("\n" if text else ""), encoding="utf-8")
            stats["txt_files"] += 1

    (json_dir / "masters.json").write_text(json.dumps(masters_json, indent=2), encoding="utf-8")

    # --- Subjects ---
    subjects_json: list[dict[str, Any]] = []
    subject_by_jewelry: dict[str, dict[str, str]] = {}
    for subj in db.query(PromptSubject).order_by(
        PromptSubject.jewelry_type.asc(), PromptSubject.workflow.asc()
    ).all():
        active = _active_version(db, PromptSubjectVersion, subj.active_version_id)
        versions = (
            db.query(PromptSubjectVersion)
            .filter(PromptSubjectVersion.subject_id == subj.id)
            .order_by(PromptSubjectVersion.version.desc())
            .all()
        )
        text = _display_text(active, sort_layers(active.layers) if active and active.layers else [])
        subjects_json.append(
            {
                "id": subj.id,
                "workflow": subj.workflow,
                "jewelry_type": subj.jewelry_type,
                "is_active": subj.is_active,
                "active_version_id": subj.active_version_id,
                "active": _serialize_version(active) if active else None,
                "versions": [_serialize_version(v) for v in versions],
            }
        )
        stats["subjects"] += 1
        subject_by_jewelry.setdefault(subj.jewelry_type, {})[subj.workflow] = text

    (json_dir / "subjects.json").write_text(json.dumps(subjects_json, indent=2), encoding="utf-8")

    # Canonical subject .txt files: prefer CATALOG_IMAGE, else first workflow alphabetically
    for jewelry_type, by_workflow in subject_by_jewelry.items():
        stem = _JEWELRY_TO_SUBJECT_STEM.get(jewelry_type)
        if not stem:
            continue
        canonical = by_workflow.get("CATALOG_IMAGE")
        if canonical is None and by_workflow:
            canonical = by_workflow[sorted(by_workflow.keys())[0]]
        if canonical is not None:
            (txt_dir / f"{stem}.txt").write_text(canonical + ("\n" if canonical else ""), encoding="utf-8")
            stats["txt_files"] += 1

    # Per-workflow subject snapshots when text differs across workflows
    workflow_subject_dir = json_dir / "subjects_by_workflow"
    workflow_subject_dir.mkdir(exist_ok=True)
    for workflow in SUBJECT_WORKFLOWS:
        wf_rows = [s for s in subjects_json if s["workflow"] == workflow and s.get("active")]
        if not wf_rows:
            continue
        (workflow_subject_dir / f"{workflow}.json").write_text(
            json.dumps(wf_rows, indent=2), encoding="utf-8"
        )

    # --- Variants ---
    variants_json: list[dict[str, Any]] = []
    for var in db.query(PromptVariant).order_by(
        PromptVariant.workflow.asc(), PromptVariant.sort_order.asc(), PromptVariant.variant_key.asc()
    ).all():
        active = _active_version(db, PromptVariantVersion, var.active_version_id)
        versions = (
            db.query(PromptVariantVersion)
            .filter(PromptVariantVersion.variant_id == var.id)
            .order_by(PromptVariantVersion.version.desc())
            .all()
        )
        variants_json.append(
            {
                "id": var.id,
                "workflow": var.workflow,
                "variant_key": var.variant_key,
                "label": var.label,
                "sort_order": var.sort_order,
                "is_active": var.is_active,
                "active_version_id": var.active_version_id,
                "active": _serialize_version(active, include_layers=False) if active else None,
                "versions": [_serialize_version(v, include_layers=False) for v in versions],
            }
        )
        stats["variants"] += 1

    (json_dir / "variants.json").write_text(json.dumps(variants_json, indent=2), encoding="utf-8")

    # Variants grouped by workflow for readability
    variants_by_workflow: dict[str, list[dict[str, Any]]] = {}
    for row in variants_json:
        variants_by_workflow.setdefault(row["workflow"], []).append(row)
    for workflow, rows in variants_by_workflow.items():
        (json_dir / f"variants_{workflow}.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    # --- Style presets ---
    presets = db.query(StylePreset).order_by(StylePreset.workflow.asc(), StylePreset.name.asc()).all()
    presets_json = [
        {
            "id": p.id,
            "name": p.name,
            "workflow": p.workflow,
            "description": p.description,
            "prompt_addon": p.prompt_addon,
            "thumbnail_url": p.thumbnail_url,
            "is_active": p.is_active,
            "created_at": _iso(p.created_at),
            "updated_at": _iso(p.updated_at),
        }
        for p in presets
    ]
    (json_dir / "style_presets.json").write_text(json.dumps(presets_json, indent=2), encoding="utf-8")
    stats["style_presets"] = len(presets_json)

    # --- Layer configs ---
    layer_rows = db.query(PromptWorkflowLayerConfig).order_by(PromptWorkflowLayerConfig.workflow.asc()).all()
    layer_configs = [
        {
            "id": row.id,
            "workflow": row.workflow,
            "structural_layers": row.structural_layers,
            "updated_at": _iso(row.updated_at),
        }
        for row in layer_rows
    ]
    (json_dir / "layer_configs.json").write_text(json.dumps(layer_configs, indent=2), encoding="utf-8")
    stats["layer_configs"] = len(layer_configs)

    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source": "production_database",
        "output_dir": str(out_dir),
        "stats": stats,
        "extra_fragment_txt_files": extra_txt,
        "notes": {
            "txt_layout": "Mirrors docs/Modals/Prompts/*.txt for re-import via seeds.import_prompts_folder",
            "subjects_txt": "One file per jewelry type from CATALOG_IMAGE workflow (see json/subjects_by_workflow if divergent)",
            "variants": "JSON only — not represented as flat .txt in repo seed layout",
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Export DB prompts to Prompts_Store/")
    parser.add_argument("--out", type=str, default=str(DEFAULT_OUT), help="Output directory")
    args = parser.parse_args()
    out_dir = Path(args.out)
    db = SessionLocal()
    try:
        manifest = export_prompts_store(db, out_dir)
        print(f"Exported to {out_dir}")
        print(json.dumps(manifest["stats"], indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
