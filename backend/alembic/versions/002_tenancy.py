"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_tenancy"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("user_id", sa.String(length=36), nullable=True))
    op.create_index("ix_projects_user_id", "projects", ["user_id"])

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
    op.create_unique_constraint("uq_favorite_user_job", "favorites", ["user_id", "job_id"])
    op.create_index("ix_favorites_user_id", "favorites", ["user_id"])

    op.create_index("ix_jobs_user_status", "generation_jobs", ["user_id", "status"])
    op.create_index("ix_jobs_batch_id", "generation_jobs", ["batch_id"])


def downgrade() -> None:
    op.drop_index("ix_jobs_batch_id", table_name="generation_jobs")
    op.drop_index("ix_jobs_user_status", table_name="generation_jobs")
    op.drop_index("ix_favorites_user_id", table_name="favorites")
    op.drop_constraint("uq_favorite_user_job", "favorites", type_="unique")
    op.drop_column("favorites", "user_id")
    op.drop_index("ix_projects_user_id", table_name="projects")
    op.drop_column("projects", "user_id")
