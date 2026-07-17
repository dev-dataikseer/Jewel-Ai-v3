"""Job cancel/stuck-job safety: celery_task_id + stuck sweep index.

Revision ID: 004_celery_task_id
Revises: 003_batch_user
"""

from alembic import op
import sqlalchemy as sa

revision = "004_celery_task_id"
down_revision = "003_batch_user"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if not inspector.has_table("generation_jobs"):
        return
    cols = {c["name"] for c in inspector.get_columns("generation_jobs")}
    indexes = {i["name"] for i in inspector.get_indexes("generation_jobs")}
    if "celery_task_id" not in cols:
        op.add_column(
            "generation_jobs",
            sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        )
    if "ix_jobs_celery_task_id" not in indexes:
        op.create_index("ix_jobs_celery_task_id", "generation_jobs", ["celery_task_id"])
    if "ix_jobs_status_processing_started" not in indexes:
        op.create_index(
            "ix_jobs_status_processing_started",
            "generation_jobs",
            ["status", "processing_started_at"],
        )


def downgrade() -> None:
    op.drop_index("ix_jobs_status_processing_started", table_name="generation_jobs")
    op.drop_index("ix_jobs_celery_task_id", table_name="generation_jobs")
    op.drop_column("generation_jobs", "celery_task_id")
