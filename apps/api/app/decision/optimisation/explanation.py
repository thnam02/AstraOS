"""Deterministic 'why this offer' reasons. No LLM."""

from app.decision.intent.models import ConstraintField, ShoppingIntent
from app.decision.offers.buyer_constraints import meets_buyer_price
from app.decision.optimisation.counterfactual import best_single_lever
from app.decision.optimisation.models import CounterfactualRow, ScoredOffer
from app.decision.utility.feature_mapping import intent_labels


def explain_recommendation(
    recommended: ScoredOffer,
    *,
    intent: ShoppingIntent,
    margin_floor: float,
    counterfactuals: list[CounterfactualRow],
    frontier: bool,
) -> list[str]:
    reasons: list[str] = []
    if meets_buyer_price(
        intent=intent,
        total_customer_price_cents=recommended.total_customer_price_cents,
        product_price_cents=recommended.product_price_cents,
    ) and recommended.policy.policy_safe:
        reasons.append(
            "Satisfies all mandatory requirements and current merchant policy guardrails."
        )
    if recommended.product_fit >= 0.7:
        reasons.append(
            f"Strong semantic product fit ({recommended.product_fit:.2f}) "
            "for the stated usage context."
        )
    labels = intent_labels(intent)
    hard = {item.field for item in intent.hard_constraints}
    if recommended.delivery_days == 0 and (
        ConstraintField.DELIVERY_DAYS in hard
        or ConstraintField.SAME_DAY_DELIVERY in hard
        or labels & {"long_haul_travel", "frequent_travel", "short_travel"}
    ):
        reasons.append(
            "Same-day delivery aligns with the urgency / travel context."
        )
    reasons.append(
        f"Remains at or above the merchant's {margin_floor:.0%} margin floor "
        f"(contribution rate {recommended.economics.contribution_margin_rate})."
    )
    discount = best_single_lever(counterfactuals, "price")
    if (
        discount is not None
        and recommended.economics.contribution_margin_cents
        > discount.contribution_margin_cents
    ):
        extra = (
            recommended.economics.contribution_margin_cents
            - discount.contribution_margin_cents
        )
        reasons.append(
            f"Preserves A${extra / 100:.2f} more contribution than the strongest "
            "discount-only alternative."
        )
    delivery = next(
        (
            item
            for item in counterfactuals
            if item.lever == "delivery" and item.delivery_code == "SAME_DAY"
        ),
        None,
    )
    if (
        delivery is not None
        and discount is not None
        and delivery.delta_utility >= discount.delta_utility
    ):
        reasons.append(
            "Same-day delivery improves simulated buyer utility more per "
            "dollar of intervention than the strongest discount."
        )
    if frontier:
        reasons.append(
            "Lies on the Pareto-efficient frontier of simulated buyer utility "
            "versus merchant contribution."
        )
    reasons.append(
        "Simulated buyer utility is a transparent cold-start score, "
        "not a win or purchase probability."
    )
    return reasons
