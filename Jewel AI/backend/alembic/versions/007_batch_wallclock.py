"""Batch wall-clock columns: started_at, completed_at.

Revision ID: 007_batch_wallclock
Revises: 006_audit_mfa
"""

from alembic import op
import sqlalchemy as sa

revision = "007_batch_wallclock"
down_revision = "006_audit_mfa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if not inspector.has_table("batches"):
        return
    cols = {c["name"] for c in inspector.get_columns("batches")}
    if "started_at" not in cols:
        op.add_column(
            "batches",
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "completed_at" not in cols:
        op.add_column(
            "batches",
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if not inspector.has_table("batches"):
        return
    cols = {c["name"] for c in inspector.get_columns("batches")}
    if "completed_at" in cols:
        op.drop_column("batches", "completed_at")
    if "started_at" in cols:
        op.drop_column("batches", "started_at")
