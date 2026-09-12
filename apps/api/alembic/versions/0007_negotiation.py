"""Negotiation sessions, turns, and immutable proposals.

Revision ID: 0007_negotiation
Revises: 0006_optimisation
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_negotiation"
down_revision: str | Sequence[str] | None = "0006_optimisation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "negotiation_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("initial_intent_run_id", sa.Uuid(), nullable=True),
        sa.Column("match_run_id", sa.Uuid(), nullable=True),
        sa.Column("offer_run_id", sa.Uuid(), nullable=True),
        sa.Column("optimisation_run_id", sa.Uuid(), nullable=True),
        sa.Column("current_offer_id", sa.Uuid(), nullable=True),
        sa.Column("current_proposal_id", sa.Uuid(), nullable=True),
        sa.Column("current_state", sa.String(length=40), nullable=False),
        sa.Column("buyer_agent_type", sa.String(length=40), nullable=False),
        sa.Column("buyer_profile", sa.String(length=40), nullable=False),
        sa.Column("merchant_policy_version", sa.String(length=64), nullable=False),
        sa.Column(
            "original_intent",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "working_intent",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "delta_history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("events", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_intent", sa.Text(), nullable=False),
        sa.Column("turn_count", sa.Integer(), nullable=False),
        sa.Column("max_turns", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "session_metadata",
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
            ["initial_intent_run_id"], ["match_runs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["match_run_id"], ["match_runs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["offer_run_id"],
            ["offer_construction_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["optimisation_run_id"],
            ["optimisation_runs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "negotiation_turns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=24), nullable=False),
        sa.Column("raw_message", sa.Text(), nullable=True),
        sa.Column("structured_action", sa.String(length=40), nullable=False),
        sa.Column(
            "structured_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("related_offer_id", sa.Uuid(), nullable=True),
        sa.Column("related_proposal_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["negotiation_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_negotiation_turns_session_id",
        "negotiation_turns",
        ["session_id"],
    )
    op.create_table(
        "merchant_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("proposal_type", sa.String(length=32), nullable=False),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=True),
        sa.Column("optimisation_run_id", sa.Uuid(), nullable=True),
        sa.Column(
            "offer_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "reason_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "explanation",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "next_allowed_actions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("compromise", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["negotiation_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_merchant_proposals_session_id",
        "merchant_proposals",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_merchant_proposals_session_id", table_name="merchant_proposals")
    op.drop_table("merchant_proposals")
    op.drop_index("ix_negotiation_turns_session_id", table_name="negotiation_turns")
    op.drop_table("negotiation_turns")
    op.drop_table("negotiation_sessions")
