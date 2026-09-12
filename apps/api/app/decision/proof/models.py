"""Machine-readable proof items. Not commercial scores."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

VerificationStatus = Literal["VERIFIED", "UNVERIFIED", "CONFLICTED", "UNKNOWN"]
FreshnessStatus = Literal["CURRENT", "STALE", "UNKNOWN"]
ProofGroup = Literal[
    "PRODUCT",
    "PRICE",
    "DELIVERY",
    "WARRANTY",
    "BUNDLE",
    "RETURNS",
    "INVENTORY",
]


class ProofItem(BaseModel):
    claim_key: str
    display_claim: str
    value: Any
    unit: str | None = None
    evidence_id: str | None = None
    source_type: str
    source_name: str | None = None
    source_record_id: str | None = None
    verification_status: VerificationStatus
    freshness_status: FreshnessStatus
    observed_at: datetime | None = None
    valid_until: datetime | None = None
    derived: bool = False
    derivation_rule: str | None = None
    group: ProofGroup = "PRODUCT"
    sku: str | None = None
    incomplete: bool = False


class ProofCoverage(BaseModel):
    displayed_claim_count: int = 0
    claims_with_evidence: int = 0
    verified_count: int = 0
    unverified_count: int = 0
    stale_count: int = 0
    conflicted_count: int = 0
    unknown_count: int = 0
    synthetic_count: int = 0
    example_import_count: int = 0
    unsupported_displayed_count: int = 0
    unsupported_displayed_claim_rate: float = 0.0
    hard_constraint_proof_rate: float = 1.0
    commercial_term_proof_rate: float = 1.0
    match_rationale_proof_rate: float = 1.0


class ProofBundle(BaseModel):
    items: list[ProofItem] = Field(default_factory=list)
    coverage: ProofCoverage = Field(default_factory=ProofCoverage)
    issued_at: datetime | None = None


def public_verification(raw: str | None) -> VerificationStatus:
    """Traceability, not independent lab certification.

    VERIFIED means the claim maps to an accepted merchant source record.
    MERCHANT_DECLARED and example-import labels are therefore VERIFIED.
    """
    key = (raw or "").upper()
    if key == "CONFLICTED":
        return "CONFLICTED"
    if key in {"UNKNOWN", ""}:
        return "UNKNOWN"
    if key in {
        "VERIFIED",
        "MERCHANT_DECLARED",
        "EXAMPLE_MERCHANT_IMPORT",
    }:
        return "VERIFIED"
    return "UNVERIFIED"


def source_family(source_type: str | None, source_name: str | None = None) -> str:
    text = f"{source_type or ''} {source_name or ''}".upper()
    if "SYNTHETIC" in text or "FIXTURE" in text:
        return "SYNTHETIC"
    if "EXAMPLE" in text:
        return "EXAMPLE_IMPORT"
    if "INVENT" in text:
        return "INVENTORY"
    if "PRIC" in text:
        return "PRICING"
    if "FULFIL" in text or "DELIVER" in text:
        return "FULFILMENT"
    if "WARRANT" in text:
        return "WARRANTY"
    if "BUNDLE" in text:
        return "BUNDLE"
    if "RETURN" in text:
        return "RETURNS"
    return "PRODUCT_FEED"
