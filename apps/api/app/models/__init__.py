"""SQLAlchemy domain models for merchant catalogue data."""

from app.db.base import Base
from app.models.bundle import BundleOption, VariantBundleOption
from app.models.delivery import DeliveryOption, VariantDeliveryOption
from app.models.embedding import VariantEmbedding
from app.models.inventory import InventoryRecord
from app.models.match import MatchResult, MatchRun
from app.models.merchant import Merchant
from app.models.offer import OfferCandidateRow, OfferConstructionRun
from app.models.optimisation import OptimisationRun
from app.models.policy import MerchantPolicy
from app.models.product import Product, ProductVariant
from app.models.provenance import AttributeEvidence, DataSource
from app.models.qualification import QualificationRun, QualificationVariantResult
from app.models.returns import ReturnPolicy, VariantReturnPolicy
from app.models.warranty import VariantWarrantyOption, WarrantyOption

__all__ = [
    "AttributeEvidence",
    "Base",
    "BundleOption",
    "DataSource",
    "DeliveryOption",
    "InventoryRecord",
    "MatchResult",
    "MatchRun",
    "Merchant",
    "OfferCandidateRow",
    "OfferConstructionRun",
    "OptimisationRun",
    "MerchantPolicy",
    "Product",
    "ProductVariant",
    "QualificationRun",
    "QualificationVariantResult",
    "ReturnPolicy",
    "VariantBundleOption",
    "VariantDeliveryOption",
    "VariantEmbedding",
    "VariantReturnPolicy",
    "VariantWarrantyOption",
    "WarrantyOption",
]
