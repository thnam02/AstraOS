"""Configurable merchant commercial objective.

Revision ID: 0011_merchant_objective
Revises: 0010_learning
Create Date: 2026-09-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_merchant_objective"
down_revision: str | Sequence[str] | None = "0010_learning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "merchant_objectives",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("merchant_id", sa.Uuid(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("buyer_weight", sa.Numeric(6, 4), nullable=False),
        sa.Column("merchant_weight", sa.Numeric(6, 4), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "buyer_weight >= 0 AND buyer_weight <= 1",
            name="ck_objective_buyer_weight",
        ),
        sa.CheckConstraint(
            "merchant_weight >= 0 AND merchant_weight <= 1",
            name="ck_objective_merchant_weight",
        ),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_merchant_objectives_merchant_id"),
        "merchant_objectives",
        ["merchant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_merchant_objectives_is_active"),
        "merchant_objectives",
        ["is_active"],
        unique=False,
    )
    op.add_column(
        "optimisation_runs",
        sa.Column(
            "merchant_objective",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.execute(
        """
        INSERT INTO merchant_objectives (
            id, merchant_id, mode, buyer_weight, merchant_weight,
            version, is_active
        )
        SELECT
            gen_random_uuid(),
            id,
            'BALANCED',
            0.5000,
            0.5000,
            'merchant-objective-v1',
            true
        FROM merchants
        """
    )
    op.execute(
        """
        UPDATE optimisation_runs
        SET merchant_objective = jsonb_build_object(
            'mode', 'BALANCED',
            'buyer_weight', 0.5,
            'merchant_weight', 0.5,
            'version', 'merchant-objective-v1'
        )
        WHERE merchant_objective IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("optimisation_runs", "merchant_objective")
    op.drop_index(
        op.f("ix_merchant_objectives_is_active"), table_name="merchant_objectives"
    )
    op.drop_index(
        op.f("ix_merchant_objectives_merchant_id"), table_name="merchant_objectives"
    )
    op.drop_table("merchant_objectives")
