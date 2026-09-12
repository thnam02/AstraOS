"""Stage 3 deep-intent extraction."""

import pytest

from app.decision.intent.models import IntentStatus
from app.decision.intent.parser import parse_intent
from app.decision.intent.taxonomy import (
    ContextLabel,
    OutcomeLabel,
    TradeoffDimension,
)

HERO = (
    "I'm flying from Sydney to Singapore tomorrow and need wireless "
    "noise-cancelling headphones under A$350. I need them delivered today. "
    "I'll wear them for hours, so comfort and reliability matter more than "
    "getting the absolute cheapest option."
)


@pytest.mark.asyncio
async def test_context_long_haul_and_hours() -> None:
    intent = await parse_intent(HERO)
    labels = {item.label for item in intent.context_items}
    assert ContextLabel.LONG_HAUL_TRAVEL in labels
    assert ContextLabel.EXTENDED_CONTINUOUS_USE in labels
    assert "long_haul_travel" in intent.context_tags


@pytest.mark.asyncio
async def test_flight_tomorrow_is_not_delivery() -> None:
    intent = await parse_intent(HERO)
    deliveries = [
        item for item in intent.hard_constraints if item.field.value == "delivery_days"
    ]
    assert len(deliveries) == 1
    assert deliveries[0].normalized_value == 0


@pytest.mark.asyncio
async def test_desired_outcomes_from_hours() -> None:
    intent = await parse_intent("I'll wear them for hours so comfort matters")
    labels = {item.label for item in intent.desired_outcomes}
    assert OutcomeLabel.LOW_FATIGUE in labels
    assert any(
        "hours" in item.source_phrase.lower() for item in intent.desired_outcomes
    )


@pytest.mark.asyncio
async def test_tradeoff_reliability_over_price() -> None:
    intent = await parse_intent(
        "I would rather pay more for reliability than get the cheapest option"
    )
    assert intent.tradeoffs
    assert intent.tradeoffs[0].preferred_dimension == TradeoffDimension.RELIABILITY
    assert intent.tradeoffs[0].over_dimension == TradeoffDimension.PRICE


@pytest.mark.asyncio
async def test_hero_tradeoffs() -> None:
    intent = await parse_intent(HERO)
    pairs = {
        (item.preferred_dimension, item.over_dimension) for item in intent.tradeoffs
    }
    assert (TradeoffDimension.COMFORT, TradeoffDimension.PRICE) in pairs
    assert (TradeoffDimension.RELIABILITY, TradeoffDimension.PRICE) in pairs


@pytest.mark.asyncio
async def test_source_phrase_on_context() -> None:
    intent = await parse_intent("for a 12-hour flight")
    assert intent.context_items
    assert "flight" in intent.context_items[0].source_phrase.lower()


@pytest.mark.asyncio
async def test_unsupported_luxurious_feel() -> None:
    intent = await parse_intent("must feel luxurious")
    assert intent.status in {
        IntentStatus.NEEDS_CLARIFICATION,
        IntentStatus.UNSUPPORTED,
    }
    assert intent.ambiguities or intent.unsupported_semantic_needs


@pytest.mark.asyncio
async def test_sustainability_is_unsupported_semantic() -> None:
    intent = await parse_intent("sustainable headphones under $200")
    labels = {item.label for item in intent.unsupported_semantic_needs}
    assert "sustainability" in labels
    assert not intent.values


@pytest.mark.asyncio
async def test_hero_desired_outcomes() -> None:
    intent = await parse_intent(HERO)
    labels = {item.label for item in intent.desired_outcomes}
    assert OutcomeLabel.LOW_FATIGUE in labels
    assert OutcomeLabel.RELIABLE_EXTENDED_USE in labels
    assert OutcomeLabel.TRAVEL_CONVENIENCE in labels


@pytest.mark.asyncio
async def test_wireless_parsed_on_hero() -> None:
    intent = await parse_intent(HERO)
    fields = {item.field.value for item in intent.hard_constraints}
    assert {"anc", "price", "delivery_days", "wireless"} <= fields
