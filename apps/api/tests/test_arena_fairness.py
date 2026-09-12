"""Arena fairness: same state, same scorer, no inventory contamination."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.arena.config import ArenaBenchmarkConfig
from app.decision.arena.context import ArenaCatalogueCache, ArenaContextBuilder
from app.decision.arena.missions import HERO_MISSION, generate_missions
from app.decision.arena.runner import run_benchmark, run_mission
from app.decision.offers.feasibility import sellable_units


@pytest.mark.asyncio
async def test_shared_merchant_snapshot(db_session: AsyncSession) -> None:
    cache = ArenaCatalogueCache()
    builder = ArenaContextBuilder(db_session, cache=cache)
    first = await builder.build(HERO_MISSION, max_products=6)
    second = await builder.build(HERO_MISSION, max_products=6)
    assert first.inventory_fingerprint == second.inventory_fingerprint
    assert first.policy_id == second.policy_id
    assert first.catalogue_variant_count == second.catalogue_variant_count
    before = {
        row.sku: sellable_units(row) for row in cache.variants if row.sku
    }
    await run_mission(
        db_session,
        HERO_MISSION,
        strategies=["DEFAULT", "ALWAYS_DISCOUNT", "ASTRAOS"],
        outside_option_utility=0.42,
        max_products=6,
        cache=cache,
    )
    after = {row.sku: sellable_units(row) for row in cache.variants if row.sku}
    assert before == after


@pytest.mark.asyncio
async def test_same_seed_reproduces_benchmark(db_session: AsyncSession) -> None:
    config = ArenaBenchmarkConfig(mission_count=8, seed=2026)
    first, results_a, _ = await run_benchmark(db_session, config)
    second, results_b, _ = await run_benchmark(db_session, config)
    assert first.no_purchase_rate == second.no_purchase_rate
    assert [item.selection.selected_strategy for item in results_a] == [
        item.selection.selected_strategy for item in results_b
    ]
    assert [item.mission.raw_intent for item in results_a] == [
        item.mission.raw_intent for item in results_b
    ]
    metrics_a = {
        row.strategy_name: row.selection_rate for row in first.strategy_metrics
    }
    metrics_b = {
        row.strategy_name: row.selection_rate for row in second.strategy_metrics
    }
    assert metrics_a == metrics_b


@pytest.mark.asyncio
async def test_generated_missions_are_valid_inputs() -> None:
    missions = generate_missions(20, seed=2026)
    assert len({item.id for item in missions}) == 20
    assert all(item.buyer_profile for item in missions)
