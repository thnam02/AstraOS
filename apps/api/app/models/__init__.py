"""SQLAlchemy domain models for merchant catalogue data."""

from app.db.base import Base
from app.models.arena import (
    ArenaBenchmarkRun,
    ArenaRun,
    ArenaSegmentMetrics,
    ArenaStrategyMetrics,
)
from app.models.bundle import BundleOption, VariantBundleOption
from app.models.commerce import (
    CommerceTransaction,
    InventoryReservation,
    Order,
    OrderNumberSequence,
)
from app.models.delivery import DeliveryOption, VariantDeliveryOption
from app.models.embedding import VariantEmbedding
from app.models.ingestion import MerchantIngestionRun
from app.models.inventory import InventoryRecord
from app.models.learning import (
    CommerceInteraction,
    LearningDatasetVersion,
    ModelTrainingRun,
    ResponseModelVersion,
)
from app.models.match import MatchResult, MatchRun
from app.models.merchant import Merchant
from app.models.negotiation import (
    MerchantProposal,
    NegotiationSession,
    NegotiationTurn,
)
from app.models.objective import MerchantObjective
from app.models.offer import OfferCandidateRow, OfferConstructionRun
from app.models.optimisation import OptimisationRun
from app.models.policy import MerchantPolicy
from app.models.product import Product, ProductVariant
from app.models.provenance import AttributeEvidence, DataSource
from app.models.qualification import QualificationRun, QualificationVariantResult
from app.models.returns import ReturnPolicy, VariantReturnPolicy
from app.models.warranty import VariantWarrantyOption, WarrantyOption

__all__ = [
    "ArenaBenchmarkRun",
    "ArenaRun",
    "ArenaSegmentMetrics",
    "ArenaStrategyMetrics",
    "AttributeEvidence",
    "Base",
    "BundleOption",
    "CommerceInteraction",
    "CommerceTransaction",
    "DataSource",
    "DeliveryOption",
    "InventoryRecord",
    "MerchantIngestionRun",
    "InventoryReservation",
    "LearningDatasetVersion",
    "MatchResult",
    "MatchRun",
    "Merchant",
    "MerchantObjective",
    "MerchantProposal",
    "ModelTrainingRun",
    "NegotiationSession",
    "NegotiationTurn",
    "OfferCandidateRow",
    "OfferConstructionRun",
    "OptimisationRun",
    "Order",
    "OrderNumberSequence",
    "MerchantPolicy",
    "Product",
    "ProductVariant",
    "QualificationRun",
    "QualificationVariantResult",
    "ResponseModelVersion",
    "ReturnPolicy",
    "VariantBundleOption",
    "VariantDeliveryOption",
    "VariantEmbedding",
    "VariantReturnPolicy",
    "VariantWarrantyOption",
    "WarrantyOption",
]
