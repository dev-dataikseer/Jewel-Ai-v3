"""Initial schema placeholder — tables created via SQLAlchemy metadata at startup.

Revision ID: 001_initial
Revises:
Create Date: 2026-07-02

"""
from typing import Sequence, Union

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  pass


def downgrade() -> None:
  pass
