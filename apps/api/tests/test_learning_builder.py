"""Arena interactions: winner, losers, invalids excluded."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.arena.context import ArenaContextBuilder
from app.decision.arena.missions import HERO_MISSION
from app.decision.arena.runner import run_mission
from app.decision.learning.builder import (
    interactions_from_arena,
    interactions_from_negotiation,
)


@pytest.mark.asyncio
async def test_arena_builder_labels(db_session: AsyncSession) -> None:
    result, extra = await run_mission(
        db_session,
        HERO_MISSION,
        strategies=["DEFAULT", "ALWAYS_DISCOUNT", "CHEAPEST_ELIGIBLE", "ASTRAOS"],
        outside_option_utility=0.42,
        max_products=6,
    )
    rows = interactions_from_arena(result, extra["context"], extra_negatives=8)
    assert rows
    assert all(item["policy_safe"] for item in rows)
    assert all(item["hard_constraints_satisfied"] for item in rows)
    assert all(item["outcome_source"] == "SIMULATED_ARENA" for item in rows)
    assert all("buyer_utility" not in item["features"] for item in rows)
    selected = [item for item in rows if item["selected"]]
    if not result.selection.no_purchase:
        assert len(selected) >= 1
        assert all(item["outcome_type"] == "SELECTED" for item in selected)
    invalid_strategies = [
        item
        for item in result.responses
        if item.offer_id and (
            not item.policy_safe or not item.hard_constraints_satisfied
        )
    ]
    invalid_ids = {str(item.offer_id) for item in invalid_strategies}
    assert invalid_ids.isdisjoint({item["offer_id"] for item in rows})


@pytest.mark.asyncio
async def test_context_builder_still_shared(db_session: AsyncSession) -> None:
    context = await ArenaContextBuilder(db_session).build(HERO_MISSION, max_products=4)
    assert context.inventory_fingerprint


@pytest.mark.asyncio
async def test_negotiation_accept_and_reject_labels(db_session: AsyncSession) -> None:
    result, extra = await run_mission(
        db_session,
        HERO_MISSION,
        strategies=["ASTRAOS"],
        outside_option_utility=0.42,
        max_products=4,
    )
    context = extra["context"]
    offer_id = next(
        item.offer_id for item in result.responses if item.offer_id is not None
    )
    accepted = interactions_from_negotiation(
        session_id=uuid4(),
        proposal_id=uuid4(),
        offer_id=offer_id,
        accepted=True,
        rejected=False,
        countered=False,
        context=context,
    )
    rejected = interactions_from_negotiation(
        session_id=uuid4(),
        proposal_id=uuid4(),
        offer_id=offer_id,
        accepted=False,
        rejected=True,
        countered=False,
        context=context,
    )
    assert accepted is not None and accepted["outcome_type"] == "ACCEPTED"
    assert accepted["selected"] is True
    assert rejected is not None and rejected["outcome_type"] == "REJECTED"
    assert rejected["selected"] is False
    assert accepted["outcome_source"] == "SIMULATED_NEGOTIATION"
