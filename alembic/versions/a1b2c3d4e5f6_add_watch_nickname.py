"""add watch nickname

Revision ID: a1b2c3d4e5f6
Revises: c7e8f9a0b1d2
Create Date: 2026-11-02
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "c7e8f9a0b1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("watches", sa.Column("nickname", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("watches", "nickname")
