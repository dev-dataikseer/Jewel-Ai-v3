"""Tenancy columns/indexes (idempotent for DBs that already have them).

Revision ID: 002_tenancy
Revises: 001_initial
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_tenancy"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if inspector.has_table("projects"):
        cols = {c["name"] for c in inspector.get_columns("projects")}
        indexes = {i["name"] for i in inspector.get_indexes("projects")}
        if "user_id" not in cols:
            op.add_column("projects", sa.Column("user_id", sa.String(length=36), nullable=True))
        if "ix_projects_user_id" not in indexes:
            op.create_index("ix_projects_user_id", "projects", ["user_id"])

    if inspector.has_table("favorites"):
        cols = {c["name"] for c in inspector.get_columns("favorites")}
        indexes = {i["name"] for i in inspector.get_indexes("favorites")}
        uqs = {u["name"] for u in inspector.get_unique_constraints("favorites")}
        if "user_id" not in cols:
            op.add_column("favorites", sa.Column("user_id", sa.String(length=36), nullable=True))
            op.execute(
                """
                UPDATE favorites
                SET user_id = (
                    SELECT user_id FROM generation_jobs
                    WHERE generation_jobs.id = favorites.job_id
                )
                """
            )
            op.execute("DELETE FROM favorites WHERE user_id IS NULL")
            op.alter_column("favorites", "user_id", nullable=False)
        if "uq_favorite_user_job" not in uqs:
            op.create_unique_constraint("uq_favorite_user_job", "favorites", ["user_id", "job_id"])
        if "ix_favorites_user_id" not in indexes:
            op.create_index("ix_favorites_user_id", "favorites", ["user_id"])

    if inspector.has_table("generation_jobs"):
        indexes = {i["name"] for i in inspector.get_indexes("generation_jobs")}
        if "ix_jobs_user_status" not in indexes:
            op.create_index("ix_jobs_user_status", "generation_jobs", ["user_id", "status"])
        if "ix_jobs_batch_id" not in indexes:
            op.create_index("ix_jobs_batch_id", "generation_jobs", ["batch_id"])


def downgrade() -> None:
    op.drop_index("ix_jobs_batch_id", table_name="generation_jobs")
    op.drop_index("ix_jobs_user_status", table_name="generation_jobs")
    op.drop_index("ix_favorites_user_id", table_name="favorites")
    op.drop_constraint("uq_favorite_user_job", "favorites", type_="unique")
    op.drop_column("favorites", "user_id")
    op.drop_index("ix_projects_user_id", table_name="projects")
    op.drop_column("projects", "user_id")
