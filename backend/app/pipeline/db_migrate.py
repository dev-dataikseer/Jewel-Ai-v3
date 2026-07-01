"""Add v3 layer columns and workflow-specific subjects to existing SQLite/Postgres tables."""

from __future__ import annotations

import copy

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import PromptSubject, PromptSubjectVersion

LAYER_COLUMNS = [
    ("prompt_master_versions", "composition_mode", "VARCHAR(32) DEFAULT 'layered'"),
    ("prompt_master_versions", "layers", "JSON"),
    ("prompt_master_versions", "raw_override", "TEXT"),
    ("prompt_master_versions", "source", "VARCHAR(32) DEFAULT 'seed'"),
    ("prompt_subject_versions", "composition_mode", "VARCHAR(32) DEFAULT 'layered'"),
    ("prompt_subject_versions", "layers", "JSON"),
    ("prompt_subject_versions", "raw_override", "TEXT"),
    ("prompt_subject_versions", "source", "VARCHAR(32) DEFAULT 'seed'"),
    ("prompt_subject_versions", "prompt_text", "TEXT"),
    ("prompt_subjects", "workflow", "VARCHAR(64) DEFAULT 'CATALOG_IMAGE'"),
]

SUBJECT_WORKFLOWS = [
    "CATALOG_IMAGE",
    "JEWELRY_ON_MODEL",
    "GEMSTONE_COLOR_CHANGE",
    "CUSTOMER_TRY_ON",
    "REFERENCE_STYLE_MATCH",
    "BACKGROUND_REPLACEMENT",
    "LUXURY_ENHANCEMENT",
    "CUSTOM_PROMPT",
    "BULK_GENERATION",
]


def _add_column_if_missing(conn, inspector, table: str, column: str, col_type: str) -> None:
    if not inspector.has_table(table):
        return
    existing = {c["name"] for c in inspector.get_columns(table)}
    if column in existing:
        return
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))


