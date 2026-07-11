"""Add batches.user_id and assets.user_id index for tenancy.

Revision ID: 003_batch_user
Revises: 002_tenancy
"""

from alembic import op
import sqlalchemy as sa

revision = "003_batch_user"
down_revision = "002_tenancy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if inspector.has_table("batches"):
        cols = {c["name"] for c in inspector.get_columns("batches")}
        if "user_id" not in cols:
            op.add_column("batches", sa.Column("user_id", sa.String(36), nullable=True))
        indexes = {i["name"] for i in inspector.get_indexes("batches")}
        if "ix_batches_user_id" not in indexes:
            op.create_index("ix_batches_user_id", "batches", ["user_id"])
    if inspector.has_table("assets"):
        indexes = {i["name"] for i in inspector.get_indexes("assets")}
        if "ix_assets_user_id" not in indexes:
            op.create_index("ix_assets_user_id", "assets", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_assets_user_id", table_name="assets")
    op.drop_index("ix_batches_user_id", table_name="batches")
    op.drop_column("batches", "user_id")
