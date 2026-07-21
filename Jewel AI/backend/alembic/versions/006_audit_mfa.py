"""Sprint 2: MFA columns + audit_logs.

Revision ID: 006_audit_mfa
Revises: 005_provider_admin_key
"""

from alembic import op
import sqlalchemy as sa

revision = "006_audit_mfa"
down_revision = "005_provider_admin_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if inspector.has_table("users"):
        cols = {c["name"] for c in inspector.get_columns("users")}
        if "totp_enabled" not in cols:
            op.add_column("users", sa.Column("totp_enabled", sa.Boolean(), server_default=sa.false(), nullable=False))
        if "encrypted_totp_secret" not in cols:
            op.add_column("users", sa.Column("encrypted_totp_secret", sa.LargeBinary(), nullable=True))
        if "totp_backup_hashes" not in cols:
            op.add_column("users", sa.Column("totp_backup_hashes", sa.JSON(), nullable=True))

    if not inspector.has_table("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("action", sa.String(128), nullable=False),
            sa.Column("entity_type", sa.String(64), nullable=False),
            sa.Column("entity_id", sa.String(64), nullable=True),
            sa.Column("before", sa.JSON(), nullable=True),
            sa.Column("after", sa.JSON(), nullable=True),
            sa.Column("request_id", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_column("users", "totp_backup_hashes")
    op.drop_column("users", "encrypted_totp_secret")
    op.drop_column("users", "totp_enabled")
