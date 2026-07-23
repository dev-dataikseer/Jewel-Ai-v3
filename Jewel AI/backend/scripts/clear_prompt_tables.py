"""Clear prompt authoring tables only — keep jobs, assets, users, etc.

Usage (Railway public DB URL):
  set DATABASE_URL=...python...
  python backend/scripts/clear_prompt_tables.py
"""

from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text

# Prompt authoring only — never touch generation_jobs, assets, users, etc.
PROMPT_TABLES_DELETE_ORDER = [
    "prompt_profile_versions",
    "prompt_profiles",
    "prompt_jewelry_section_versions",
    "prompt_jewelry_sections",
    "prompt_image_roles",
    "prompt_fragment_versions",
    "prompt_fragments",
    "prompt_variant_versions",
    "prompt_variants",
    "prompt_subject_versions",
    "prompt_subjects",
    "prompt_master_versions",
    "prompt_master_templates",
    "prompt_workflow_layer_configs",
    "style_presets",
]


def main() -> int:
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        print("DATABASE_URL required", file=sys.stderr)
        return 1
    if "confirm" not in sys.argv:
        print(
            "Refusing to run without 'confirm' arg.\n"
            "Example: python clear_prompt_tables.py confirm",
            file=sys.stderr,
        )
        return 2

    engine = create_engine(url)
    counts_before: dict[str, int] = {}
    with engine.begin() as conn:
        for table in PROMPT_TABLES_DELETE_ORDER:
            try:
                counts_before[table] = int(conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0)
            except Exception:
                counts_before[table] = -1  # missing table

        # Detach style preset FKs from non-prompt tables (do not delete those rows).
        for stmt in (
            "UPDATE generation_jobs SET style_preset_id = NULL WHERE style_preset_id IS NOT NULL",
            "UPDATE batches SET preset_id = NULL WHERE preset_id IS NOT NULL",
            "UPDATE projects SET preset_id = NULL WHERE preset_id IS NOT NULL",
            "UPDATE prompt_profiles SET active_version_id = NULL",
            "UPDATE prompt_jewelry_sections SET active_version_id = NULL",
            "UPDATE prompt_fragments SET active_version_id = NULL",
            "UPDATE prompt_master_templates SET active_version_id = NULL",
            "UPDATE prompt_subjects SET active_version_id = NULL",
            "UPDATE prompt_variants SET active_version_id = NULL",
        ):
            try:
                conn.execute(text(stmt))
            except Exception as exc:
                print(f"skip: {stmt[:48]}... ({exc})")

        for table in PROMPT_TABLES_DELETE_ORDER:
            if counts_before.get(table, -1) < 0:
                print(f"skip missing table: {table}")
                continue
            result = conn.execute(text(f"DELETE FROM {table}"))
            print(f"cleared {table}: {counts_before[table]} -> 0 (deleted={result.rowcount})")

        # Sanity: jobs/assets untouched
        jobs = conn.execute(text("SELECT COUNT(*) FROM generation_jobs")).scalar()
        assets = conn.execute(text("SELECT COUNT(*) FROM assets")).scalar()
        users = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
        print(f"preserved generation_jobs={jobs} assets={assets} users={users}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
