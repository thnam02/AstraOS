"""Semantic embeddings and match runs.

Revision ID: 0004_semantic_matching
Revises: 0003_qualification_runs
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_semantic_matching"
down_revision: str | Sequence[str] | None = "0003_qualification_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "variant_embeddings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("embedding_model", sa.String(length=80), nullable=False),
        sa.Column("semantic_document_version", sa.String(length=64), nullable=False),
        sa.Column("document_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"], ["product_variants.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("variant_id"),
    )

    op.create_table(
        "match_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("raw_intent", sa.Text(), nullable=False),
        sa.Column("parsed_intent", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("parser_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("embedding_model", sa.String(length=80), nullable=False),
        sa.Column("semantic_document_version", sa.String(length=64), nullable=False),
        sa.Column(
            "qualification_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("timing", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "eligible_variant_ids",
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
        "match_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("brand", sa.String(length=120), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["match_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "variant_id", name="uq_match_run_variant"),
    )
    op.create_index("ix_match_results_run_id", "match_results", ["run_id"])
    op.create_index("ix_match_results_variant_id", "match_results", ["variant_id"])


def downgrade() -> None:
    op.drop_index("ix_match_results_variant_id", table_name="match_results")
    op.drop_index("ix_match_results_run_id", table_name="match_results")
    op.drop_table("match_results")
    op.drop_table("match_runs")
    op.drop_table("variant_embeddings")
