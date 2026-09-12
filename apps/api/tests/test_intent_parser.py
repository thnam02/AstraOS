"""Rule-based intent parser tests."""

import pytest

from app.decision.intent.models import (
    ConstraintField,
    ConstraintOperator,
    IntentStatus,
    PreferenceDirection,
    PreferenceField,
)
from app.decision.intent.parser import parse_intent
from app.decision.intent.rule_based_parser import RuleBasedIntentParser
from tests.qualification_fixtures import HERO_INTENT, HERO_INTENT_DELIVERED


def _constraint(intent, field):
    return next(item for item in intent.hard_constraints if item.field == field)


def _pref(intent, field):
    return next(item for item in intent.soft_preferences if item.field == field)


@pytest.mark.asyncio
async def test_parses_price_under_as_lt() -> None:
    intent = await parse_intent("headphones under $350")
    price = _constraint(intent, ConstraintField.PRICE)
    assert price.operator == ConstraintOperator.LT
    assert price.normalized_value == 35000
    assert price.unit == "AUD_CENTS"
    assert "350" in price.source_phrase


@pytest.mark.asyncio
async def test_parses_or_less_as_lte() -> None:
    intent = await parse_intent("headphones $350 or less")
    price = _constraint(intent, ConstraintField.PRICE)
    assert price.operator == ConstraintOperator.LTE
    assert price.normalized_value == 35000


@pytest.mark.asyncio
async def test_parses_less_than_price() -> None:
    intent = await parse_intent("less than $300")
    price = intent.hard_constraints[0]
    assert price.operator == ConstraintOperator.LT
    assert price.normalized_value == 30000


@pytest.mark.asyncio
async def test_parses_anc_required() -> None:
    intent = await parse_intent("must have ANC")
    anc = intent.hard_constraints[0]
    assert anc.field == ConstraintField.ANC
    assert anc.operator == ConstraintOperator.EQ
    assert anc.value is True
    assert "ANC" in anc.source_phrase


@pytest.mark.asyncio
async def test_parses_noise_cancelling_synonym() -> None:
    intent = await parse_intent("I need noise-cancelling headphones")
    assert any(
        item.field == ConstraintField.ANC and item.value is True
        for item in intent.hard_constraints
    )


@pytest.mark.asyncio
async def test_parses_no_anc() -> None:
    intent = await parse_intent("no ANC please")
    anc = _constraint(intent, ConstraintField.ANC)
    assert anc.value is False


@pytest.mark.asyncio
async def test_parses_battery_minimum() -> None:
    intent = await parse_intent("at least 30 hours battery")
    battery = intent.hard_constraints[0]
    assert battery.field == ConstraintField.BATTERY_HOURS
    assert battery.operator == ConstraintOperator.GTE
    assert battery.normalized_value == 30


@pytest.mark.asyncio
async def test_parses_battery_more_than() -> None:
    intent = await parse_intent("more than 30 hours battery")
    battery = intent.hard_constraints[0]
    assert battery.operator == ConstraintOperator.GT
    assert battery.normalized_value == 30


@pytest.mark.asyncio
async def test_parses_battery_symbolic() -> None:
    intent = await parse_intent("battery >= 40h")
    battery = intent.hard_constraints[0]
    assert battery.operator == ConstraintOperator.GTE
    assert battery.normalized_value == 40


@pytest.mark.asyncio
async def test_parses_today_delivery() -> None:
    intent = await parse_intent("need them delivered today")
    delivery = intent.hard_constraints[0]
    assert delivery.field == ConstraintField.DELIVERY_DAYS
    assert delivery.operator == ConstraintOperator.LTE
    assert delivery.normalized_value == 0


@pytest.mark.asyncio
async def test_parses_same_day() -> None:
    intent = await parse_intent("same-day delivery")
    delivery = intent.hard_constraints[0]
    assert delivery.normalized_value == 0


@pytest.mark.asyncio
async def test_parses_within_two_days() -> None:
    intent = await parse_intent("within two days")
    delivery = intent.hard_constraints[0]
    assert delivery.field == ConstraintField.DELIVERY_DAYS
    assert delivery.operator == ConstraintOperator.LTE
    assert delivery.normalized_value == 2


