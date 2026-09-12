"""Proposal acceptance, reservations, and orders.

Revision ID: 0008_commerce
Revises: 0007_negotiation
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_commerce"
down_revision: str | Sequence[str] | None = "0007_negotiation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "commerce_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("negotiation_session_id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=True),
        sa.Column("transaction_state", sa.String(length=32), nullable=False),
        sa.Column("reservation_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column(
            "failure_details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "revalidation",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("events", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "transaction_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["negotiation_session_id"],
            ["negotiation_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["merchant_proposals.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_commerce_transactions_idemp"),
    )
    op.create_index(
        "ix_commerce_transactions_negotiation_session_id",
        "commerce_transactions",
        ["negotiation_session_id"],
    )
    op.create_index(
        "ix_commerce_transactions_proposal_id",
        "commerce_transactions",
        ["proposal_id"],
    )
    op.create_index(
        "ix_commerce_transactions_offer_id",
        "commerce_transactions",
        ["offer_id"],
    )
    op.create_index(
        "ix_commerce_confirmed_proposal",
        "commerce_transactions",
        ["proposal_id"],
        unique=True,
        postgresql_where=sa.text("transaction_state = 'CONFIRMED'"),
    )
    op.create_table(
        "inventory_reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["commerce_transactions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["product_variants.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inventory_reservations_transaction_id",
        "inventory_reservations",
        ["transaction_id"],
    )
    op.create_index(
        "ix_inventory_reservations_variant_id",
        "inventory_reservations",
        ["variant_id"],
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.String(length=32), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("negotiation_session_id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=True),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("product_price_cents", sa.Integer(), nullable=False),
        sa.Column("delivery_charge_cents", sa.Integer(), nullable=False),
        sa.Column("warranty_price_cents", sa.Integer(), nullable=False),
        sa.Column("bundle_price_cents", sa.Integer(), nullable=False),
        sa.Column("total_amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("delivery_option_id", sa.Uuid(), nullable=True),
        sa.Column("warranty_option_id", sa.Uuid(), nullable=True),
        sa.Column("bundle_option_id", sa.Uuid(), nullable=True),
        sa.Column("return_policy_id", sa.Uuid(), nullable=True),
        sa.Column("delivery_code", sa.String(length=32), nullable=True),
        sa.Column("warranty_code", sa.String(length=32), nullable=True),
        sa.Column("bundle_code", sa.String(length=32), nullable=True),
        sa.Column("return_policy_code", sa.String(length=32), nullable=True),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("warranty_months", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("payment_mode", sa.String(length=32), nullable=False),
        sa.Column("payment_status", sa.String(length=40), nullable=False),
        sa.Column(
            "confirmation",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["commerce_transactions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["negotiation_session_id"],
            ["negotiation_sessions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["merchant_proposals.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["product_variants.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_number", name="uq_orders_order_number"),
        sa.UniqueConstraint("transaction_id"),
    )
    op.create_index(
        "ix_orders_negotiation_session_id",
        "orders",
        ["negotiation_session_id"],
    )
    op.create_table(
        "order_number_sequences",
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("last_value", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("year"),
    )


def downgrade() -> None:
    op.drop_table("order_number_sequences")
    op.drop_index("ix_orders_negotiation_session_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index(
        "ix_inventory_reservations_variant_id",
        table_name="inventory_reservations",
    )
    op.drop_index(
        "ix_inventory_reservations_transaction_id",
        table_name="inventory_reservations",
    )
    op.drop_table("inventory_reservations")
    op.drop_index(
        "ix_commerce_confirmed_proposal",
        table_name="commerce_transactions",
    )
    op.drop_index(
        "ix_commerce_transactions_offer_id",
        table_name="commerce_transactions",
    )
    op.drop_index(
        "ix_commerce_transactions_proposal_id",
        table_name="commerce_transactions",
    )
    op.drop_index(
        "ix_commerce_transactions_negotiation_session_id",
        table_name="commerce_transactions",
    )
    op.drop_table("commerce_transactions")
