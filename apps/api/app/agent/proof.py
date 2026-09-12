"""Map match/offer artefacts into public evidence claims."""

from datetime import UTC, datetime
from typing import Any

from app.agent.schemas import EvidenceClaim
from app.decision.eligibility.snapshot import variant_to_snapshot
from app.decision.proof.compiler import compile_offer_proof
from app.decision.proof.models import ProofBundle, ProofItem
from app.models import ProductVariant
from app.schemas.match import MatchResponse
from app.schemas.optimisation import PublicScoredOffer

_PRIVATE_KEYS = {
    "cogs",
    "cogs_cents",
    "contribution",
    "margin",
    "merchant_cost",
    "buyer_weight",
    "merchant_weight",
}


def claims_from_bundle(
    bundle: dict[str, Any] | ProofBundle | None,
) -> list[EvidenceClaim]:
    if bundle is None:
        return []
    payload = bundle if isinstance(bundle, dict) else bundle.model_dump(mode="json")
    items = [ProofItem.model_validate(item) for item in payload.get("items") or []]
    return proof_items_to_claims(items)


def proof_items_to_claims(items: list[ProofItem]) -> list[EvidenceClaim]:
    rows: list[EvidenceClaim] = []
    for item in items:
        if item.claim_key in _PRIVATE_KEYS or item.incomplete:
            continue
        rows.append(
            EvidenceClaim(
                claim=item.claim_key,
                value=item.value,
                source_type=item.source_type,
                source_reference=item.source_record_id,
                observed_at=item.observed_at,
                freshness=item.freshness_status,
                verification_status=item.verification_status,
                evidence_id=item.evidence_id,
                display_claim=item.display_claim,
                derived=item.derived,
                derivation_rule=item.derivation_rule,
                unit=item.unit,
            )
        )
    return rows


def claims_from_match(match: MatchResponse | None) -> list[EvidenceClaim]:
    if match is None or not match.semantic_matching.matches:
        return []
    top = match.semantic_matching.matches[0]
    rows: list[EvidenceClaim] = []
    for item in top.proof:
        rows.extend(claims_from_bundle({"items": [item]}))
    if rows:
        return rows[:24]
    for reason in top.reasons:
        for fact in reason.facts:
            if not fact.evidence_id and not fact.derived:
                continue
            rows.append(
                EvidenceClaim(
                    claim=fact.attribute,
                    value=fact.value,
                    source_type=fact.source_type or "MERCHANT_PRODUCT_FEED",
                    source_reference=fact.source_record_id or fact.source_name,
                    freshness=fact.freshness or "UNKNOWN",
                    verification_status=fact.verification_status or "UNVERIFIED",
                    evidence_id=fact.evidence_id,
                    derived=fact.derived,
                    derivation_rule=fact.derivation_rule,
                    observed_at=fact.observed_at,
                )
            )
    return rows[:24]


def claims_from_offer(
    offer: PublicScoredOffer | dict[str, Any] | None,
) -> list[EvidenceClaim]:
    if offer is None:
        return []
    payload = (
        offer.model_dump(mode="json")
        if isinstance(offer, PublicScoredOffer)
        else offer
    )
    snapshotted = payload.get("proof_bundle")
    if snapshotted:
        return claims_from_bundle(snapshotted)
    rows: list[EvidenceClaim] = []
    delivery = payload.get("delivery") or {}
    days = delivery.get("days")
    if days is not None:
        rows.append(
            EvidenceClaim(
                claim="same_day_delivery",
                value=int(days) <= 0,
                source_type="FULFILMENT_CONFIGURATION",
                source_reference=delivery.get("code"),
                observed_at=datetime.now(UTC),
                freshness="CURRENT",
                derived=True,
                derivation_rule="selected_delivery_option_v1",
                display_claim=(
                    "Same-day delivery"
                    if int(days) <= 0
                    else "Scheduled delivery"
                ),
            )
        )
        rows.append(
            EvidenceClaim(
                claim="delivery_days",
                value=days,
                source_type="FULFILMENT_CONFIGURATION",
                source_reference=delivery.get("code"),
                freshness="CURRENT",
                derived=True,
                derivation_rule="selected_delivery_option_v1",
            )
        )
    warranty = payload.get("warranty") or {}
    if warranty.get("months") is not None:
        rows.append(
            EvidenceClaim(
                claim="warranty_months",
                value=warranty.get("months"),
                source_type="WARRANTY_POLICY",
                source_reference=warranty.get("code"),
                freshness="CURRENT",
                derived=True,
                derivation_rule="selected_warranty_option_v1",
            )
        )
    pricing = payload.get("pricing") or {}
    if pricing.get("total_price_cents") is not None:
        rows.append(
            EvidenceClaim(
                claim="price",
                value=pricing.get("total_price_cents"),
                source_type="PRICING_FEED",
                source_reference=payload.get("sku"),
                freshness="CURRENT",
                derived=True,
                derivation_rule="variant_list_price_v1",
            )
        )
    return rows


def compile_and_snapshot(
    variant: ProductVariant,
    offer: dict[str, Any],
    match: MatchResponse | None = None,
) -> dict[str, Any]:
    snapshot = variant_to_snapshot(variant)
    top = (
        match.semantic_matching.matches[0]
        if match and match.semantic_matching.matches
        else None
    )
    bundle = compile_offer_proof(snapshot, offer, match=top)
    return bundle.model_dump(mode="json")


_COMMERCIAL_CLAIMS = {
    "price",
    "delivery",
    "warranty",
    "bundle",
    "returns",
    "same_day_delivery",
}


def merge_claims(*groups: list[EvidenceClaim]) -> list[EvidenceClaim]:
    seen: set[str] = set()
    merged: list[EvidenceClaim] = []
    for group in groups:
        for item in group:
            key = f"{item.claim}:{item.value}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    commercial = [item for item in merged if item.claim in _COMMERCIAL_CLAIMS]
    other = [item for item in merged if item.claim not in _COMMERCIAL_CLAIMS]
    return (commercial + other)[:24]
