"""fix watches active not null

Revision ID: b935f180e30a
Revises: d5f2716c02d1
Create Date: 2026-11-02 11:01:16.352706

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b935f180e30a"
down_revision: Union[str, Sequence[str], None] = "d5f2716c02d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "watches",
        "active",
        existing_type=sa.Boolean(),
        nullable=False,
        existing_server_default=sa.text("true"),
    )


def downgrade() -> None:
    op.alter_column(
        "watches",
        "active",
        existing_type=sa.Boolean(),
        nullable=True,
        existing_server_default=sa.text("true"),
    )
