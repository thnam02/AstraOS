"""Offer construction runs and candidates.

Revision ID: 0005_offer_construction
Revises: 0004_semantic_matching
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_offer_construction"
down_revision: str | Sequence[str] | None = "0004_semantic_matching"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "offer_construction_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("match_run_id", sa.Uuid(), nullable=True),
        sa.Column("raw_intent", sa.Text(), nullable=False),
        sa.Column("parsed_intent", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("construction_version", sa.String(length=32), nullable=False),
        sa.Column("top_product_count", sa.Integer(), nullable=False),
        sa.Column("estimated_candidates", sa.Integer(), nullable=False),
        sa.Column("generated_offer_count", sa.Integer(), nullable=False),
        sa.Column("feasible_offer_count", sa.Integer(), nullable=False),
        sa.Column("rejected_offer_count", sa.Integer(), nullable=False),
        sa.Column("pruning_reason", sa.String(length=80), nullable=True),
        sa.Column("dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "rejection_distribution",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("timing", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "construction_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["match_run_id"], ["match_runs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_offer_construction_runs_match_run_id",
        "offer_construction_runs",
        ["match_run_id"],
    )

    op.create_table(
        "offer_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("brand", sa.String(length=120), nullable=False),
        sa.Column("construction_status", sa.String(length=24), nullable=False),
        sa.Column("feasibility_status", sa.String(length=24), nullable=False),
        sa.Column("delivery_code", sa.String(length=32), nullable=False),
        sa.Column("warranty_code", sa.String(length=32), nullable=False),
        sa.Column("bundle_code", sa.String(length=32), nullable=True),
        sa.Column("return_policy_code", sa.String(length=32), nullable=True),
        sa.Column("final_product_price_cents", sa.Integer(), nullable=False),
        sa.Column("total_customer_price_cents", sa.Integer(), nullable=False),
        sa.Column("direct_intervention_cost_cents", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "rejection_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["offer_construction_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_offer_candidates_run_id", "offer_candidates", ["run_id"])
    op.create_index("ix_offer_candidates_variant_id", "offer_candidates", ["variant_id"])
    op.create_index("ix_offer_candidates_product_id", "offer_candidates", ["product_id"])
    op.create_index("ix_offer_candidates_sku", "offer_candidates", ["sku"])
    op.create_index(
        "ix_offer_candidates_feasibility_status",
        "offer_candidates",
        ["feasibility_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_offer_candidates_feasibility_status", table_name="offer_candidates")
    op.drop_index("ix_offer_candidates_sku", table_name="offer_candidates")
    op.drop_index("ix_offer_candidates_product_id", table_name="offer_candidates")
    op.drop_index("ix_offer_candidates_variant_id", table_name="offer_candidates")
    op.drop_index("ix_offer_candidates_run_id", table_name="offer_candidates")
    op.drop_table("offer_candidates")
    op.drop_index(
        "ix_offer_construction_runs_match_run_id",
        table_name="offer_construction_runs",
    )
    op.drop_table("offer_construction_runs")
