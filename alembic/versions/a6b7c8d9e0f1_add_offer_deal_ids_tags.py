"""add offer_snapshots.deal_ids e tags

Revision ID: a6b7c8d9e0f1
Revises: f4a5b6c7d8e9
Create Date: 2026-11-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a6b7c8d9e0f1"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_JSONList = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    # Só ADD COLUMN nullable sem default: metadado, sem reescrever a tabela.
    # Linhas antigas ficam NULL (= coletadas antes da mudança).
    op.add_column("offer_snapshots", sa.Column("deal_ids", _JSONList, nullable=True))
    op.add_column("offer_snapshots", sa.Column("tags", _JSONList, nullable=True))


def downgrade() -> None:
    op.drop_column("offer_snapshots", "tags")
    op.drop_column("offer_snapshots", "deal_ids")
