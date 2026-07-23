"""Initial schema baseline from current SQLAlchemy models.

Revision ID: 001_initial
Revises:
Create Date: 2026-07-02

Production uses SCHEMA_VIA_ALEMBIC=true and runs `alembic upgrade head`
(no SQLAlchemy create_all). This revision creates the full table set.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent baseline: create any missing tables from ORM metadata.
    # Safe on fresh DBs and on DBs previously bootstrapped via create_all.
    bind = op.get_bind()
    from app.database import Base
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    from app.database import Base
    import app.models  # noqa: F401

    Base.metadata.drop_all(bind=bind)
