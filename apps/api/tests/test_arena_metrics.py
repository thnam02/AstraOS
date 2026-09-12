"""Metric formulas, including contribution per opportunity."""

from app.decision.arena.metrics import compute_strategy_metrics, summarize
from app.decision.arena.models import (
    ArenaMissionResult,
    BuyerMission,
    BuyerSelection,
    StrategyResponse,
)


def _mission(idx: int, tag: str, profile: str) -> BuyerMission:
    return BuyerMission(
        id=f"m-{idx}",
        raw_intent="ANC headphones under A$300",
        buyer_profile=profile,
        scenario_tags=[tag],
        seed=idx,
    )


def _result(
    idx: int,
    winner: str | None,
    *,
    tag: str = "urgent",
    profile: str = "URGENT_TRAVELLER",
    contrib: dict[str, int] | None = None,
) -> ArenaMissionResult:
    contrib = contrib or {"DEFAULT": 11900, "ASTRAOS": 11100}
    responses = [
        StrategyResponse(
            strategy_name=name,
            offer_id=None if name == "MISSING" else None,
            buyer_utility=0.6 if name == "DEFAULT" else 0.8,
            merchant_contribution_cents=value,
            intervention_cost_cents=800 if name == "ASTRAOS" else 0,
            hard_constraints_satisfied=True,
            policy_safe=True,
            transaction_possible=True,
        )
        for name, value in contrib.items()
    ]
    for item in responses:
        if item.strategy_name != "MISSING":
            from uuid import uuid4

            item.offer_id = uuid4()
    no_purchase = winner is None
    return ArenaMissionResult(
        mission=_mission(idx, tag, profile),
        responses=responses,
        selection=BuyerSelection(
            selected_strategy=winner,
            no_purchase=no_purchase,
            reason="NO_PURCHASE" if no_purchase else "HIGHEST_SIMULATED_UTILITY",
        ),
    )


def test_contribution_per_opportunity() -> None:
    results = [
        _result(1, "ASTRAOS"),
        _result(2, "ASTRAOS"),
        _result(3, "DEFAULT"),
        _result(4, None),
    ]
    astra = compute_strategy_metrics(results, "ASTRAOS")
    assert astra.wins == 2
    assert astra.selection_rate == 0.5
    assert astra.avg_contribution_when_selected == 11100
    assert astra.contribution_per_opportunity_cents == 5550


def test_no_purchase_and_violation_rates() -> None:
    hard = _result(1, "DEFAULT")
    hard.responses[0].hard_constraints_satisfied = False
    hard.responses[0].policy_safe = False
    policy = _result(2, None)
    policy.responses[0].hard_constraints_satisfied = True
    policy.responses[0].policy_safe = False
    results = [hard, policy]
    metrics = compute_strategy_metrics(results, "DEFAULT")
    assert metrics.hard_constraint_violation_rate == 0.5
    assert metrics.policy_violation_rate == 0.5
    summary = summarize(
        results,
        strategies=["DEFAULT", "ASTRAOS"],
        seed=1,
        config={},
        timing={},
    )
    assert summary.no_purchase_rate == 0.5
    assert summary.segment_metrics
