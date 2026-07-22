"""ARCHIVED — CLI for one-time prompt TXT migration.

Prefer Admin → Prompts → Tools → Import from files, or seeds.import_prompts_folder.
"""

from __future__ import annotations

import argparse

from app.database import SessionLocal
from seeds.prompt_txt_import import import_prompt_txt_library


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import data/seed-prompt-templates/*.txt into the database (one-time migration)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Import even if prompt versions already exist (overwrites via new versions)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = import_prompt_txt_library(db, force=args.force)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
