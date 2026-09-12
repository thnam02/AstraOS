"""Pydantic request and response schemas."""

from app.schemas.bundle import BundleOptionResponse
from app.schemas.delivery import DeliveryOptionResponse
from app.schemas.health import HealthResponse
from app.schemas.intent import QualifyRequest, QualifyResponse
from app.schemas.inventory import InventoryResponse
from app.schemas.match import (
    AnalyseRequest,
    AnalyseResponse,
    MatchRequest,
    MatchResponse,
)
from app.schemas.merchant import MerchantPolicyResponse, MerchantPolicyUpdate
from app.schemas.offer import GenerateOffersRequest, GenerateOffersResponse
from app.schemas.product import (
    CatalogueStatsResponse,
    ProductDetail,
    ProductListResponse,
    ProductVariantDetail,
)
from app.schemas.provenance import AttributeEvidenceResponse
from app.schemas.returns import ReturnPolicyResponse
from app.schemas.warranty import WarrantyOptionResponse

__all__ = [
    "AnalyseRequest",
    "AnalyseResponse",
    "AttributeEvidenceResponse",
    "BundleOptionResponse",
    "CatalogueStatsResponse",
    "DeliveryOptionResponse",
    "HealthResponse",
    "InventoryResponse",
    "MatchRequest",
    "MatchResponse",
    "GenerateOffersRequest",
    "GenerateOffersResponse",
    "MerchantPolicyResponse",
    "MerchantPolicyUpdate",
    "ProductDetail",
    "ProductListResponse",
    "ProductVariantDetail",
    "QualifyRequest",
    "QualifyResponse",
    "ReturnPolicyResponse",
    "WarrantyOptionResponse",
]
