"""Warranty constraints and mappings."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import VariantWarrantyOption
from tests.factories import make_product, make_variant, make_warranty


@pytest.mark.asyncio
async def test_warranty_months_positive(db_session: AsyncSession) -> None:
    option = make_warranty(months=0)
    db_session.add(option)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_variant_warranty_mapping(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id)
    option = make_warranty(months=24)
    link = VariantWarrantyOption(
        variant_id=variant.id,
        warranty_option_id=option.id,
        available=True,
    )
    db_session.add_all([product, variant, option, link])
    await db_session.flush()
    rows = (
        await db_session.scalars(
            select(VariantWarrantyOption).where(
                VariantWarrantyOption.variant_id == variant.id
            )
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].available is True
