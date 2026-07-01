"""Export SQLite MVP data for import into the Jewel V3 PostgreSQL API."""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQLITE_PATH = ROOT.parent / "Old Project" / "backend" / "prisma" / "dev.db"
OUT_PATH = ROOT / "api" / "seeds" / "sqlite_export.json"


def export_sqlite(path: Path = SQLITE_PATH) -> dict:
    if not path.exists():
        return {"error": f"SQLite DB not found at {path}"}
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    tables = [
        "PromptTemplate",
        "SubjectPrompt",
        "PromptVariant",
        "StylePreset",
        "RateEntry",
        "ProviderSetting",
    ]
    data = {}
    for table in tables:
        try:
            rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
            data[table] = [dict(r) for r in rows]
        except sqlite3.OperationalError:
            data[table] = []
    conn.close()
    return data


if __name__ == "__main__":
    out = export_sqlite()
    OUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"Exported to {OUT_PATH}")
