"""Map existing match/offer artefacts into external evidence claims."""

from datetime import UTC, datetime
from typing import Any

from app.agent.schemas import EvidenceClaim
from app.schemas.match import MatchResponse
from app.schemas.optimisation import PublicScoredOffer


def claims_from_match(match: MatchResponse | None) -> list[EvidenceClaim]:
    if match is None or not match.semantic_matching.matches:
        return []
    top = match.semantic_matching.matches[0]
    rows: list[EvidenceClaim] = []
    for reason in top.reasons:
        for fact in reason.facts:
            rows.append(
                EvidenceClaim(
                    claim=fact.attribute,
                    value=fact.value,
                    source_type="PRODUCT_SPECIFICATION",
                    source_reference=fact.source_name,
                    freshness="CURRENT",
                )
            )
    return rows[:12]


def claims_from_offer(
    offer: PublicScoredOffer | dict[str, Any] | None,
) -> list[EvidenceClaim]:
    if offer is None:
        return []
    payload = offer.model_dump() if isinstance(offer, PublicScoredOffer) else offer
    delivery = payload.get("delivery") or {}
    days = delivery.get("days")
    rows: list[EvidenceClaim] = []
    if days is not None:
        rows.append(
            EvidenceClaim(
                claim="same_day_delivery",
                value=int(days) <= 0,
                source_type="FULFILMENT",
                source_reference=delivery.get("code"),
                observed_at=datetime.now(UTC),
                freshness="CURRENT",
            )
        )
        rows.append(
            EvidenceClaim(
                claim="delivery_days",
                value=days,
                source_type="FULFILMENT",
                source_reference=delivery.get("code"),
                freshness="CURRENT",
            )
        )
    warranty = payload.get("warranty") or {}
    if warranty.get("months") is not None:
        rows.append(
            EvidenceClaim(
                claim="warranty_months",
                value=warranty.get("months"),
                source_type="PRODUCT_SPECIFICATION",
                source_reference=warranty.get("code"),
                freshness="CURRENT",
            )
        )
    return rows


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
    return merged
