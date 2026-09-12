"""Deterministic upsert seeder for merchant data."""

from __future__ import annotations

import argparse
import asyncio
import random
from dataclasses import dataclass
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models import (
    AttributeEvidence,
    InventoryRecord,
    Product,
    ProductVariant,
    VariantDeliveryOption,
)
from app.models.delivery import DeliveryOption
from app.seed.catalog import (
    bundle_options,
    data_sources,
    delivery_options,
    merchant,
    merchant_policy,
    return_policies,
    warranty_options,
)
from app.seed.generator import generate_catalogue
from app.seed.ids import stable_uuid
from app.services.catalogue import CORE_ATTRIBUTES


@dataclass
class SeedSummary:
    """Printed after a successful seed."""

    products: int
    variants: int
    brands: int
    in_stock: int
    out_of_stock: int
    same_day_capable: int
    missing_attribute_variants: int
    evidence_records: int
    minimum_margin_rate: float
    maximum_discount_rate: float


async def _merge_all(session: AsyncSession, rows: list[object]) -> None:
    for row in rows:
        await session.merge(row)


async def seed_database(session: AsyncSession, seed_value: int) -> SeedSummary:
    """Upsert merchant fixtures using stable UUIDs."""
    rng = random.Random(seed_value)
    store = merchant()
    sources = data_sources()
    deliveries = delivery_options()
    warranties = warranty_options()
    bundles = bundle_options()
    returns = return_policies()
    policy = merchant_policy(store.id)

    await _merge_all(
        session, [store, *sources, *deliveries, *warranties, *bundles, *returns, policy]
    )

    catalogue = generate_catalogue(
        rng,
        source_ids={
            "manufacturer_specs": stable_uuid("source", "manufacturer_specs"),
            "merchant_pim": stable_uuid("source", "merchant_pim"),
            "merchant_inventory": stable_uuid("source", "merchant_inventory"),
            "merchant_pricing": stable_uuid("source", "merchant_pricing"),
            "merchant_policy": stable_uuid("source", "merchant_policy"),
            "fulfilment": stable_uuid("source", "fulfilment"),
            "synthetic": stable_uuid("source", "synthetic"),
        },
        delivery_ids={row.code: row.id for row in deliveries},
        warranty_ids={row.code: row.id for row in warranties},
        bundle_ids={row.code: row.id for row in bundles},
        return_ids={row.code: row.id for row in returns},
    )
    await _merge_all(session, list(catalogue.products))
    await _merge_all(session, list(catalogue.variants))
    await _merge_all(session, list(catalogue.inventory))
    await _merge_all(session, list(catalogue.deliveries))
    await _merge_all(session, list(catalogue.warranties))
    await _merge_all(session, list(catalogue.bundles))
    await _merge_all(session, list(catalogue.returns))
    await _merge_all(session, list(catalogue.evidence))
    await session.commit()
    return await summarize(session)


async def summarize(session: AsyncSession) -> SeedSummary:
    """Collect seed totals from the database."""
    products = int(await session.scalar(select(func.count()).select_from(Product)) or 0)
    variants = int(
        await session.scalar(select(func.count()).select_from(ProductVariant)) or 0
    )
    brands = int(
        await session.scalar(select(func.count(func.distinct(Product.brand)))) or 0
    )
    in_stock = int(
        await session.scalar(
            select(func.count())
            .select_from(InventoryRecord)
            .where(InventoryRecord.units_available > InventoryRecord.units_reserved)
        )
        or 0
    )
    same_day = int(
        await session.scalar(
            select(func.count(func.distinct(VariantDeliveryOption.variant_id)))
            .join(DeliveryOption)
            .where(
                DeliveryOption.code == "SAME_DAY",
                VariantDeliveryOption.available.is_(True),
            )
        )
        or 0
    )
    evidence = int(
        await session.scalar(select(func.count()).select_from(AttributeEvidence)) or 0
    )
    missing = 0
    for attributes in (await session.scalars(select(ProductVariant.attributes))).all():
        if any(
            key not in attributes or attributes[key] is None for key in CORE_ATTRIBUTES
        ):
            missing += 1
    return SeedSummary(
        products=products,
        variants=variants,
        brands=brands,
        in_stock=in_stock,
        out_of_stock=max(variants - in_stock, 0),
        same_day_capable=same_day,
        missing_attribute_variants=missing,
        evidence_records=evidence,
        minimum_margin_rate=0.15,
        maximum_discount_rate=0.10,
    )


def format_summary(summary: SeedSummary) -> str:
    """Human-readable seed report."""
    return "\n".join(
        [
            "AstraOS merchant seed complete",
            "",
            f"Products:           {summary.products}",
            f"Variants:           {summary.variants}",
            f"Brands:              {summary.brands}",
            "",
            f"In stock:           {summary.in_stock}",
            f"Out of stock:        {summary.out_of_stock}",
            "",
            f"Same-day capable:   {summary.same_day_capable}",
            "",
            "Variants with",
            f"missing attributes:  {summary.missing_attribute_variants}",
            "",
            f"Evidence records:   {summary.evidence_records}",
            "",
            "Merchant policy:",
            f"minimum margin      {summary.minimum_margin_rate:.0%}",
            f"max discount        {summary.maximum_discount_rate:.0%}",
        ]
    )


def _alembic_config() -> Config:
    ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    return Config(str(ini))


def reset_schema() -> None:
    """Drop domain tables and reapply migrations when a revision exists."""
    config = _alembic_config()
    engine = create_engine(settings.sqlalchemy_database_uri)
    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_revision()
    engine.dispose()
    if current and current != "0001_baseline":
        command.downgrade(config, "0001_baseline")
    command.upgrade(config, "head")


async def run(reset: bool = False) -> SeedSummary:
    """Optionally reset schema, then seed."""
    if reset:
        reset_schema()
    async with AsyncSessionLocal() as session:
        return await seed_database(session, settings.astraos_seed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed AstraOS merchant data.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Downgrade to the Stage 0 baseline, reapply migrations, then seed.",
    )
    args = parser.parse_args()
    summary = asyncio.run(run(reset=args.reset))
    print(format_summary(summary))
