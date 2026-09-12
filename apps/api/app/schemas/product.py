"""Product and variant API schemas."""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.bundle import BundleOptionResponse
from app.schemas.delivery import DeliveryOptionResponse
from app.schemas.inventory import InventoryResponse
from app.schemas.provenance import AttributeEvidenceResponse
from app.schemas.returns import ReturnPolicyResponse
from app.schemas.warranty import WarrantyOptionResponse


class VariantSummary(BaseModel):
    """Compact SKU row for catalogue tables."""

    id: uuid.UUID
    sku: str
    variant_name: str | None
    currency: str
    base_price_cents: int
    cogs_cents: int
    units_available: int
    units_reserved: int
    same_day_available: bool
    anc: bool | None
    battery_hours: float | None
    is_active: bool
    has_missing_attributes: bool


class ProductSummary(BaseModel):
    """Product with compact variant rows."""

    id: uuid.UUID
    name: str
    brand: str
    category: str
    model_number: str | None
    is_active: bool
    variant_count: int
    variants: list[VariantSummary]


class ProductListResponse(BaseModel):
    """Paginated product listing."""

    items: list[ProductSummary]
    total: int
    limit: int
    offset: int


class ProductVariantDetail(BaseModel):
    """Full SKU inspection payload."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    sku: str
    variant_name: str | None
    currency: str
    base_price_cents: int
    cogs_cents: int
    attributes: dict[str, Any]
    is_active: bool
    inventory: InventoryResponse | None
    delivery_options: list[DeliveryOptionResponse]
    warranty_options: list[WarrantyOptionResponse]
    bundle_options: list[BundleOptionResponse]
    return_policies: list[ReturnPolicyResponse]
    evidence: list[AttributeEvidenceResponse] = Field(default_factory=list)


class ProductRecord(BaseModel):
    """Conceptual product fields."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    brand: str
    category: str
    description: str | None
    model_number: str | None
    manufacturer: str | None
    is_active: bool


class ProductDetail(BaseModel):
    """Product plus every attached merchant-data surface."""

    product: ProductRecord
    variants: list[ProductVariantDetail]


class CatalogueStatsResponse(BaseModel):
    """Merchant catalogue counters."""

    products: int
    variants: int
    in_stock_variants: int
    out_of_stock_variants: int
    same_day_capable: int
    missing_attribute_variants: int
    brands: int
    categories: list[str]
    evidence_records: int
