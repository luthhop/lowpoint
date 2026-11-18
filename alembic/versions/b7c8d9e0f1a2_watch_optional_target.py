"""watches.target_price opcional + watches.target_suggested_at

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-11-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "a6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # DROP NOT NULL e ADD COLUMN nullable sem default: só metadado no Postgres,
    # sem reescrever a tabela. Linhas existentes ficam iguais (todas com alvo).
    op.alter_column(
        "watches", "target_price",
        existing_type=sa.Numeric(12, 2), nullable=True,
    )
    op.add_column(
        "watches",
        sa.Column("target_suggested_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # Falha de propósito se existir watch sem alvo: decidir antes o que fazer com ele.
    op.drop_column("watches", "target_suggested_at")
    op.alter_column(
        "watches", "target_price",
        existing_type=sa.Numeric(12, 2), nullable=False,
    )
