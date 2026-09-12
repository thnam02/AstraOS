"""Agent Arena duels and synthetic benchmarks.

Revision ID: 0009_arena
Revises: 0008_commerce
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_arena"
down_revision: str | Sequence[str] | None = "0008_commerce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "arena_benchmark_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("mission_count", sa.Integer(), nullable=False),
        sa.Column(
            "strategy_names",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("buyer_model_version", sa.String(length=40), nullable=False),
        sa.Column("merchant_policy_version", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "config", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "events", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "run_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "arena_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("mission_id", sa.String(length=64), nullable=False),
        sa.Column("buyer_profile", sa.String(length=40), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("buyer_selected_strategy", sa.String(length=40), nullable=True),
        sa.Column("buyer_selected_offer_id", sa.Uuid(), nullable=True),
        sa.Column("no_purchase", sa.Boolean(), nullable=False),
        sa.Column(
            "mission", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "strategy_responses",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "selection", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "events", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "run_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("benchmark_run_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["benchmark_run_id"],
            ["arena_benchmark_runs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_arena_runs_mission_id", "arena_runs", ["mission_id"])
    op.create_index(
        "ix_arena_runs_benchmark_run_id", "arena_runs", ["benchmark_run_id"]
    )
    op.create_table(
        "arena_strategy_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("benchmark_run_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_name", sa.String(length=40), nullable=False),
        sa.Column("missions", sa.Integer(), nullable=False),
        sa.Column("wins", sa.Integer(), nullable=False),
        sa.Column("selection_rate", sa.String(length=24), nullable=False),
        sa.Column("avg_buyer_utility", sa.String(length=24), nullable=True),
        sa.Column(
            "avg_contribution_when_selected",
            sa.String(length=24),
            nullable=True,
        ),
        sa.Column(
            "contribution_per_opportunity",
            sa.String(length=24),
            nullable=False,
        ),
        sa.Column("avg_intervention_cost", sa.String(length=24), nullable=True),
        sa.Column(
            "hard_constraint_violation_rate",
            sa.String(length=24),
            nullable=False,
        ),
        sa.Column("policy_violation_rate", sa.String(length=24), nullable=False),
        sa.Column("no_offer_rate", sa.String(length=24), nullable=False),
        sa.Column(
            "transaction_completion_rate",
            sa.String(length=24),
            nullable=False,
        ),
        sa.Column(
            "payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["benchmark_run_id"],
            ["arena_benchmark_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_arena_strategy_metrics_benchmark_run_id",
        "arena_strategy_metrics",
        ["benchmark_run_id"],
    )
    op.create_table(
        "arena_segment_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("benchmark_run_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_tag", sa.String(length=40), nullable=False),
        sa.Column("buyer_profile", sa.String(length=40), nullable=False),
        sa.Column("strategy_name", sa.String(length=40), nullable=False),
        sa.Column("missions", sa.Integer(), nullable=False),
        sa.Column("wins", sa.Integer(), nullable=False),
        sa.Column("selection_rate", sa.String(length=24), nullable=False),
        sa.Column(
            "payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["benchmark_run_id"],
            ["arena_benchmark_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_arena_segment_metrics_benchmark_run_id",
        "arena_segment_metrics",
        ["benchmark_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_arena_segment_metrics_benchmark_run_id",
        table_name="arena_segment_metrics",
    )
    op.drop_table("arena_segment_metrics")
    op.drop_index(
        "ix_arena_strategy_metrics_benchmark_run_id",
        table_name="arena_strategy_metrics",
    )
    op.drop_table("arena_strategy_metrics")
    op.drop_index("ix_arena_runs_benchmark_run_id", table_name="arena_runs")
    op.drop_index("ix_arena_runs_mission_id", table_name="arena_runs")
    op.drop_table("arena_runs")
    op.drop_table("arena_benchmark_runs")
