"""Transparent selection narrative. Not a black-box attribution model."""

from app.decision.arena.ablation import loss_category, win_category
from app.decision.arena.models import ArenaContext, BuyerSelection, StrategyResponse
from app.decision.utility.profiles import PROFILE_LABELS


def explain_selection(
    context: ArenaContext,
    responses: list[StrategyResponse],
    selection: BuyerSelection,
) -> dict:
    weights = context.weights.as_dict()
    winner = next(
        (
            item
            for item in responses
            if item.strategy_name == selection.selected_strategy
        ),
        None,
    )
    default = next(
        (item for item in responses if item.strategy_name == "DEFAULT"),
        None,
    )
    discount = next(
        (item for item in responses if item.strategy_name == "ALWAYS_DISCOUNT"),
        None,
    )
    semantic = next(
        (item for item in responses if item.strategy_name == "SEMANTIC_ONLY"),
        None,
    )
    reasons: list[str] = []
    if selection.no_purchase:
        reasons.append(
            "No strategy cleared the outside-option utility threshold, "
            "so the simulated buyer made no purchase."
        )
    elif winner is not None:
        if (
            default
            and winner.delivery
            and default.delivery
            and winner.delivery != default.delivery
            and (
                winner.delivery_days
                if winner.delivery_days is not None
                else 99
            )
            < (
                default.delivery_days
                if default.delivery_days is not None
                else 99
            )
        ):
            reasons.append(
                "Faster delivery improved simulated delivery fit versus the "
                "default catalogue card."
            )
        if (
            default
            and winner.total_customer_price_cents is not None
            and default.total_customer_price_cents is not None
            and winner.total_customer_price_cents
            < default.total_customer_price_cents
        ):
            reasons.append(
                "The selected price is lower than the default list configuration."
            )
        if (
            default
            and winner.total_customer_price_cents == default.total_customer_price_cents
            and winner.delivery != default.delivery
        ):
            reasons.append(
                "AstraOS did not simply discount; it changed the offer "
                "dimension that mattered to this buyer."
            )
        if (
            discount
            and winner.strategy_name == "ASTRAOS"
            and winner.intervention_cost_cents is not None
            and discount.intervention_cost_cents is not None
            and winner.intervention_cost_cents < discount.intervention_cost_cents
        ):
            reasons.append(
                "Intervention cost is lower than automatic discounting while "
                "simulated utility is higher."
            )
        if default and winner.product_name == default.product_name:
            reasons.append("Product fit is the same as the default match.")
        if not reasons:
            reasons.append(
                "The simulated buyer chose the highest transparent utility "
                "under the declared weights."
            )
    compare = semantic or default
    component_deltas = _component_deltas(winner, compare)
    return {
        "profile_id": context.buyer_profile,
        "profile_label": PROFILE_LABELS.get(
            context.buyer_profile, context.buyer_profile
        ),
        "weights": weights,
        "reasons": reasons,
        "win_category": win_category(winner, semantic, default, discount),
        "loss_category": loss_category(
            _selection_result(context, responses, selection)
        ),
        "component_deltas": component_deltas,
        "winner_trace": winner.utility_trace.model_dump()
        if winner and winner.utility_trace
        else None,
        "default_trace": default.utility_trace.model_dump()
        if default and default.utility_trace
        else None,
        "semantic_trace": semantic.utility_trace.model_dump()
        if semantic and semantic.utility_trace
        else None,
    }


def _component_deltas(
    winner: StrategyResponse | None, baseline: StrategyResponse | None
) -> list[dict[str, float | str]]:
    if winner is None or baseline is None:
        return []
    if winner.utility_trace is None or baseline.utility_trace is None:
        return []
    base = {item.component: item.weighted for item in baseline.utility_trace.components}
    rows: list[dict[str, float | str]] = []
    for item in winner.utility_trace.components:
        rows.append(
            {
                "component": item.component,
                "winner": item.weighted,
                "baseline": base.get(item.component, 0.0),
                "delta": round(item.weighted - base.get(item.component, 0.0), 4),
            }
        )
    net = (winner.buyer_utility or 0) - (baseline.buyer_utility or 0)
    rows.append(
        {
            "component": "net",
            "winner": winner.buyer_utility or 0,
            "baseline": baseline.buyer_utility or 0,
            "delta": round(net, 4),
        }
    )
    return rows


def _selection_result(context, responses, selection):
    from app.decision.arena.models import ArenaMissionResult

    return ArenaMissionResult(
        mission=context.mission,
        responses=responses,
        selection=selection,
    )
