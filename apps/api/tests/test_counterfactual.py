"""Single-lever counterfactuals from a conceptual baseline."""

from datetime import UTC, datetime

from app.decision.offers.bundles import relevant_bundle_codes
from app.decision.offers.constructor import construct_variant
from app.decision.offers.models import ConstructionLimits
from app.decision.optimisation.baseline import is_conceptual_baseline, lever_family
from app.decision.optimisation.counterfactual import (
    best_single_lever,
    build_counterfactuals,
)
from app.decision.optimisation.engine import score_space
from tests.offer_fixtures import travel_intent, wired_variant


def _space():
    variant, policy = wired_variant()
    intent = travel_intent()
    offers, _dims = construct_variant(
        variant=variant,
        intent=intent,
        policy=policy,
        relevant_bundles=relevant_bundle_codes(intent),
        limits=ConstructionLimits(),
        expires_at=datetime.now(UTC),
    )
    result = score_space(
        offers,
        intent=intent,
        policy=policy,
        variants={variant.id: variant},
        product_fits={variant.id: 0.88},
        profile_id="INTENT_ADAPTED",
    )
    return offers, result, variant


def test_baseline_identity() -> None:
    offers, result, _variant = _space()
    bases = [item for item in offers if is_conceptual_baseline(item)]
    assert len(bases) == 1
    scored = next(item for item in result.scored if item.offer_id == bases[0].id)
    assert scored.is_baseline


def test_single_lever_changes() -> None:
    offers, _result, _variant = _space()
    baseline = next(item for item in offers if is_conceptual_baseline(item))
    families = {
        lever_family(item, baseline)
        for item in offers
        if lever_family(item, baseline)
    }
    assert {"price", "delivery", "warranty", "bundle", "returns"} <= families


def test_counterfactual_deltas() -> None:
    _offers, result, variant = _space()
    baseline = next(item for item in result.scored if item.is_baseline)
    rows = build_counterfactuals(
        result.scored, variant_id=variant.id, baseline=baseline
    )
    assert rows[0].lever == "baseline"
    assert rows[0].delta_utility == 0
    same_day = next(
        item
        for item in rows
        if item.delivery_code == "SAME_DAY" and item.lever == "delivery"
    )
    discount = best_single_lever(rows, "price")
    assert (
        same_day.delta_utility != 0
        or same_day.incremental_intervention_cost_cents > 0
    )
    if discount:
        assert discount.incremental_intervention_cost_cents >= 0


def test_recommended_on_frontier() -> None:
    _offers, result, _variant = _space()
    assert result.recommended is not None
    assert result.recommended.is_pareto_efficient
    assert result.recommended.policy.policy_safe
    unsafe = [item for item in result.scored if not item.policy.policy_safe]
    assert all(not item.is_pareto_efficient for item in unsafe)
