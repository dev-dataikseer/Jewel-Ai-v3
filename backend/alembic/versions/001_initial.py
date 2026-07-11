"""Initial schema placeholder — tables created via SQLAlchemy metadata at startup.

Revision ID: 001_initial
Revises:
Create Date: 2026-07-02

Full schema is created via SQLAlchemy metadata + additive migrators in
`app.pipeline.db_migrate` on startup. Subsequent revisions (002+) apply
incremental changes.
"""

from typing import Sequence, Union

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Intentionally empty — baseline tables come from create_all / ORM.
    pass


def downgrade() -> None:
    pass
