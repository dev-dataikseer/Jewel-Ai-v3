"""Create prompt_fragments tables (missing from Alembic path).

Revision ID: 009_prompt_fragments
Revises: 008_prompt_profiles_v2
"""

from alembic import op
import sqlalchemy as sa

revision = "009_prompt_fragments"
down_revision = "008_prompt_profiles_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if not inspector.has_table("prompt_fragments"):
        op.create_table(
            "prompt_fragments",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("fragment_key", sa.String(128), nullable=False, unique=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("active_version_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if not inspector.has_table("prompt_fragment_versions"):
        op.create_table(
            "prompt_fragment_versions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "fragment_id",
                sa.String(36),
                sa.ForeignKey("prompt_fragments.id"),
                nullable=False,
            ),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("prompt_text", sa.Text(), nullable=False),
            sa.Column("content_json", sa.JSON(), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("source", sa.String(32), server_default="seed"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("prompt_fragment_versions")
    op.drop_table("prompt_fragments")
