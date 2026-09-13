"""Deterministic baseline offer identity per variant."""

from collections.abc import Iterable

from app.decision.offers.models import OfferCandidate

STANDARD_DELIVERY = "STANDARD"
STANDARD_WARRANTY = "STANDARD_12"
STANDARD_RETURNS = "STANDARD_30"


def is_conceptual_baseline(offer: OfferCandidate) -> bool:
    return (
        offer.price_adjustment_type == "BASE"
        and offer.delivery_code == STANDARD_DELIVERY
        and offer.warranty_code == STANDARD_WARRANTY
        and offer.bundle_code is None
        and (offer.return_policy_code in {None, STANDARD_RETURNS})
    )


def baseline_for_variant(
    offers: Iterable[OfferCandidate], variant_id: object
) -> OfferCandidate | None:
    matches = [
        item
        for item in offers
        if item.variant_id == variant_id and is_conceptual_baseline(item)
    ]
    return matches[0] if matches else None


def conceptual_baselines(offers: Iterable[OfferCandidate]) -> list[OfferCandidate]:
    """One conceptual baseline per variant, for presentation only."""
    found: dict[object, OfferCandidate] = {}
    for item in offers:
        if is_conceptual_baseline(item):
            found[item.variant_id] = item
    return list(found.values())


def lever_family(offer: OfferCandidate, baseline: OfferCandidate) -> str | None:
    """Return the single changed family, or None if 0 or 2+ levers differ."""
    changed: list[str] = []
    if offer.price_adjustment_type != baseline.price_adjustment_type or (
        offer.price_adjustment_rate != baseline.price_adjustment_rate
    ):
        changed.append("price")
    if offer.delivery_code != baseline.delivery_code:
        changed.append("delivery")
    if offer.warranty_code != baseline.warranty_code:
        changed.append("warranty")
    if offer.bundle_code != baseline.bundle_code:
        changed.append("bundle")
    if (offer.return_policy_code or STANDARD_RETURNS) != (
        baseline.return_policy_code or STANDARD_RETURNS
    ):
        changed.append("returns")
    if len(changed) != 1:
        return None
    return changed[0]
