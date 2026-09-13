"""Pure optimisation pipeline. Persistence lives in the service layer."""

import time
from collections import Counter
from uuid import UUID

from app.decision.economics.calculator import compute_economics
from app.decision.intent.models import ConstraintField, ShoppingIntent
from app.decision.offers.buyer_constraints import meets_buyer_price
from app.decision.offers.feasibility import sellable_units as variant_sellable
from app.decision.offers.models import OfferCandidate
from app.decision.optimisation.baseline import is_conceptual_baseline
from app.decision.optimisation.counterfactual import (
    best_single_lever,
    build_counterfactuals,
)
from app.decision.optimisation.explanation import explain_recommendation
from app.decision.optimisation.models import (
    EngineResult,
    MerchantObjectiveSnapshot,
    NamedComparison,
    OptimisationFailure,
    ScoredOffer,
)
from app.decision.optimisation.objective import (
    MerchantObjectiveConfig,
    default_objective,
    explain_objective,
)
from app.decision.optimisation.selection import compare_objectives, select_offer
from app.decision.pareto.dominance import DEFAULT_EPSILON
from app.decision.pareto.frontier import build_frontier
from app.decision.policies.offer_policy_evaluator import evaluate_offer_policy
from app.decision.utility.scorer import score_offer, weights_for
from app.models import MerchantPolicy, ProductVariant


def _units(variant: ProductVariant | None) -> int | None:
    if variant is None:
        return None
    return variant_sellable(variant)


