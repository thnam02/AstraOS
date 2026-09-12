"""Merchant domain tables.

Revision ID: 0002_domain_models
Revises: 0001_baseline
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_domain_models"
down_revision: str | Sequence[str] | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "merchants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("brand", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("model_number", sa.String(length=80), nullable=True),
        sa.Column("manufacturer", sa.String(length=160), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_brand", "products", ["brand"])
    op.create_index("ix_products_category", "products", ["category"])
    op.create_index("ix_products_is_active", "products", ["is_active"])

    op.create_table(
        "product_variants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("variant_name", sa.String(length=120), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("base_price_cents", sa.Integer(), nullable=False),
        sa.Column("cogs_cents", sa.Integer(), nullable=False),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("base_price_cents > 0", name="ck_variant_base_price_positive"),
        sa.CheckConstraint("cogs_cents >= 0", name="ck_variant_cogs_nonnegative"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku", name="uq_product_variants_sku"),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])

    op.create_table(
        "inventory_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("units_available", sa.Integer(), nullable=False),
        sa.Column("units_reserved", sa.Integer(), nullable=False),
        sa.Column("warehouse_code", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("units_available >= 0", name="ck_inventory_available_nonnegative"),
        sa.CheckConstraint("units_reserved >= 0", name="ck_inventory_reserved_nonnegative"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("variant_id"),
    )

    op.create_table(
        "delivery_options",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("delivery_days", sa.Integer(), nullable=False),
        sa.Column("merchant_cost_cents", sa.Integer(), nullable=False),
        sa.Column("customer_charge_cents", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("delivery_days >= 0", name="ck_delivery_days_nonnegative"),
        sa.CheckConstraint("merchant_cost_cents >= 0", name="ck_delivery_merchant_cost_nonnegative"),
        sa.CheckConstraint("customer_charge_cents >= 0", name="ck_delivery_customer_charge_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "variant_delivery_options",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("delivery_option_id", sa.Uuid(), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("merchant_cost_override_cents", sa.Integer(), nullable=True),
        sa.Column("customer_charge_override_cents", sa.Integer(), nullable=True),
        sa.Column("cutoff_time", sa.Time(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "merchant_cost_override_cents IS NULL OR merchant_cost_override_cents >= 0",
            name="ck_variant_delivery_merchant_override_nonnegative",
        ),
        sa.CheckConstraint(
            "customer_charge_override_cents IS NULL OR customer_charge_override_cents >= 0",
            name="ck_variant_delivery_customer_override_nonnegative",
        ),
        sa.ForeignKeyConstraint(["delivery_option_id"], ["delivery_options.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("variant_id", "delivery_option_id", name="uq_variant_delivery_option"),
    )
    op.create_index("ix_variant_delivery_options_variant_id", "variant_delivery_options", ["variant_id"])

    op.create_table(
        "warranty_options",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("months", sa.Integer(), nullable=False),
        sa.Column("merchant_cost_cents", sa.Integer(), nullable=False),
        sa.Column("customer_price_cents", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("months > 0", name="ck_warranty_months_positive"),
        sa.CheckConstraint("merchant_cost_cents >= 0", name="ck_warranty_merchant_cost_nonnegative"),
        sa.CheckConstraint("customer_price_cents >= 0", name="ck_warranty_customer_price_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "variant_warranty_options",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("warranty_option_id", sa.Uuid(), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["warranty_option_id"], ["warranty_options.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("variant_id", "warranty_option_id", name="uq_variant_warranty_option"),
    )
    op.create_index("ix_variant_warranty_options_variant_id", "variant_warranty_options", ["variant_id"])

    op.create_table(
        "bundle_options",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("merchant_cost_cents", sa.Integer(), nullable=False),
        sa.Column("customer_price_cents", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("merchant_cost_cents >= 0", name="ck_bundle_merchant_cost_nonnegative"),
        sa.CheckConstraint("customer_price_cents >= 0", name="ck_bundle_customer_price_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "variant_bundle_options",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("bundle_option_id", sa.Uuid(), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["bundle_option_id"], ["bundle_options.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("variant_id", "bundle_option_id", name="uq_variant_bundle_option"),
    )
    op.create_index("ix_variant_bundle_options_variant_id", "variant_bundle_options", ["variant_id"])

    op.create_table(
        "return_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("return_window_days", sa.Integer(), nullable=False),
        sa.Column("restocking_fee_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column("merchant_expected_cost_cents", sa.Integer(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("return_window_days > 0", name="ck_return_window_positive"),
        sa.CheckConstraint(
            "restocking_fee_rate IS NULL OR (restocking_fee_rate >= 0 AND restocking_fee_rate <= 1)",
            name="ck_return_restocking_fee_rate",
        ),
        sa.CheckConstraint(
            "merchant_expected_cost_cents IS NULL OR merchant_expected_cost_cents >= 0",
            name="ck_return_expected_cost_nonnegative",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "variant_return_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("return_policy_id", sa.Uuid(), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["return_policy_id"], ["return_policies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("variant_id", "return_policy_id", name="uq_variant_return_policy"),
    )
    op.create_index("ix_variant_return_policies_variant_id", "variant_return_policies", ["variant_id"])

    op.create_table(
        "merchant_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("merchant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("minimum_margin_rate", sa.Numeric(5, 4), nullable=False),
        sa.Column("maximum_discount_rate", sa.Numeric(5, 4), nullable=False),
        sa.Column("delivery_subsidy_enabled", sa.Boolean(), nullable=False),
        sa.Column("warranty_upgrade_enabled", sa.Boolean(), nullable=False),
        sa.Column("bundle_enabled", sa.Boolean(), nullable=False),
        sa.Column("flexible_returns_enabled", sa.Boolean(), nullable=False),
        sa.Column("loyalty_enabled", sa.Boolean(), nullable=False),
        sa.Column("maximum_delivery_subsidy_cents", sa.Integer(), nullable=True),
        sa.Column("maximum_warranty_subsidy_cents", sa.Integer(), nullable=True),
        sa.Column("maximum_bundle_subsidy_cents", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "minimum_margin_rate >= 0 AND minimum_margin_rate < 1",
            name="ck_policy_minimum_margin_rate",
        ),
        sa.CheckConstraint(
            "maximum_discount_rate >= 0 AND maximum_discount_rate <= 1",
            name="ck_policy_maximum_discount_rate",
        ),
        sa.CheckConstraint(
            "maximum_delivery_subsidy_cents IS NULL OR maximum_delivery_subsidy_cents >= 0",
            name="ck_policy_max_delivery_subsidy",
        ),
        sa.CheckConstraint(
            "maximum_warranty_subsidy_cents IS NULL OR maximum_warranty_subsidy_cents >= 0",
            name="ck_policy_max_warranty_subsidy",
        ),
        sa.CheckConstraint(
            "maximum_bundle_subsidy_cents IS NULL OR maximum_bundle_subsidy_cents >= 0",
            name="ck_policy_max_bundle_subsidy",
        ),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_merchant_policies_merchant_id", "merchant_policies", ["merchant_id"])
    op.create_index("ix_merchant_policies_is_active", "merchant_policies", ["is_active"])

    op.create_table(
        "data_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("reference", sa.String(length=240), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_sources_source_type", "data_sources", ["source_type"])

    op.create_table(
        "attribute_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=True),
        sa.Column("attribute_name", sa.String(length=80), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("source_reference", sa.String(length=240), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attribute_evidence_variant_id", "attribute_evidence", ["variant_id"])
    op.create_index("ix_attribute_evidence_attribute_name", "attribute_evidence", ["attribute_name"])


def downgrade() -> None:
    op.drop_index("ix_attribute_evidence_attribute_name", table_name="attribute_evidence")
    op.drop_index("ix_attribute_evidence_variant_id", table_name="attribute_evidence")
    op.drop_table("attribute_evidence")
    op.drop_index("ix_data_sources_source_type", table_name="data_sources")
    op.drop_table("data_sources")
    op.drop_index("ix_merchant_policies_is_active", table_name="merchant_policies")
    op.drop_index("ix_merchant_policies_merchant_id", table_name="merchant_policies")
    op.drop_table("merchant_policies")
    op.drop_index("ix_variant_return_policies_variant_id", table_name="variant_return_policies")
    op.drop_table("variant_return_policies")
    op.drop_table("return_policies")
    op.drop_index("ix_variant_bundle_options_variant_id", table_name="variant_bundle_options")
    op.drop_table("variant_bundle_options")
    op.drop_table("bundle_options")
    op.drop_index("ix_variant_warranty_options_variant_id", table_name="variant_warranty_options")
    op.drop_table("variant_warranty_options")
    op.drop_table("warranty_options")
    op.drop_index("ix_variant_delivery_options_variant_id", table_name="variant_delivery_options")
    op.drop_table("variant_delivery_options")
    op.drop_table("delivery_options")
    op.drop_table("inventory_records")
    op.drop_index("ix_product_variants_product_id", table_name="product_variants")
    op.drop_table("product_variants")
    op.drop_index("ix_products_is_active", table_name="products")
    op.drop_index("ix_products_category", table_name="products")
    op.drop_index("ix_products_brand", table_name="products")
    op.drop_table("products")
    op.drop_table("merchants")
