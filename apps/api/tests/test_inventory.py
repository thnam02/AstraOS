"""Inventory constraints."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InventoryRecord
from tests.factories import make_inventory, make_product, make_variant


@pytest.mark.asyncio
async def test_inventory_available_nonnegative(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id)
    inventory = make_inventory(variant.id, units_available=-1)
    db_session.add_all([product, variant, inventory])
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_inventory_reserved_nonnegative(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id)
    inventory = make_inventory(variant.id, units_reserved=-1)
    db_session.add_all([product, variant, inventory])
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_out_of_stock_state_can_exist(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id)
    inventory = make_inventory(variant.id, units_available=0, units_reserved=0)
    db_session.add_all([product, variant, inventory])
    await db_session.flush()
    loaded = await db_session.get(InventoryRecord, inventory.id)
    assert loaded is not None
    assert loaded.units_available == 0