def score_space(
    offers: list[OfferCandidate],
    *,
    intent: ShoppingIntent,
    policy: MerchantPolicy,
    variants: dict[UUID, ProductVariant],
    product_fits: dict[UUID, float],
    profile_id: str,
    alpha: float | None = None,
    objective: MerchantObjectiveConfig | None = None,
    epsilon: float = DEFAULT_EPSILON,
) -> EngineResult:
    weights = weights_for(intent, profile_id)
    baselines = {
        item.variant_id: item
        for item in offers
        if is_conceptual_baseline(item)
    }
    economics_started = time.perf_counter()
    economics_by_id = {}
    for offer in offers:
        variant = variants.get(offer.variant_id)
        baseline = baselines.get(offer.variant_id)
        economics_by_id[offer.id] = compute_economics(
            offer,
            cogs_cents=int(variant.cogs_cents) if variant is not None else 0,
            baseline_product_price_cents=offer.base_price_cents,
            baseline_delivery_cost_cents=(
                baseline.delivery_merchant_cost_cents if baseline else 0
            ),
            baseline_warranty_cost_cents=(
                baseline.warranty_merchant_cost_cents if baseline else 0
            ),
            baseline_bundle_cost_cents=0,
            baseline_return_cost_cents=(
                int(baseline.return_policy_expected_cost_cents or 0) if baseline else 0
            ),
        )
    economics_ms = (time.perf_counter() - economics_started) * 1000

    policy_started = time.perf_counter()
    evaluations = {}
    for offer in offers:
        variant = variants.get(offer.variant_id)
        active = True
        if variant is not None:
            active = bool(variant.is_active and variant.product.is_active)
        evaluations[offer.id] = evaluate_offer_policy(
            offer,
            economics=economics_by_id[offer.id],
            policy=policy,
            intent=intent,
            sellable_units=_units(variant),
            product_active=active,
        )
    policy_ms = (time.perf_counter() - policy_started) * 1000

    safe_ids = {item.id for item in offers if evaluations[item.id].policy_safe}
    safe_prices = [
        item.total_customer_price_cents for item in offers if item.id in safe_ids
    ]
    if safe_prices:
        price_low, price_high = min(safe_prices), max(safe_prices)
    else:
        all_prices = [item.total_customer_price_cents for item in offers] or [0]
        price_low, price_high = min(all_prices), max(all_prices)

    utility_started = time.perf_counter()
    scored: list[ScoredOffer] = []
    for offer in offers:
        baseline = baselines.get(offer.variant_id)
        utility = score_offer(
            offer,
            intent=intent,
            product_fit=product_fits.get(offer.variant_id, 0.0),
            price_low=price_low,
            price_high=price_high,
            weights=weights,
            profile_id=profile_id,
        )
        scored.append(
            ScoredOffer(
                offer_id=offer.id,
                variant_id=offer.variant_id,
                sku=offer.sku,
                product_name=offer.product_name,
                brand=offer.brand,
                product_price_cents=offer.final_product_price_cents,
                total_customer_price_cents=offer.total_customer_price_cents,
                currency=offer.currency,
                delivery_code=offer.delivery_code,
                delivery_name=offer.delivery_name,
                delivery_days=offer.delivery_days,
                warranty_code=offer.warranty_code,
                warranty_name=offer.warranty_name,
                warranty_months=offer.warranty_months,
                bundle_code=offer.bundle_code,
                bundle_name=offer.bundle_name,
                return_policy_code=offer.return_policy_code,
                return_window_days=offer.return_window_days,
                economics=economics_by_id[offer.id],
                policy=evaluations[offer.id],
                utility=utility,
                is_baseline=is_conceptual_baseline(offer),
                baseline_offer_id=baseline.id if baseline else None,
                product_fit=product_fits.get(offer.variant_id, 0.0),
            )
        )
    utility_ms = (time.perf_counter() - utility_started) * 1000

    safe = [
        item
        for item in scored
        if item.policy.policy_safe
        and meets_buyer_price(
            intent=intent,
            total_customer_price_cents=item.total_customer_price_cents,
            product_price_cents=item.product_price_cents,
        )
    ]
    pareto_started = time.perf_counter()
    frontier_result = build_frontier(
        [item.offer_id for item in safe],
        [item.utility.score for item in safe],
        [item.economics.contribution_margin_cents for item in safe],
        epsilon=epsilon,
    )
    efficient_ids = set(frontier_result.efficient_offer_ids)
    for item in scored:
        item.is_pareto_efficient = item.offer_id in efficient_ids
        dominated = frontier_result.dominated_by.get(str(item.offer_id))
        item.dominated_by_offer_id = dominated
    pareto_ms = (time.perf_counter() - pareto_started) * 1000

    frontier = [item for item in scored if item.is_pareto_efficient]
    selection_started = time.perf_counter()
    chosen = objective
    if chosen is None and alpha is None:
        chosen = default_objective()
    recommended, selection = select_offer(
        frontier, alpha=alpha, objective=chosen
    )
    if recommended is not None:
        for item in scored:
            item.is_recommended = item.offer_id == recommended.offer_id
        recommended.is_recommended = True
    selection_ms = (time.perf_counter() - selection_started) * 1000

    cf_started = time.perf_counter()
    focus_variant = (
        recommended.variant_id
        if recommended is not None
        else (
            safe[0].variant_id
            if safe
            else (scored[0].variant_id if scored else None)
        )
    )
    baseline_scored = next(
        (
            item
            for item in scored
            if item.variant_id == focus_variant and item.is_baseline
        ),
        None,
    )
    counterfactuals = build_counterfactuals(
        scored, variant_id=focus_variant, baseline=baseline_scored
    )

    comparisons: list[NamedComparison] = []
    if baseline_scored is not None:
        comparisons.append(
            NamedComparison(
                role="BASE_OFFER",
                offer_id=baseline_scored.offer_id,
                label="Baseline",
                buyer_utility=baseline_scored.utility.score,
                contribution_margin_cents=baseline_scored.economics.contribution_margin_cents,
                policy_safe=baseline_scored.policy.policy_safe,
            )
        )
    for role, family in (
        ("BEST_DISCOUNT_ONLY", "price"),
        ("BEST_DELIVERY_ONLY", "delivery"),
        ("BEST_WARRANTY_ONLY", "warranty"),
        ("BEST_BUNDLE_ONLY", "bundle"),
    ):
        row = best_single_lever(counterfactuals, family)
        comparisons.append(
            NamedComparison(
                role=role,
                offer_id=row.offer_id if row else None,
                label=row.label if row else family,
                buyer_utility=row.buyer_utility if row else None,
                contribution_margin_cents=(
                    row.contribution_margin_cents if row else None
                ),
                policy_safe=bool(row and row.policy_safe),
            )
        )
    if recommended is not None:
        comparisons.append(
            NamedComparison(
                role="ASTRAOS_RECOMMENDED",
                offer_id=recommended.offer_id,
                label=recommended.product_name,
                buyer_utility=recommended.utility.score,
                contribution_margin_cents=recommended.economics.contribution_margin_cents,
                policy_safe=True,
            )
        )

    failure = None
    if recommended is None:
        rejected = Counter(
            item.policy.rejection_codes[0]
            for item in scored
            if item.policy.rejection_codes
        )
        budget = None
        for constraint in intent.hard_constraints:
            if constraint.field == ConstraintField.PRICE:
                value = constraint.normalized_value or constraint.value
                if isinstance(value, int):
                    budget = value
        constructed_prices = [item.total_customer_price_cents for item in scored]
        failure = OptimisationFailure(
            code="NO_POLICY_SAFE_OFFER",
            message=(
                "No constructed offer clears current merchant policy. "
                "AstraOS will not invent a deal."
            ),
            requested_max_price_cents=budget,
            lowest_constructed_price_cents=(
                min(constructed_prices) if constructed_prices else None
            ),
            rejection_distribution=dict(rejected),
        )

    reasons = []
    if recommended is not None:
        used = chosen or default_objective()
        reasons = [
            explain_objective(used),
            *explain_recommendation(
                recommended,
                intent=intent,
                margin_floor=float(policy.minimum_margin_rate),
                counterfactuals=counterfactuals,
                frontier=True,
            ),
        ]
    counterfactual_ms = (time.perf_counter() - cf_started) * 1000
    return EngineResult(
        scored=scored,
        frontier=frontier,
        recommended=recommended,
        selection=selection,
        counterfactuals=counterfactuals,
        comparisons=comparisons,
        failure=failure,
        explanation=reasons,
        timing={
            "economics_ms": round(economics_ms, 2),
            "policy_filter_ms": round(policy_ms, 2),
            "utility_ms": round(utility_ms, 2),
            "pareto_ms": round(pareto_ms, 2),
            "selection_ms": round(selection_ms, 2),
            "counterfactual_ms": round(counterfactual_ms, 2),
        },
        merchant_objective=MerchantObjectiveSnapshot.model_validate(
            (chosen or default_objective()).snapshot()
        ),
        objective_comparisons=compare_objectives(frontier),
    )


