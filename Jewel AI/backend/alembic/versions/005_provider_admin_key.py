"""Add providers.encrypted_admin_api_key for fal Admin billing key.

Revision ID: 005_provider_admin_key
Revises: 004_celery_task_id
"""

from alembic import op
import sqlalchemy as sa

revision = "005_provider_admin_key"
down_revision = "004_celery_task_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if not inspector.has_table("providers"):
        return
    cols = {c["name"] for c in inspector.get_columns("providers")}
    if "encrypted_admin_api_key" in cols:
        return
    dialect = conn.dialect.name
    col_type = sa.LargeBinary() if dialect == "postgresql" else sa.LargeBinary()
    op.add_column("providers", sa.Column("encrypted_admin_api_key", col_type, nullable=True))


def downgrade() -> None:
    op.drop_column("providers", "encrypted_admin_api_key")
