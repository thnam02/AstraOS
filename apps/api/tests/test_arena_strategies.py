"""Baseline strategies must not secretly use Stage 5 optimisation."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.arena.config import ArenaDuelRequest
from app.decision.arena.context import ArenaContextBuilder
from app.decision.arena.missions import HERO_MISSION
from app.decision.arena.models import BuyerMission
from app.decision.arena.runner import run_duel
from app.decision.arena.strategies import get_strategy
from app.decision.optimisation.baseline import is_conceptual_baseline

HERO = HERO_MISSION.raw_intent


@pytest.fixture
async def hero_context(db_session: AsyncSession):
    builder = ArenaContextBuilder(db_session)
    return await builder.build(HERO_MISSION, max_products=8)


@pytest.mark.asyncio
async def test_default_is_conceptual_baseline(hero_context) -> None:
    response = get_strategy("DEFAULT").generate_response(hero_context)
    assert response.used_pareto is False
    if response.offer_id is None:
        return
    offer = next(item for item in hero_context.offers if item.id == response.offer_id)
    assert is_conceptual_baseline(offer)
    assert offer.price_adjustment_type == "BASE"
    assert response.delivery == "STANDARD"


@pytest.mark.asyncio
async def test_discount_uses_discount_rule(db_session: AsyncSession) -> None:
    mission = BuyerMission(
        id="budget-discount",
        raw_intent=(
            "I need wireless ANC headphones under A$300. "
            "Cheapest option that still works is fine. Two-day delivery is ok."
        ),
        buyer_profile="BUDGET_SHOPPER",
        scenario_tags=["budget"],
        seed=2026,
    )
    context = await ArenaContextBuilder(db_session).build(mission, max_products=8)
    response = get_strategy("ALWAYS_DISCOUNT").generate_response(context)
    assert response.used_pareto is False
    assert response.offer_id is not None
    offer = next(item for item in context.offers if item.id == response.offer_id)
    assert offer.price_adjustment_type == "DISCOUNT"
    assert offer.delivery_code == "STANDARD"
    assert offer.warranty_code == "STANDARD_12"
    assert offer.bundle_code is None
    assert response.used_max_discount is True


@pytest.mark.asyncio
async def test_cheapest_is_actually_cheapest(hero_context) -> None:
    response = get_strategy("CHEAPEST_ELIGIBLE").generate_response(hero_context)
    assert response.used_pareto is False
    if response.offer_id is None:
        pytest.skip("no policy-safe offer in this space")
    assert response.is_cheapest_in_space is True
    safe_prices = [
        item.total_customer_price_cents
        for item in hero_context.scored
        if item.policy.policy_safe
    ]
    assert response.total_customer_price_cents == min(safe_prices)


@pytest.mark.asyncio
async def test_semantic_only_does_not_use_pareto(hero_context) -> None:
    response = get_strategy("SEMANTIC_ONLY").generate_response(hero_context)
    assert response.used_pareto is False
    default = get_strategy("DEFAULT").generate_response(hero_context)
    assert response.sku == default.sku
    assert response.delivery == default.delivery
    assert response.warranty == default.warranty


@pytest.mark.asyncio
async def test_astraos_uses_stage_five_selection(hero_context) -> None:
    response = get_strategy("ASTRAOS").generate_response(hero_context)
    assert response.used_pareto is True
    assert response.offer_id == hero_context.recommended_offer_id
    if response.offer_id is not None:
        assert response.hard_constraints_satisfied is response.policy_safe


@pytest.mark.asyncio
async def test_strategies_share_one_context(hero_context) -> None:
    names = ["DEFAULT", "ALWAYS_DISCOUNT", "CHEAPEST_ELIGIBLE", "ASTRAOS"]
    first = hero_context.inventory_fingerprint
    for name in names:
        get_strategy(name).generate_response(hero_context)
        assert hero_context.inventory_fingerprint == first
        assert hero_context.buyer_profile == "URGENT_TRAVELLER"
        assert hero_context.policy_id is not None


@pytest.mark.asyncio
async def test_hero_duel_is_synthetic(db_session: AsyncSession) -> None:
    payload = await run_duel(
        db_session,
        ArenaDuelRequest(intent=HERO, buyer_profile="URGENT_TRAVELLER"),
    )
    result = payload["result"]
    assert payload["disclaimer"].startswith("Synthetic evaluation")
    names = {item.strategy_name for item in result.responses}
    assert {"DEFAULT", "ALWAYS_DISCOUNT", "CHEAPEST_ELIGIBLE", "ASTRAOS"} <= names
    astra = next(item for item in result.responses if item.strategy_name == "ASTRAOS")
    default = next(item for item in result.responses if item.strategy_name == "DEFAULT")
    assert astra.used_pareto is True
    assert default.used_pareto is False