def apply_experimental_buyer_objective(
    result: EngineResult,
    buyer_objective: dict[UUID, float],
    *,
    alpha: float | None = None,
    objective: MerchantObjectiveConfig | None = None,
    epsilon: float = DEFAULT_EPSILON,
) -> EngineResult:
    """Rebuild Pareto using learned scores. Cold-start utility traces stay."""
    safe = [item for item in result.scored if item.policy.policy_safe]
    objectives = [
        buyer_objective.get(item.offer_id, item.utility.score) for item in safe
    ]
    frontier_result = build_frontier(
        [item.offer_id for item in safe],
        objectives,
        [item.economics.contribution_margin_cents for item in safe],
        epsilon=epsilon,
    )
    efficient_ids = set(frontier_result.efficient_offer_ids)
    for item in result.scored:
        item.is_pareto_efficient = item.offer_id in efficient_ids
        dominated = frontier_result.dominated_by.get(str(item.offer_id))
        item.dominated_by_offer_id = dominated
        item.is_recommended = False
    frontier = [item for item in result.scored if item.is_pareto_efficient]
    chosen = objective
    if chosen is None and alpha is None:
        chosen = default_objective()
    recommended, selection = select_offer(
        frontier,
        alpha=alpha,
        objective=chosen,
        buyer_objective=buyer_objective,
    )
    if recommended is not None:
        recommended.is_recommended = True
        for item in result.scored:
            item.is_recommended = item.offer_id == recommended.offer_id
    result.frontier = frontier
    result.recommended = recommended
    result.selection = selection
    result.merchant_objective = MerchantObjectiveSnapshot.model_validate(
        (chosen or default_objective()).snapshot()
    )
    result.objective_comparisons = compare_objectives(frontier)
    return result
