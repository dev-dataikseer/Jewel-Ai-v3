"""Prompt Profile V2 tables: profiles, jewelry sections, image roles.

Revision ID: 008_prompt_profiles_v2
Revises: 007_batch_wallclock
"""

from alembic import op
import sqlalchemy as sa

revision = "008_prompt_profiles_v2"
down_revision = "007_batch_wallclock"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if not inspector.has_table("prompt_profiles"):
        op.create_table(
            "prompt_profiles",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("workflow", sa.String(64), nullable=False, index=True),
            sa.Column("reference_mode", sa.String(32), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("active_version_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("workflow", "reference_mode", name="uq_profile_workflow_ref"),
        )

    if not inspector.has_table("prompt_profile_versions"):
        op.create_table(
            "prompt_profile_versions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("profile_id", sa.String(36), sa.ForeignKey("prompt_profiles.id"), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("content_json", sa.JSON(), nullable=False),
            sa.Column("environment_pool", sa.JSON(), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("source", sa.String(32), server_default="seed"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if not inspector.has_table("prompt_jewelry_sections"):
        op.create_table(
            "prompt_jewelry_sections",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("workflow", sa.String(64), nullable=False, index=True),
            sa.Column("jewelry_type", sa.String(128), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("active_version_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("workflow", "jewelry_type", name="uq_jewelry_section_workflow_type"),
        )

    if not inspector.has_table("prompt_jewelry_section_versions"):
        op.create_table(
            "prompt_jewelry_section_versions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "section_id",
                sa.String(36),
                sa.ForeignKey("prompt_jewelry_sections.id"),
                nullable=False,
            ),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("content_json", sa.JSON(), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("source", sa.String(32), server_default="seed"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if not inspector.has_table("prompt_image_roles"):
        op.create_table(
            "prompt_image_roles",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("role", sa.String(32), nullable=False, index=True),
            sa.Column("workflow", sa.String(64), nullable=True, index=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("instruction", sa.Text(), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("version", sa.Integer(), server_default="1"),
            sa.Column("source", sa.String(32), server_default="seed"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("role", "workflow", name="uq_image_role_workflow"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for table in (
        "prompt_image_roles",
        "prompt_jewelry_section_versions",
        "prompt_jewelry_sections",
        "prompt_profile_versions",
        "prompt_profiles",
    ):
        if inspector.has_table(table):
            op.drop_table(table)