def migrate_layer_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, column, col_type in LAYER_COLUMNS:
            _add_column_if_missing(conn, inspector, table, column, col_type)
        if not inspector.has_table("prompt_workflow_layer_configs"):
            dialect = engine.dialect.name
            if dialect == "sqlite":
                conn.execute(
                    text(
                        """
                        CREATE TABLE prompt_workflow_layer_configs (
                            id VARCHAR(36) NOT NULL PRIMARY KEY,
                            workflow VARCHAR(64) NOT NULL UNIQUE,
                            structural_layers JSON NOT NULL,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
                        )
                        """
                    )
                )
            else:
                conn.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS prompt_workflow_layer_configs (
                            id VARCHAR(36) PRIMARY KEY,
                            workflow VARCHAR(64) NOT NULL UNIQUE,
                            structural_layers JSON NOT NULL DEFAULT '[]',
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                        )
                        """
                    )
                )
        migrate_prompt_subjects_constraints(engine)


def migrate_job_indexes(engine: Engine) -> None:
    """Add indexes for common job list and stream queries."""
    inspector = inspect(engine)
    if not inspector.has_table("generation_jobs"):
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "sqlite":
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_user_id ON generation_jobs (user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_status ON generation_jobs (status)"))
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_jobs_user_created ON generation_jobs (user_id, created_at)")
            )
        elif dialect == "postgresql":
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_user_id ON generation_jobs (user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_status ON generation_jobs (status)"))
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_jobs_user_created ON generation_jobs (user_id, created_at DESC)")
            )


def _prompt_subjects_has_composite_unique(inspector) -> bool:
    if not inspector.has_table("prompt_subjects"):
        return False
    for uc in inspector.get_unique_constraints("prompt_subjects"):
        cols = set(uc.get("column_names") or [])
        if cols == {"workflow", "jewelry_type"}:
            return True
    return False


def migrate_prompt_subjects_constraints(engine: Engine) -> None:
    """Replace legacy UNIQUE(jewelry_type) with UNIQUE(workflow, jewelry_type)."""
    inspector = inspect(engine)
    if not inspector.has_table("prompt_subjects"):
        return
    if _prompt_subjects_has_composite_unique(inspector):
        return

    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "sqlite":
            conn.execute(
                text(
                    """
                    CREATE TABLE prompt_subjects_new (
                        id VARCHAR(36) NOT NULL PRIMARY KEY,
                        workflow VARCHAR(64) NOT NULL DEFAULT 'CATALOG_IMAGE',
                        jewelry_type VARCHAR(128) NOT NULL,
                        is_active BOOLEAN NOT NULL,
                        active_version_id VARCHAR(36),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        CONSTRAINT uq_subject_workflow_jewelry UNIQUE (workflow, jewelry_type)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    INSERT INTO prompt_subjects_new
                        (id, workflow, jewelry_type, is_active, active_version_id, created_at, updated_at)
                    SELECT
                        id,
                        COALESCE(workflow, 'CATALOG_IMAGE'),
                        jewelry_type,
                        is_active,
                        active_version_id,
                        created_at,
                        updated_at
                    FROM prompt_subjects
                    """
                )
            )
            conn.execute(text("DROP TABLE prompt_subjects"))
            conn.execute(text("ALTER TABLE prompt_subjects_new RENAME TO prompt_subjects"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_prompt_subjects_workflow ON prompt_subjects (workflow)"))
        elif dialect == "postgresql":
            conn.execute(text("UPDATE prompt_subjects SET workflow = 'CATALOG_IMAGE' WHERE workflow IS NULL"))
            for uc in inspector.get_unique_constraints("prompt_subjects"):
                cols = uc.get("column_names") or []
                name = uc.get("name")
                if cols == ["jewelry_type"] and name:
                    conn.execute(text(f'ALTER TABLE prompt_subjects DROP CONSTRAINT "{name}"'))
            conn.execute(
                text(
                    "ALTER TABLE prompt_subjects "
                    "ADD CONSTRAINT uq_subject_workflow_jewelry UNIQUE (workflow, jewelry_type)"
                )
            )
        else:
            # Generic fallback: ensure workflow populated; composite unique may require manual migration
            conn.execute(text("UPDATE prompt_subjects SET workflow = 'CATALOG_IMAGE' WHERE workflow IS NULL"))


def migrate_workflow_subjects(db: Session) -> None:
    """Backfill workflow column and duplicate shared subjects per workflow."""
    inspector = inspect(db.bind)
    if not inspector.has_table("prompt_subjects"):
        return

    columns = {c["name"] for c in inspector.get_columns("prompt_subjects")}
    if "workflow" not in columns:
        return

    subjects = db.query(PromptSubject).all()
    if not subjects:
        return

    # Assign workflow to legacy rows missing it
    for subj in subjects:
        if not getattr(subj, "workflow", None):
            subj.workflow = "CATALOG_IMAGE"
    db.flush()

    by_jt: dict[str, PromptSubject] = {}
    for subj in subjects:
        wf = subj.workflow or "CATALOG_IMAGE"
        key = f"{wf}:{subj.jewelry_type}"
        if key not in by_jt:
            by_jt[key] = subj

    for subj in list(subjects):
        if subj.workflow and subj.workflow != "CATALOG_IMAGE":
            continue
        active_ver = None
        if subj.active_version_id:
            active_ver = db.query(PromptSubjectVersion).filter(PromptSubjectVersion.id == subj.active_version_id).first()
        if not active_ver:
            active_ver = (
                db.query(PromptSubjectVersion)
                .filter(PromptSubjectVersion.subject_id == subj.id, PromptSubjectVersion.is_active == True)  # noqa: E712
                .order_by(PromptSubjectVersion.version.desc())
                .first()
            )
        for wf in SUBJECT_WORKFLOWS:
            if wf == "CATALOG_IMAGE":
                subj.workflow = wf
                continue
            key = f"{wf}:{subj.jewelry_type}"
            if key in by_jt:
                continue
            new_subj = PromptSubject(workflow=wf, jewelry_type=subj.jewelry_type, is_active=subj.is_active)
            db.add(new_subj)
            db.flush()
            if active_ver:
                new_ver = PromptSubjectVersion(
                    subject_id=new_subj.id,
                    version=1,
                    prompt_text=getattr(active_ver, "prompt_text", None),
                    core_description=active_ver.core_description,
                    anatomy_interaction=active_ver.anatomy_interaction,
                    physics_and_gravity=active_ver.physics_and_gravity,
                    placement_rules=active_ver.placement_rules,
                    composition_mode=active_ver.composition_mode or "layered",
                    layers=copy.deepcopy(active_ver.layers) if active_ver.layers else None,
                    raw_override=active_ver.raw_override,
                    is_active=True,
                    source=getattr(active_ver, "source", "seed") or "seed",
                )
                db.add(new_ver)
                db.flush()
                new_subj.active_version_id = new_ver.id
            by_jt[key] = new_subj
    db.commit()
