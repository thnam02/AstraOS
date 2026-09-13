"""Presentation-only conceptual baselines. Does not change scoring."""

from datetime import UTC, datetime

from app.decision.offers.bundles import relevant_bundle_codes
from app.decision.offers.constructor import construct_variant
from app.decision.offers.models import ConstructionLimits
from app.decision.optimisation.baseline import (
    conceptual_baselines,
    is_conceptual_baseline,
)
from tests.offer_fixtures import travel_intent, wired_variant


def test_conceptual_baselines_one_per_variant() -> None:
    variant, policy = wired_variant()
    offers, _dims = construct_variant(
        variant=variant,
        intent=travel_intent(),
        policy=policy,
        relevant_bundles=relevant_bundle_codes(travel_intent()),
        limits=ConstructionLimits(),
        expires_at=datetime.now(UTC),
    )
    found = conceptual_baselines(offers)
    assert found
    assert all(is_conceptual_baseline(item) for item in found)
    assert len({item.variant_id for item in found}) == len(found)
    assert found[0].delivery_code == "STANDARD"
    assert found[0].warranty_code == "STANDARD_12"
    assert found[0].bundle_code is None
