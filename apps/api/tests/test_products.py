"""Product and variant persistence."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, ProductVariant
from tests.factories import make_product, make_variant


@pytest.mark.asyncio
async def test_product_creation(db_session: AsyncSession) -> None:
    product = make_product(name="Helix Air 01")
    db_session.add(product)
    await db_session.flush()
    loaded = await db_session.get(Product, product.id)
    assert loaded is not None
    assert loaded.name == "Helix Air 01"


@pytest.mark.asyncio
async def test_product_has_variants(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id, variant_name="Black")
    db_session.add_all([product, variant])
    await db_session.flush()
    result = await db_session.scalars(
        select(ProductVariant).where(ProductVariant.product_id == product.id)
    )
    assert [row.variant_name for row in result.all()] == ["Black"]


@pytest.mark.asyncio
async def test_sku_unique(db_session: AsyncSession) -> None:
    product = make_product()
    first = make_variant(product.id, sku="HEL-DUP-BLK")
    second = make_variant(product.id, sku="HEL-DUP-BLK")
    db_session.add_all([product, first, second])
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_money_stored_as_cents(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id, base_price_cents=32900, cogs_cents=18000)
    db_session.add_all([product, variant])
    await db_session.flush()
    loaded = await db_session.get(ProductVariant, variant.id)
    assert loaded is not None
    assert loaded.base_price_cents == 32900
    assert loaded.cogs_cents == 18000
    assert isinstance(loaded.base_price_cents, int)


@pytest.mark.asyncio
async def test_attributes_json(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(
        product.id,
        attributes={"anc": True, "battery_hours": 30, "comfort_score": 0.84},
    )
    db_session.add_all([product, variant])
    await db_session.flush()
    loaded = await db_session.get(ProductVariant, variant.id)
    assert loaded is not None
    assert loaded.attributes["anc"] is True
    assert loaded.attributes["battery_hours"] == 30


@pytest.mark.asyncio
async def test_missing_attributes_allowed(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id, attributes={"wireless": True})
    db_session.add_all([product, variant])
    await db_session.flush()
    loaded = await db_session.get(ProductVariant, variant.id)
    assert loaded is not None
    assert "anc" not in loaded.attributes
    assert "battery_hours" not in loaded.attributes


@pytest.mark.asyncio
async def test_base_price_must_be_positive(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id, base_price_cents=0)
    db_session.add_all([product, variant])
    with pytest.raises(IntegrityError):
        await db_session.flush()
