"""Phase 11 ablation: Semantic Only is matching-only; metrics stay honest."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.arena.ablation import (
    astraos_vs_semantic,
    classify_commercial_change,
    intervention_attribution,
)
from app.decision.arena.config import ABLATION_STRATEGIES, DEFAULT_STRATEGIES
from app.decision.arena.context import ArenaContextBuilder
from app.decision.arena.metrics import pairwise_matrix, summarize
from app.decision.arena.missions import HERO_MISSION
from app.decision.arena.models import (
    ArenaMissionResult,
    BuyerMission,
    BuyerSelection,
    StrategyResponse,
)
from app.decision.arena.selection import choose_response
from app.decision.arena.strategies import get_strategy
from app.decision.optimisation.baseline import is_conceptual_baseline


@pytest.fixture
async def hero_context(db_session: AsyncSession):
    return await ArenaContextBuilder(db_session).build(HERO_MISSION, max_products=8)


def _mission(idx: int, tag: str = "urgent") -> BuyerMission:
    return BuyerMission(
        id=f"ab-{idx}",
        raw_intent="ANC headphones under A$300",
        buyer_profile="URGENT_TRAVELLER",
        scenario_tags=[tag],
        seed=idx,
    )


def _row(
    name: str,
    *,
    utility: float,
    contrib: int,
    cost: int = 0,
    sku: str = "SON-T32",
    price: int = 19488,
    delivery: str = "STANDARD",
    days: int = 2,
    warranty: str = "STANDARD_12",
    months: int = 12,
    bundle: str | None = None,
    returns: str = "STANDARD_30",
    safe: bool = True,
) -> StrategyResponse:
    return StrategyResponse(
        strategy_name=name,
        offer_id=uuid4(),
        sku=sku,
        product_name=sku,
        total_customer_price_cents=price,
        delivery=delivery,
        delivery_days=days,
        warranty=warranty,
        warranty_months=months,
        bundle=bundle,
        returns=returns,
        buyer_utility=utility,
        merchant_contribution_cents=contrib,
        intervention_cost_cents=cost,
        hard_constraints_satisfied=safe,
        policy_safe=safe,
        transaction_possible=safe,
        selectable=safe,
        used_pareto=name == "ASTRAOS",
    )


def _result(
    idx: int, rows: list[StrategyResponse], winner: str | None
) -> ArenaMissionResult:
    return ArenaMissionResult(
        mission=_mission(idx),
        responses=rows,
        selection=BuyerSelection(
            selected_strategy=winner,
            no_purchase=winner is None,
            reason="NO_PURCHASE" if winner is None else "HIGHEST_SIMULATED_UTILITY",
        ),
    )


def test_primary_ablation_set() -> None:
    assert DEFAULT_STRATEGIES == ABLATION_STRATEGIES
    assert DEFAULT_STRATEGIES == (
        "DEFAULT",
        "ALWAYS_DISCOUNT",
        "SEMANTIC_ONLY",
        "ASTRAOS",
    )
    assert "CHEAPEST_ELIGIBLE" not in DEFAULT_STRATEGIES


def test_incremental_deltas_from_metrics() -> None:
    results = [
        _result(
            1,
            [
                _row("DEFAULT", utility=0.50, contrib=10000),
                _row(
                    "ALWAYS_DISCOUNT",
                    utility=0.55,
                    contrib=7000,
                    cost=3000,
                    price=16488,
                ),
                _row("SEMANTIC_ONLY", utility=0.50, contrib=10000),
                _row(
                    "ASTRAOS",
                    utility=0.70,
                    contrib=9000,
                    cost=800,
                    delivery="SAME_DAY",
                    days=0,
                ),
            ],
            "ASTRAOS",
        ),
        _result(
            2,
            [
                _row("DEFAULT", utility=0.40, contrib=10000),
                _row("ALWAYS_DISCOUNT", utility=0.62, contrib=7000, cost=3000),
                _row("SEMANTIC_ONLY", utility=0.40, contrib=10000),
                _row("ASTRAOS", utility=0.41, contrib=9800, cost=200),
            ],
            "ALWAYS_DISCOUNT",
        ),
    ]
    summary = summarize(
        results,
        strategies=["DEFAULT", "ALWAYS_DISCOUNT", "SEMANTIC_ONLY", "ASTRAOS"],
        seed=2026,
        config={"outside_option_utility": 0.42},
        timing={},
    )
    by_name = {row["name"]: row for row in summary.ablation["incremental_deltas"]}
    assert by_name["semantic_value"]["selection_rate"] == 0.0
    assert by_name["full_astraos_value"]["selection_rate"] == 0.5
    assert by_name["discount_value"]["selection_rate"] == 0.5


def test_astraos_vs_semantic_and_attribution() -> None:
    results = [
        _result(
            1,
            [
                _row("SEMANTIC_ONLY", utility=0.50, contrib=10000),
                _row(
                    "ASTRAOS",
                    utility=0.70,
                    contrib=9200,
                    cost=800,
                    delivery="SAME_DAY",
                    days=0,
                    warranty="EXTENDED_36",
                    months=36,
                    bundle="HARD_CASE",
                ),
            ],
            "ASTRAOS",
        ),
        _result(
            2,
            [
                _row("SEMANTIC_ONLY", utility=0.66, contrib=10000),
                _row("ASTRAOS", utility=0.66, contrib=10000),
            ],
            "SEMANTIC_ONLY",
        ),
    ]
    vs = astraos_vs_semantic(results)
    assert vs["both_valid"] == 2
    assert vs["astraos_preferred"] == 1
    assert vs["tie"] == 1
    assert vs["denominator"] == "missions_where_both_valid"
    attr = intervention_attribution(results)
    assert attr["astraos_preferred_over_semantic"] == 1
    assert attr["pct_involving_delivery"] == 1.0
    assert attr["pct_involving_warranty"] == 1.0
    assert attr["pct_involving_bundle"] == 1.0
    assert attr["pct_multi_lever"] == 1.0
    assert attr["pct_involving_price"] == 0.0
    assert attr["pct_involving_product"] == 0.0


def test_pairwise_uses_both_valid_denominator() -> None:
    results = [
        _result(
            1,
            [
                _row("DEFAULT", utility=0.50, contrib=10000),
                _row("ASTRAOS", utility=0.70, contrib=9000),
            ],
            "ASTRAOS",
        ),
        _result(
            2,
            [
                _row("DEFAULT", utility=0.20, contrib=10000, safe=False),
                _row("ASTRAOS", utility=0.70, contrib=9000),
            ],
            "ASTRAOS",
        ),
    ]
    rows = pairwise_matrix(results, ["DEFAULT", "ASTRAOS"])
    assert len(rows) == 1
    assert rows[0].both_valid == 1
    assert rows[0].denominator == "both_valid_offers"
    assert rows[0].left_wins == 0.0
    assert rows[0].right_wins == 1.0


def test_invalid_offer_never_enters_selection() -> None:
    unsafe = _row("ALWAYS_DISCOUNT", utility=0.99, contrib=1000, safe=False)
    valid = _row("ASTRAOS", utility=0.55, contrib=8000)
    choice = choose_response([unsafe, valid], outside_option_utility=0.42)
    assert choice.selected_strategy == "ASTRAOS"
    assert choice.no_purchase is False


def test_classify_commercial_change() -> None:
    left = _row("SEMANTIC_ONLY", utility=0.5, contrib=10000)
    same = _row("ASTRAOS", utility=0.5, contrib=10000)
    assert classify_commercial_change(left, same) == "NONE"
    faster = _row("ASTRAOS", utility=0.6, contrib=9000, delivery="SAME_DAY", days=0)
    assert classify_commercial_change(left, faster) == "DELIVERY"


@pytest.mark.asyncio
async def test_semantic_only_never_reuses_recommended(hero_context) -> None:
    semantic = get_strategy("SEMANTIC_ONLY").generate_response(hero_context)
    astraos = get_strategy("ASTRAOS").generate_response(hero_context)
    assert semantic.used_pareto is False
    assert semantic.strategy_version == "v1"
    if semantic.offer_id is None:
        return
    offer = next(item for item in hero_context.offers if item.id == semantic.offer_id)
    assert is_conceptual_baseline(offer)
    assert offer.price_adjustment_type == "BASE"
    if astraos.offer_id and not is_conceptual_baseline(
        next(item for item in hero_context.offers if item.id == astraos.offer_id)
    ):
        assert semantic.offer_id != astraos.offer_id
        assert semantic.offer_id != hero_context.recommended_offer_id


@pytest.mark.asyncio
async def test_ablation_benchmark_is_reproducible(db_session: AsyncSession) -> None:
    from app.decision.arena.config import ArenaBenchmarkConfig
    from app.decision.arena.runner import run_benchmark

    config = ArenaBenchmarkConfig(
        mission_count=6,
        seed=2026,
        strategies=list(ABLATION_STRATEGIES),
    )
    first, a, _ = await run_benchmark(db_session, config)
    second, b, _ = await run_benchmark(db_session, config)
    assert first.strategies == list(ABLATION_STRATEGIES)
    assert first.ablation["default_uses_semantic_ranking"] is True
    assert [item.selection.selected_strategy for item in a] == [
        item.selection.selected_strategy for item in b
    ]
    assert first.strategy_metrics == second.strategy_metrics
    assert (
        first.ablation["astraos_vs_semantic"]
        == second.ablation["astraos_vs_semantic"]
    )
