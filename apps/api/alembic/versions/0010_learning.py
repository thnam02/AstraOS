"""Intent-offer-outcome learning registry.

Revision ID: 0010_learning
Revises: 0009_arena
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_learning"
down_revision: str | Sequence[str] | None = "0009_arena"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "commerce_interactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("intent_request_id", sa.Uuid(), nullable=True),
        sa.Column("qualification_run_id", sa.Uuid(), nullable=True),
        sa.Column("match_run_id", sa.Uuid(), nullable=True),
        sa.Column("offer_run_id", sa.Uuid(), nullable=True),
        sa.Column("optimisation_run_id", sa.Uuid(), nullable=True),
        sa.Column("negotiation_session_id", sa.Uuid(), nullable=True),
        sa.Column("proposal_id", sa.Uuid(), nullable=True),
        sa.Column("offer_id", sa.Uuid(), nullable=True),
        sa.Column("transaction_id", sa.Uuid(), nullable=True),
        sa.Column("arena_run_id", sa.Uuid(), nullable=True),
        sa.Column("group_id", sa.String(length=80), nullable=False),
        sa.Column("buyer_profile", sa.String(length=40), nullable=True),
        sa.Column(
            "structured_intent",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "offer_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "features", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("product_fit", sa.String(length=24), nullable=False),
        sa.Column("total_price_cents", sa.Integer(), nullable=False),
        sa.Column("delivery", sa.String(length=40), nullable=True),
        sa.Column("warranty", sa.String(length=40), nullable=True),
        sa.Column("bundle", sa.String(length=40), nullable=True),
        sa.Column("returns", sa.String(length=40), nullable=True),
        sa.Column("merchant_contribution_cents", sa.Integer(), nullable=False),
        sa.Column("intervention_cost_cents", sa.Integer(), nullable=False),
        sa.Column("outcome_type", sa.String(length=32), nullable=False),
        sa.Column("selected", sa.Boolean(), nullable=True),
        sa.Column("accepted", sa.Boolean(), nullable=True),
        sa.Column("transacted", sa.Boolean(), nullable=True),
        sa.Column("outcome_source", sa.String(length=40), nullable=False),
        sa.Column("policy_safe", sa.Boolean(), nullable=False),
        sa.Column("hard_constraints_satisfied", sa.Boolean(), nullable=False),
        sa.Column("buyer_utility", sa.String(length=24), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "interaction_metadata",
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
    op.create_index(
        "ix_commerce_interactions_group_id",
        "commerce_interactions",
        ["group_id"],
    )
    op.create_index(
        "ix_commerce_interactions_offer_id",
        "commerce_interactions",
        ["offer_id"],
    )
    op.create_index(
        "ix_commerce_interactions_outcome_source",
        "commerce_interactions",
        ["outcome_source"],
    )
    op.create_table(
        "learning_dataset_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "source_types",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("interaction_count", sa.Integer(), nullable=False),
        sa.Column("positive_count", sa.Integer(), nullable=False),
        sa.Column("negative_count", sa.Integer(), nullable=False),
        sa.Column("feature_schema_version", sa.String(length=32), nullable=False),
        sa.Column(
            "dataset_metadata",
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
        "model_training_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column(
            "algorithms", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "results", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["learning_dataset_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_model_training_runs_dataset_id",
        "model_training_runs",
        ["dataset_id"],
    )
    op.create_table(
        "response_model_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("algorithm", sa.String(length=40), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("training_data_source", sa.String(length=64), nullable=False),
        sa.Column("training_dataset_version", sa.String(length=64), nullable=False),
        sa.Column("feature_schema_version", sa.String(length=32), nullable=False),
        sa.Column("train_size", sa.Integer(), nullable=False),
        sa.Column("validation_size", sa.Integer(), nullable=False),
        sa.Column("test_size", sa.Integer(), nullable=False),
        sa.Column(
            "parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("artifact_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("training_run_id", sa.Uuid(), nullable=True),
        sa.Column("dataset_id", sa.Uuid(), nullable=True),
        sa.Column(
            "model_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["learning_dataset_versions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["training_run_id"],
            ["model_training_runs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_response_model_versions_status",
        "response_model_versions",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_response_model_versions_status",
        table_name="response_model_versions",
    )
    op.drop_table("response_model_versions")
    op.drop_index(
        "ix_model_training_runs_dataset_id", table_name="model_training_runs"
    )
    op.drop_table("model_training_runs")
    op.drop_table("learning_dataset_versions")
    op.drop_index(
        "ix_commerce_interactions_outcome_source",
        table_name="commerce_interactions",
    )
    op.drop_index(
        "ix_commerce_interactions_offer_id", table_name="commerce_interactions"
    )
    op.drop_index(
        "ix_commerce_interactions_group_id", table_name="commerce_interactions"
    )
    op.drop_table("commerce_interactions")
