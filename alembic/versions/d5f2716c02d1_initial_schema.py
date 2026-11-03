"""initial schema

Revision ID: d5f2716c02d1
Revises:
Create Date: 2026-11-02 10:46:23.193379

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5f2716c02d1"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("catalog_product_id", sa.String, unique=True, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("url", sa.String, nullable=False),
        sa.Column("image_url", sa.String, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "watches",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("chat_id", sa.BigInteger, nullable=False),
        sa.Column(
            "product_id",
            sa.Integer,
            sa.ForeignKey("products.id"),
            nullable=False,
        ),
        sa.Column("target_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("chat_id", "product_id", name="uq_watch_chat_product"),
    )

    op.create_table(
        "offer_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer,
            sa.ForeignKey("products.id"),
            nullable=False,
        ),
        sa.Column("item_id", sa.String, nullable=False),
        sa.Column("seller_id", sa.BigInteger, nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("original_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("condition", sa.String, nullable=False),
        sa.Column("official_store_id", sa.Integer, nullable=True),
        sa.Column("free_shipping", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("warranty", sa.String, nullable=True),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer,
            sa.ForeignKey("products.id"),
            nullable=False,
        ),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("original_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("item_id", sa.String, nullable=False),
        sa.Column("seller_id", sa.BigInteger, nullable=False),
        sa.Column("available", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_price_history_product_collected",
        "price_history",
        ["product_id", "collected_at"],
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "watch_id",
            sa.Integer,
            sa.ForeignKey("watches.id"),
            nullable=False,
        ),
        sa.Column("alert_type", sa.String, nullable=False),
        sa.Column("verdict", sa.String, nullable=True),
        sa.Column("price_at_alert", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_index("ix_price_history_product_collected", table_name="price_history")
    op.drop_table("price_history")
    op.drop_table("offer_snapshots")
    op.drop_table("watches")
    op.drop_table("products")
