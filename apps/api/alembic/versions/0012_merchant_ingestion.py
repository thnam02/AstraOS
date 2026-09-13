"""Merchant catalogue ingestion runs and external identifiers.

Revision ID: 0012_merchant_ingestion
Revises: 0011_merchant_objective
Create Date: 2026-09-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_merchant_ingestion"
down_revision: str | Sequence[str] | None = "0011_merchant_objective"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "merchant_ingestion_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("merchant_id", sa.Uuid(), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_name", sa.String(length=240), nullable=False),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("snapshot_mode", sa.String(length=16), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("initiated_by", sa.String(length=80), nullable=True),
        sa.Column("records_received", sa.Integer(), nullable=False),
        sa.Column("records_created", sa.Integer(), nullable=False),
        sa.Column("records_updated", sa.Integer(), nullable=False),
        sa.Column("records_unchanged", sa.Integer(), nullable=False),
        sa.Column("records_rejected", sa.Integer(), nullable=False),
        sa.Column("records_deactivated", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("semantic_documents_changed", sa.Integer(), nullable=False),
        sa.Column("embeddings_refreshed", sa.Integer(), nullable=False),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("errors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("index_status", sa.String(length=32), nullable=True),
        sa.Column("failure_detail", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_merchant_ingestion_runs_merchant_id"),
        "merchant_ingestion_runs",
        ["merchant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_merchant_ingestion_runs_status"),
        "merchant_ingestion_runs",
        ["status"],
        unique=False,
    )
    op.add_column(
        "merchants",
        sa.Column(
            "data_mode",
            sa.String(length=16),
            nullable=False,
            server_default="DEMO_SEED",
        ),
    )
    op.add_column(
        "products", sa.Column("external_id", sa.String(length=80), nullable=True)
    )
    op.add_column(
        "products", sa.Column("source_system", sa.String(length=40), nullable=True)
    )
    op.add_column(
        "products", sa.Column("source_record_id", sa.String(length=120), nullable=True)
    )
    op.add_column("products", sa.Column("import_run_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_products_external_id"), "products", ["external_id"], unique=True
    )
    op.create_index(
        op.f("ix_products_source_system"), "products", ["source_system"], unique=False
    )
    op.create_index(
        op.f("ix_products_import_run_id"), "products", ["import_run_id"], unique=False
    )
    op.create_foreign_key(
        "fk_products_import_run_id",
        "products",
        "merchant_ingestion_runs",
        ["import_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "product_variants",
        sa.Column("source_system", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "product_variants",
        sa.Column("source_record_id", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "product_variants", sa.Column("import_run_id", sa.Uuid(), nullable=True)
    )
    op.create_index(
        op.f("ix_product_variants_source_system"),
        "product_variants",
        ["source_system"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_variants_import_run_id"),
        "product_variants",
        ["import_run_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_product_variants_import_run_id",
        "product_variants",
        "merchant_ingestion_runs",
        ["import_run_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_product_variants_import_run_id", "product_variants", type_="foreignkey"
    )
    op.drop_index(
        op.f("ix_product_variants_import_run_id"), table_name="product_variants"
    )
    op.drop_index(
        op.f("ix_product_variants_source_system"), table_name="product_variants"
    )
    op.drop_column("product_variants", "import_run_id")
    op.drop_column("product_variants", "source_record_id")
    op.drop_column("product_variants", "source_system")
    op.drop_constraint("fk_products_import_run_id", "products", type_="foreignkey")
    op.drop_index(op.f("ix_products_import_run_id"), table_name="products")
    op.drop_index(op.f("ix_products_source_system"), table_name="products")
    op.drop_index(op.f("ix_products_external_id"), table_name="products")
    op.drop_column("products", "import_run_id")
    op.drop_column("products", "source_record_id")
    op.drop_column("products", "source_system")
    op.drop_column("products", "external_id")
    op.drop_column("merchants", "data_mode")
    op.drop_index(
        op.f("ix_merchant_ingestion_runs_status"), table_name="merchant_ingestion_runs"
    )
    op.drop_index(
        op.f("ix_merchant_ingestion_runs_merchant_id"),
        table_name="merchant_ingestion_runs",
    )
    op.drop_table("merchant_ingestion_runs")
