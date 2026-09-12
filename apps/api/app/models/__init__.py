"""SQLAlchemy domain models for merchant catalogue data."""

from app.db.base import Base
from app.models.bundle import BundleOption, VariantBundleOption
from app.models.delivery import DeliveryOption, VariantDeliveryOption
from app.models.inventory import InventoryRecord
from app.models.merchant import Merchant
from app.models.policy import MerchantPolicy
from app.models.product import Product, ProductVariant
from app.models.provenance import AttributeEvidence, DataSource
from app.models.returns import ReturnPolicy, VariantReturnPolicy
from app.models.warranty import VariantWarrantyOption, WarrantyOption

__all__ = [
    "AttributeEvidence",
    "Base",
    "BundleOption",
    "DataSource",
    "DeliveryOption",
    "InventoryRecord",
    "Merchant",
    "MerchantPolicy",
    "Product",
    "ProductVariant",
    "ReturnPolicy",
    "VariantBundleOption",
    "VariantDeliveryOption",
    "VariantReturnPolicy",
    "VariantWarrantyOption",
    "WarrantyOption",
]
