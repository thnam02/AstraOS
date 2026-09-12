"""Bundle costs and variant mappings."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import VariantBundleOption
from tests.factories import make_bundle, make_product, make_variant


@pytest.mark.asyncio
async def test_bundle_costs_nonnegative(db_session: AsyncSession) -> None:
    option = make_bundle(merchant_cost_cents=-1)
    db_session.add(option)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_variant_bundle_mapping(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id)
    option = make_bundle()
    link = VariantBundleOption(
        variant_id=variant.id,
        bundle_option_id=option.id,
        available=True,
    )
    db_session.add_all([product, variant, option, link])
    await db_session.flush()
    rows = (
        await db_session.scalars(
            select(VariantBundleOption).where(
                VariantBundleOption.variant_id == variant.id
            )
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].bundle_option_id == option.id
