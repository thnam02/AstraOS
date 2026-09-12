"""Qualification run persistence.

Revision ID: 0003_qualification_runs
Revises: 0002_domain_models
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_qualification_runs"
down_revision: str | Sequence[str] | None = "0002_domain_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "qualification_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("raw_intent", sa.Text(), nullable=False),
        sa.Column("parsed_intent", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("parser_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "qualification_variant_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("brand", sa.String(length=120), nullable=False),
        sa.Column("variant_name", sa.String(length=120), nullable=True),
        sa.Column("base_price_cents", sa.Integer(), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("violated_count", sa.Integer(), nullable=False),
        sa.Column("unknown_count", sa.Integer(), nullable=False),
        sa.Column("satisfied_count", sa.Integer(), nullable=False),
        sa.Column(
            "exclusion_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "evaluations",
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
            ["run_id"], ["qualification_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "variant_id", name="uq_qualification_run_variant"),
    )
    op.create_index(
        "ix_qualification_variant_results_run_id",
        "qualification_variant_results",
        ["run_id"],
    )
    op.create_index(
        "ix_qualification_variant_results_variant_id",
        "qualification_variant_results",
        ["variant_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_qualification_variant_results_variant_id",
        table_name="qualification_variant_results",
    )
    op.drop_index(
        "ix_qualification_variant_results_run_id",
        table_name="qualification_variant_results",
    )
    op.drop_table("qualification_variant_results")
    op.drop_table("qualification_runs")
