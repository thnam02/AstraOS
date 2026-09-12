"""Seed completeness and idempotency."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AttributeEvidence, InventoryRecord, Product, ProductVariant
from app.models.delivery import DeliveryOption, VariantDeliveryOption
from app.seed.runner import seed_database
from app.services.catalogue import CORE_ATTRIBUTES


@pytest.mark.asyncio
async def test_seeding_succeeds(db_session: AsyncSession) -> None:
    products = await db_session.scalar(select(func.count()).select_from(Product))
    variants = await db_session.scalar(select(func.count()).select_from(ProductVariant))
    assert products and products >= 100
    assert variants and variants >= 300


@pytest.mark.asyncio
async def test_seed_is_idempotent(db_session: AsyncSession) -> None:
    before_products = await db_session.scalar(select(func.count()).select_from(Product))
    before_variants = await db_session.scalar(
        select(func.count()).select_from(ProductVariant)
    )
    await seed_database(db_session, 2026)
    after_products = await db_session.scalar(select(func.count()).select_from(Product))
    after_variants = await db_session.scalar(
        select(func.count()).select_from(ProductVariant)
    )
    assert after_products == before_products
    assert after_variants == before_variants


@pytest.mark.asyncio
async def test_seed_has_missing_attributes(db_session: AsyncSession) -> None:
    attributes = (await db_session.scalars(select(ProductVariant.attributes))).all()
    missing = [
        row
        for row in attributes
        if any(key not in row or row[key] is None for key in CORE_ATTRIBUTES)
    ]
    assert missing


@pytest.mark.asyncio
async def test_seed_has_out_of_stock(db_session: AsyncSession) -> None:
    count = await db_session.scalar(
        select(func.count())
        .select_from(InventoryRecord)
        .where(InventoryRecord.units_available == 0)
    )
    assert count and count > 0


@pytest.mark.asyncio
async def test_seed_has_same_day(db_session: AsyncSession) -> None:
    count = await db_session.scalar(
        select(func.count(func.distinct(VariantDeliveryOption.variant_id)))
        .join(DeliveryOption)
        .where(
            DeliveryOption.code == "SAME_DAY", VariantDeliveryOption.available.is_(True)
        )
    )
    assert count and count > 0


@pytest.mark.asyncio
async def test_seed_has_provenance(db_session: AsyncSession) -> None:
    count = await db_session.scalar(select(func.count()).select_from(AttributeEvidence))
    assert count and count >= 2500


@pytest.mark.asyncio
async def test_seed_has_stale_evidence(db_session: AsyncSession) -> None:
    count = await db_session.scalar(
        select(func.count())
        .select_from(AttributeEvidence)
        .where(AttributeEvidence.expires_at < datetime.now(UTC))
    )
    assert count and count > 0


@pytest.mark.asyncio
async def test_seed_brand_count(db_session: AsyncSession) -> None:
    brands = await db_session.scalar(select(func.count(func.distinct(Product.brand))))
    assert brands == 12
