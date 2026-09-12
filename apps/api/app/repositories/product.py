"""Product and variant persistence."""

import uuid
from collections.abc import Sequence
from typing import TypedDict

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    AttributeEvidence,
    InventoryRecord,
    Product,
    ProductVariant,
    VariantBundleOption,
    VariantDeliveryOption,
    VariantReturnPolicy,
    VariantWarrantyOption,
)

_VARIANT_LOAD = (
    selectinload(ProductVariant.inventory),
    selectinload(ProductVariant.delivery_options).selectinload(
        VariantDeliveryOption.delivery_option
    ),
    selectinload(ProductVariant.warranty_options).selectinload(
        VariantWarrantyOption.warranty_option
    ),
    selectinload(ProductVariant.bundle_options).selectinload(
        VariantBundleOption.bundle_option
    ),
    selectinload(ProductVariant.return_policies).selectinload(
        VariantReturnPolicy.return_policy
    ),
    selectinload(ProductVariant.evidence).selectinload(AttributeEvidence.source),
)


class CatalogueCounts(TypedDict):
    products: int
    variants: int
    in_stock_variants: int
    brands: int
    categories: list[str]


class ProductRepository:
    """Read products and variants. No commercial decisions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _product_query(self) -> Select[tuple[Product]]:
        return select(Product).options(
            selectinload(Product.variants).options(*_VARIANT_LOAD)
        )

    async def list_products(
        self,
        *,
        category: str | None = None,
        brand: str | None = None,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[Product], int]:
        filters = []
        if category:
            filters.append(Product.category == category)
        if brand:
            filters.append(Product.brand == brand)
        if active_only:
            filters.append(Product.is_active.is_(True))

        count_stmt = select(func.count()).select_from(Product)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = int(await self.session.scalar(count_stmt) or 0)

        stmt = (
            self._product_query()
            .order_by(Product.brand, Product.name)
            .limit(limit)
            .offset(offset)
        )
        if filters:
            stmt = stmt.where(*filters)
        result = await self.session.scalars(stmt)
        return result.unique().all(), total

    async def get_product(self, product_id: uuid.UUID) -> Product | None:
        stmt = self._product_query().where(Product.id == product_id)
        result = await self.session.scalars(stmt)
        return result.unique().one_or_none()

    async def get_variant_by_sku(self, sku: str) -> ProductVariant | None:
        stmt = (
            select(ProductVariant)
            .options(*_VARIANT_LOAD, selectinload(ProductVariant.product))
            .where(ProductVariant.sku == sku)
        )
        result = await self.session.scalars(stmt)
        return result.unique().one_or_none()

    async def get_variant(self, variant_id: uuid.UUID) -> ProductVariant | None:
        stmt = (
            select(ProductVariant)
            .options(*_VARIANT_LOAD)
            .where(ProductVariant.id == variant_id)
        )
        result = await self.session.scalars(stmt)
        return result.unique().one_or_none()

    async def list_variants_by_ids(
        self, variant_ids: list[uuid.UUID]
    ) -> Sequence[ProductVariant]:
        if not variant_ids:
            return []
        stmt = (
            select(ProductVariant)
            .options(*_VARIANT_LOAD, selectinload(ProductVariant.product))
            .where(ProductVariant.id.in_(variant_ids))
        )
        result = await self.session.scalars(stmt)
        rows = {row.id: row for row in result.unique().all()}
        return [rows[item] for item in variant_ids if item in rows]

    async def list_active_variants(
        self, *, category: str | None = None
    ) -> Sequence[ProductVariant]:
        """All active SKUs in an optional category. MVP full scan is intentional."""
        stmt = (
            select(ProductVariant)
            .join(Product)
            .options(*_VARIANT_LOAD, selectinload(ProductVariant.product))
            .where(
                ProductVariant.is_active.is_(True),
                Product.is_active.is_(True),
            )
            .order_by(Product.brand, Product.name, ProductVariant.sku)
        )
        if category:
            stmt = stmt.where(Product.category == category)
        result = await self.session.scalars(stmt)
        return result.unique().all()

    async def stats(self) -> CatalogueCounts:
        products = int(
            await self.session.scalar(select(func.count()).select_from(Product)) or 0
        )
        variants = int(
            await self.session.scalar(select(func.count()).select_from(ProductVariant))
            or 0
        )
        in_stock = int(
            await self.session.scalar(
                select(func.count())
                .select_from(InventoryRecord)
                .where(InventoryRecord.units_available > InventoryRecord.units_reserved)
            )
            or 0
        )
        brands = int(
            await self.session.scalar(select(func.count(func.distinct(Product.brand))))
            or 0
        )
        category_rows = (
            await self.session.scalars(
                select(Product.category).distinct().order_by(Product.category)
            )
        ).all()
        return {
            "products": products,
            "variants": variants,
            "in_stock_variants": in_stock,
            "brands": brands,
            "categories": [str(row) for row in category_rows],
        }
