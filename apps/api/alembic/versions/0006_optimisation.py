"""Optimisation runs.

Revision ID: 0006_optimisation
Revises: 0005_offer_construction
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_optimisation"
down_revision: str | Sequence[str] | None = "0005_offer_construction"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "optimisation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("offer_run_id", sa.Uuid(), nullable=False),
        sa.Column("match_run_id", sa.Uuid(), nullable=True),
        sa.Column("buyer_profile", sa.String(length=40), nullable=False),
        sa.Column(
            "weight_configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("merchant_policy_id", sa.Uuid(), nullable=True),
        sa.Column(
            "merchant_policy_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("total_offers", sa.Integer(), nullable=False),
        sa.Column("policy_safe_offers", sa.Integer(), nullable=False),
        sa.Column("policy_rejected_offers", sa.Integer(), nullable=False),
        sa.Column("pareto_count", sa.Integer(), nullable=False),
        sa.Column("recommended_offer_id", sa.Uuid(), nullable=True),
        sa.Column("algorithm_version", sa.String(length=32), nullable=False),
        sa.Column("selection_rule", sa.String(length=40), nullable=False),
        sa.Column("selection_alpha", sa.String(length=16), nullable=False),
        sa.Column("raw_intent", sa.Text(), nullable=False),
        sa.Column("timing", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "buyer_model", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("recommended", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "pareto_offers", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "plot_points", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "counterfactuals", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "comparisons", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("failure", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "run_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["offer_run_id"],
            ["offer_construction_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["match_run_id"], ["match_runs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_optimisation_runs_offer_run_id",
        "optimisation_runs",
        ["offer_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_optimisation_runs_offer_run_id", table_name="optimisation_runs")
    op.drop_table("optimisation_runs")
