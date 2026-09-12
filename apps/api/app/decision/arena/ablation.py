"""Deterministic Arena ablation analysis. No LLM. No formula changes."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.decision.arena.models import (
    ArenaMissionResult,
    StrategyMetrics,
    StrategyResponse,
)

OUTSIDE_DEFAULT = 0.42


def _by_name(result: ArenaMissionResult, name: str) -> StrategyResponse | None:
    return next(
        (item for item in result.responses if item.strategy_name == name),
        None,
    )


def _valid(row: StrategyResponse | None) -> bool:
    return bool(
        row
        and row.offer_id
        and row.policy_safe
        and row.hard_constraints_satisfied
        and row.buyer_utility is not None
    )


def _metric(metrics: list[StrategyMetrics], name: str) -> StrategyMetrics | None:
    return next((item for item in metrics if item.strategy_name == name), None)


def incremental_deltas(metrics: list[StrategyMetrics]) -> list[dict[str, Any]]:
    pairs = (
        ("discount_value", "DEFAULT", "ALWAYS_DISCOUNT"),
        ("semantic_value", "DEFAULT", "SEMANTIC_ONLY"),
        ("full_astraos_value", "SEMANTIC_ONLY", "ASTRAOS"),
    )
    rows: list[dict[str, Any]] = []
    for name, left, right in pairs:
        a = _metric(metrics, left)
        b = _metric(metrics, right)
        if a is None or b is None:
            continue
        rows.append(
            {
                "name": name,
                "from_strategy": left,
                "to_strategy": right,
                "selection_rate": round(b.selection_rate - a.selection_rate, 6),
                "contribution_per_opportunity_cents": round(
                    b.contribution_per_opportunity_cents
                    - a.contribution_per_opportunity_cents,
                    4,
                ),
                "avg_buyer_utility": _delta(
                    a.avg_buyer_utility, b.avg_buyer_utility
                ),
                "avg_intervention_cost_cents": _delta(
                    a.avg_intervention_cost_cents, b.avg_intervention_cost_cents
                ),
            }
        )
    return rows


def _delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return round(right - left, 6)


def classify_commercial_change(
    left: StrategyResponse, right: StrategyResponse
) -> str:
    changed: list[str] = []
    if left.sku != right.sku:
        changed.append("PRODUCT_SUBSTITUTION")
    if left.total_customer_price_cents != right.total_customer_price_cents:
        changed.append("PRICE")
    if left.delivery != right.delivery or left.delivery_days != right.delivery_days:
        changed.append("DELIVERY")
    if left.warranty != right.warranty or left.warranty_months != right.warranty_months:
        changed.append("WARRANTY")
    if (left.bundle or None) != (right.bundle or None):
        changed.append("BUNDLE")
    if (left.returns or None) != (right.returns or None):
        changed.append("RETURNS")
    if not changed:
        return "NONE"
    if len(changed) == 1:
        return changed[0]
    return "MULTIPLE"


def astraos_vs_semantic(
    results: list[ArenaMissionResult],
    *,
    outside_option_utility: float = OUTSIDE_DEFAULT,
) -> dict[str, Any]:
    both = 0
    astraos_pref = 0
    semantic_pref = 0
    ties = 0
    neither = 0
    contrib_deltas: list[float] = []
    utility_deltas: list[float] = []
    classes: Counter[str] = Counter()
    for result in results:
        semantic = _by_name(result, "SEMANTIC_ONLY")
        astraos = _by_name(result, "ASTRAOS")
        if not _valid(semantic) or not _valid(astraos):
            continue
        both += 1
        assert semantic.buyer_utility is not None
        assert astraos.buyer_utility is not None
        su = semantic.buyer_utility
        au = astraos.buyer_utility
        if au < outside_option_utility and su < outside_option_utility:
            neither += 1
        elif au > su:
            astraos_pref += 1
            if (
                astraos.merchant_contribution_cents is not None
                and semantic.merchant_contribution_cents is not None
            ):
                contrib_deltas.append(
                    float(astraos.merchant_contribution_cents)
                    - float(semantic.merchant_contribution_cents)
                )
            utility_deltas.append(au - su)
        elif su > au:
            semantic_pref += 1
        else:
            ties += 1
        classes[classify_commercial_change(semantic, astraos)] += 1
    denom = both or 1
    return {
        "both_valid": both,
        "astraos_preferred": astraos_pref,
        "semantic_preferred": semantic_pref,
        "tie": ties,
        "neither_outside_option": neither,
        "astraos_preferred_pct": round(astraos_pref / denom, 6),
        "semantic_preferred_pct": round(semantic_pref / denom, 6),
        "tie_pct": round(ties / denom, 6),
        "neither_pct": round(neither / denom, 6),
        "avg_contribution_delta_when_astraos_preferred": (
            round(sum(contrib_deltas) / len(contrib_deltas), 4)
            if contrib_deltas
            else None
        ),
        "avg_utility_delta_when_astraos_preferred": (
            round(sum(utility_deltas) / len(utility_deltas), 6)
            if utility_deltas
            else None
        ),
        "change_classifications": dict(classes),
        "denominator": "missions_where_both_valid",
    }


def intervention_attribution(
    results: list[ArenaMissionResult],
    *,
    outside_option_utility: float = OUTSIDE_DEFAULT,
) -> dict[str, Any]:
    """Levers that differ when AstraOS is preferred over Semantic Only."""
    wins = 0
    counts = Counter(
        {
            "price": 0,
            "delivery": 0,
            "warranty": 0,
            "bundle": 0,
            "returns": 0,
            "product": 0,
            "multi_lever": 0,
        }
    )
    for result in results:
        semantic = _by_name(result, "SEMANTIC_ONLY")
        astraos = _by_name(result, "ASTRAOS")
        if not _valid(semantic) or not _valid(astraos):
            continue
        assert semantic.buyer_utility is not None
        assert astraos.buyer_utility is not None
        if astraos.buyer_utility <= semantic.buyer_utility:
            continue
        if astraos.buyer_utility < outside_option_utility:
            continue
        wins += 1
        levers: list[str] = []
        if semantic.sku != astraos.sku:
            levers.append("product")
        if semantic.total_customer_price_cents != astraos.total_customer_price_cents:
            levers.append("price")
        if (
            semantic.delivery != astraos.delivery
            or semantic.delivery_days != astraos.delivery_days
        ):
            levers.append("delivery")
        if (
            semantic.warranty != astraos.warranty
            or semantic.warranty_months != astraos.warranty_months
        ):
            levers.append("warranty")
        if (semantic.bundle or None) != (astraos.bundle or None):
            levers.append("bundle")
        if (semantic.returns or None) != (astraos.returns or None):
            levers.append("returns")
        for lever in levers:
            counts[lever] += 1
        if len(levers) > 1:
            counts["multi_lever"] += 1
    denom = wins or 1
    return {
        "astraos_preferred_over_semantic": wins,
        "pct_involving_price": round(counts["price"] / denom, 6),
        "pct_involving_delivery": round(counts["delivery"] / denom, 6),
        "pct_involving_warranty": round(counts["warranty"] / denom, 6),
        "pct_involving_bundle": round(counts["bundle"] / denom, 6),
        "pct_involving_returns": round(counts["returns"] / denom, 6),
        "pct_involving_product": round(counts["product"] / denom, 6),
        "pct_multi_lever": round(counts["multi_lever"] / denom, 6),
        "counts": dict(counts),
    }


def win_category(
    winner: StrategyResponse | None,
    semantic: StrategyResponse | None,
    default: StrategyResponse | None,
    _discount: StrategyResponse | None,
) -> str | None:
    if winner is None or winner.strategy_name != "ASTRAOS":
        return None
    baseline = semantic or default
    if baseline is None:
        return "BETTER_MULTI_DIMENSIONAL_TRADEOFF"
    if winner.sku != baseline.sku:
        return "HIGHER_PRODUCT_FIT"
    days_w = winner.delivery_days if winner.delivery_days is not None else 99
    days_b = baseline.delivery_days if baseline.delivery_days is not None else 99
    if days_w < days_b:
        return "FASTER_DELIVERY"
    if (winner.warranty_months or 0) > (baseline.warranty_months or 0):
        return "BETTER_ASSURANCE"
    if winner.bundle and not baseline.bundle:
        return "BETTER_BUNDLE"
    if (
        winner.total_customer_price_cents is not None
        and baseline.total_customer_price_cents is not None
        and winner.total_customer_price_cents < baseline.total_customer_price_cents
    ):
        return "LOWER_PRICE"
    if (
        winner.merchant_contribution_cents is not None
        and baseline.merchant_contribution_cents is not None
        and winner.merchant_contribution_cents > baseline.merchant_contribution_cents
    ):
        return "MARGIN_PRESERVATION"
    if not _valid(baseline) and _valid(winner):
        return "POLICY_SAFE_ALTERNATIVE"
    return "BETTER_MULTI_DIMENSIONAL_TRADEOFF"


def loss_category(
    result: ArenaMissionResult,
    *,
    outside_option_utility: float = OUTSIDE_DEFAULT,
) -> str | None:
    if result.selection.no_purchase:
        return "OUTSIDE_OPTION"
    chosen = result.selection.selected_strategy
    if chosen == "ASTRAOS":
        return None
    astraos = _by_name(result, "ASTRAOS")
    semantic = _by_name(result, "SEMANTIC_ONLY")
    if chosen == "ALWAYS_DISCOUNT":
        return "DISCOUNT_BETTER_VALUE"
    if chosen == "CHEAPEST_ELIGIBLE":
        return "CHEAPEST_BETTER_FOR_BUDGET"
    if chosen == "SEMANTIC_ONLY" or chosen == "DEFAULT":
        if (
            _valid(astraos)
            and _valid(semantic)
            and classify_commercial_change(semantic, astraos) == "NONE"
        ):
            return "SEMANTIC_DEFAULT_ALREADY_OPTIMAL"
        if astraos and not _valid(astraos):
            return "POLICY_LIMITED"
        if (
            astraos
            and semantic
            and astraos.intervention_cost_cents
            and semantic.buyer_utility is not None
            and astraos.buyer_utility is not None
            and astraos.buyer_utility - semantic.buyer_utility < 0.02
        ):
            return "INTERVENTION_TOO_EXPENSIVE"
        return "SEMANTIC_DEFAULT_ALREADY_OPTIMAL"
    if (
        astraos
        and astraos.buyer_utility is not None
        and astraos.buyer_utility < outside_option_utility
    ):
        return "OUTSIDE_OPTION"
    return "POLICY_LIMITED"


def win_loss_summary(
    results: list[ArenaMissionResult],
    *,
    outside_option_utility: float = OUTSIDE_DEFAULT,
) -> dict[str, Any]:
    wins: Counter[str] = Counter()
    losses: Counter[str] = Counter()
    astraos_wins = 0
    astraos_losses = 0
    for result in results:
        if result.selection.selected_strategy == "ASTRAOS":
            astraos_wins += 1
            wins[
                win_category(
                    _by_name(result, "ASTRAOS"),
                    _by_name(result, "SEMANTIC_ONLY"),
                    _by_name(result, "DEFAULT"),
                    _by_name(result, "ALWAYS_DISCOUNT"),
                )
                or "BETTER_MULTI_DIMENSIONAL_TRADEOFF"
            ] += 1
        else:
            astraos_losses += 1
            losses[
                loss_category(result, outside_option_utility=outside_option_utility)
                or "POLICY_LIMITED"
            ] += 1
    return {
        "astraos_wins": astraos_wins,
        "astraos_losses_or_no_purchase": astraos_losses,
        "win_categories": dict(wins),
        "loss_categories": dict(losses),
    }


def example_missions(
    results: list[ArenaMissionResult],
    *,
    outside_option_utility: float = OUTSIDE_DEFAULT,
) -> dict[str, Any]:
    """Pick representative real missions. Do not invent offers."""
    wanted = {
        "urgent": None,
        "budget": None,
        "assurance": None,
        "balanced": None,
    }
    hero_same_product = None
    discount_contrast = None
    for result in results:
        tags = set(result.mission.scenario_tags)
        for tag in wanted:
            if wanted[tag] is None and tag in tags:
                wanted[tag] = _mission_view(result, outside_option_utility)
        semantic = _by_name(result, "SEMANTIC_ONLY")
        astraos = _by_name(result, "ASTRAOS")
        discount = _by_name(result, "ALWAYS_DISCOUNT")
        if (
            hero_same_product is None
            and _valid(semantic)
            and _valid(astraos)
            and semantic.sku == astraos.sku
            and classify_commercial_change(semantic, astraos)
            in {"DELIVERY", "WARRANTY", "BUNDLE", "RETURNS", "MULTIPLE"}
            and (astraos.buyer_utility or 0) > (semantic.buyer_utility or 0)
        ):
            hero_same_product = _mission_view(result, outside_option_utility)
        if (
            discount_contrast is None
            and _valid(discount)
            and _valid(astraos)
            and (astraos.buyer_utility or 0) >= (discount.buyer_utility or 0)
            and (astraos.intervention_cost_cents or 0)
            < (discount.intervention_cost_cents or 0)
        ):
            discount_contrast = _mission_view(result, outside_option_utility)
    examples = [row for row in wanted.values() if row is not None]
    return {
        "segments": examples,
        "same_product_non_price": hero_same_product,
        "discount_contrast": discount_contrast,
    }


def _mission_view(
    result: ArenaMissionResult, outside_option_utility: float
) -> dict[str, Any]:
    return {
        "mission_id": result.mission.id,
        "segment": result.mission.scenario_tags,
        "buyer_profile": result.mission.buyer_profile,
        "intent": result.mission.raw_intent,
        "selected_strategy": result.selection.selected_strategy,
        "no_purchase": result.selection.no_purchase,
        "win_category": win_category(
            _by_name(result, "ASTRAOS")
            if result.selection.selected_strategy == "ASTRAOS"
            else None,
            _by_name(result, "SEMANTIC_ONLY"),
            _by_name(result, "DEFAULT"),
            _by_name(result, "ALWAYS_DISCOUNT"),
        ),
        "loss_category": loss_category(
            result, outside_option_utility=outside_option_utility
        ),
        "responses": {
            item.strategy_name: {
                "product": item.product_name,
                "sku": item.sku,
                "price_cents": item.total_customer_price_cents,
                "delivery": item.delivery,
                "delivery_days": item.delivery_days,
                "warranty": item.warranty,
                "warranty_months": item.warranty_months,
                "bundle": item.bundle,
                "returns": item.returns,
                "buyer_utility": item.buyer_utility,
                "contribution_cents": item.merchant_contribution_cents,
                "intervention_cost_cents": item.intervention_cost_cents,
                "status": item.status,
                "selectable": item.selectable,
                "used_pareto": item.used_pareto,
            }
            for item in result.responses
        },
    }


def build_ablation(
    results: list[ArenaMissionResult],
    metrics: list[StrategyMetrics],
    *,
    outside_option_utility: float = OUTSIDE_DEFAULT,
) -> dict[str, Any]:
    vs = astraos_vs_semantic(
        results, outside_option_utility=outside_option_utility
    )
    examples = example_missions(
        results, outside_option_utility=outside_option_utility
    )
    return {
        "incremental_deltas": incremental_deltas(metrics),
        "astraos_vs_semantic": vs,
        "intervention_attribution": intervention_attribution(
            results, outside_option_utility=outside_option_utility
        ),
        "win_loss": win_loss_summary(
            results, outside_option_utility=outside_option_utility
        ),
        "examples": examples,
        "default_uses_semantic_ranking": True,
        "default_note": (
            "DEFAULT already selects the top semantically ranked eligible "
            "product plus that product's conceptual default terms. "
            "Default → Semantic Only therefore does not isolate semantic "
            "search; Semantic Only → AstraOS isolates offer optimisation."
        ),
    }