@pytest.mark.asyncio
async def test_parses_in_stock() -> None:
    intent = await parse_intent("in stock")
    stock = intent.hard_constraints[0]
    assert stock.field == ConstraintField.IN_STOCK
    assert stock.value is True


@pytest.mark.asyncio
async def test_parses_soft_comfort_preference() -> None:
    intent = await parse_intent("comfort matters a lot")
    pref = _pref(intent, PreferenceField.COMFORT)
    assert pref.direction == PreferenceDirection.MAXIMIZE
    assert pref.importance >= 0.8


@pytest.mark.asyncio
async def test_parses_lightweight_preference() -> None:
    intent = await parse_intent("prefer something lightweight")
    pref = _pref(intent, PreferenceField.WEIGHT)
    assert pref.direction == PreferenceDirection.MINIMIZE
    assert 0.6 <= pref.importance <= 0.8


@pytest.mark.asyncio
async def test_parses_low_price_sensitivity() -> None:
    intent = await parse_intent(
        "Comfort and reliability matter more than getting the absolute cheapest option."
    )
    price = _pref(intent, PreferenceField.PRICE)
    assert price.importance == 0.3


@pytest.mark.asyncio
async def test_parses_long_haul_context() -> None:
    intent = await parse_intent("for a 12-hour flight")
    assert "long_haul_travel" in intent.context_tags
    assert not any(
        item.field == ConstraintField.BATTERY_HOURS for item in intent.hard_constraints
    )


@pytest.mark.asyncio
async def test_preserves_source_phrase() -> None:
    intent = await parse_intent("under $350")
    assert intent.hard_constraints[0].source_phrase.lower().startswith("under")


@pytest.mark.asyncio
async def test_unsupported_luxurious_recorded() -> None:
    intent = await parse_intent("must look luxurious")
    assert intent.ambiguities
    assert intent.ambiguities[0].reason == "unsupported_attribute"
    assert intent.ambiguities[0].appears_mandatory is True
    assert intent.status in {IntentStatus.NEEDS_CLARIFICATION, IntentStatus.UNSUPPORTED}


@pytest.mark.asyncio
async def test_animal_leather_is_unsupported_not_satisfied() -> None:
    intent = await parse_intent("No animal leather")
    assert any(item.reason == "unsupported_attribute" for item in intent.ambiguities)
    assert not any(item.field.value == "material" for item in intent.hard_constraints)


@pytest.mark.asyncio
async def test_parser_is_deterministic() -> None:
    first = await parse_intent(HERO_INTENT)
    second = await parse_intent(HERO_INTENT)
    assert first.model_dump() == second.model_dump()


@pytest.mark.asyncio
async def test_hero_intent_structure() -> None:
    intent = await parse_intent(HERO_INTENT)
    fields = {item.field for item in intent.hard_constraints}
    assert ConstraintField.ANC in fields
    assert ConstraintField.PRICE in fields
    assert ConstraintField.DELIVERY_DAYS in fields
    assert intent.category == "headphones"
    assert "long_haul_travel" in intent.context_tags
    prefs = {item.field for item in intent.soft_preferences}
    assert PreferenceField.COMFORT in prefs
    assert PreferenceField.RELIABILITY in prefs
    assert intent.status == IntentStatus.READY


@pytest.mark.asyncio
async def test_hero_delivered_today_variant() -> None:
    intent = await parse_intent(HERO_INTENT_DELIVERED)
    delivery = _constraint(intent, ConstraintField.DELIVERY_DAYS)
    assert delivery.normalized_value == 0


@pytest.mark.asyncio
async def test_foldable_and_wireless() -> None:
    intent = await parse_intent("foldable wireless headphones")
    fields = {item.field: item.value for item in intent.hard_constraints}
    assert fields[ConstraintField.FOLDABLE] is True
    assert fields[ConstraintField.WIRELESS] is True


@pytest.mark.asyncio
async def test_not_foldable() -> None:
    intent = await parse_intent("not foldable")
    assert intent.hard_constraints[0].value is False


@pytest.mark.asyncio
async def test_rule_based_parser_type() -> None:
    parsed = await RuleBasedIntentParser().parse("under $100")
    assert parsed.parser_type == "rule_based"
