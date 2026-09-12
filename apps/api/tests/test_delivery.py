"""Delivery option constraints and mappings."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import VariantDeliveryOption
from tests.factories import make_delivery, make_product, make_variant


@pytest.mark.asyncio
async def test_delivery_days_nonnegative(db_session: AsyncSession) -> None:
    option = make_delivery(delivery_days=-1)
    db_session.add(option)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_delivery_cost_nonnegative(db_session: AsyncSession) -> None:
    option = make_delivery(merchant_cost_cents=-10)
    db_session.add(option)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_variant_delivery_uniqueness(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id)
    option = make_delivery()
    first = VariantDeliveryOption(
        variant_id=variant.id,
        delivery_option_id=option.id,
        available=True,
    )
    second = VariantDeliveryOption(
        variant_id=variant.id,
        delivery_option_id=option.id,
        available=False,
    )
    db_session.add_all([product, variant, option, first, second])
    with pytest.raises(IntegrityError):
        await db_session.flush()
