"""Optional live LLM parser checks. Skipped in CI without credentials."""

import os

import pytest

from app.decision.intent.models import ConstraintField
from app.decision.intent.parser import parse_intent
from app.decision.intent.provider import provider_configured

pytestmark = pytest.mark.integration_llm

HERO = (
    "I'm flying from Sydney to Singapore tomorrow and need wireless "
    "noise-cancelling headphones under A$350. I need them delivered today. "
    "I'll wear them for hours, so comfort and reliability matter more than "
    "getting the absolute cheapest option."
)


def _have_key() -> bool:
    return provider_configured() or bool(
        os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    )


@pytest.mark.skipif(not _have_key(), reason="LLM credentials are not configured")
async def test_live_llm_parses_hero_critical_constraints() -> None:
    intent = await parse_intent(HERO, parser_mode="llm")
    assert intent.parser_metadata is not None
    if intent.parser_metadata.fallback_used:
        pytest.skip("live provider fell back; environment is not integration-ready")
    fields = {item.field for item in intent.hard_constraints}
    assert ConstraintField.ANC in fields
    assert ConstraintField.PRICE in fields
    assert ConstraintField.WIRELESS in fields
    assert ConstraintField.DELIVERY_DAYS in fields
    assert intent.parser_type == "llm"
    assert intent.parser_metadata.prompt_version == "intent-parser-v2"


@pytest.mark.skipif(not _have_key(), reason="LLM credentials are not configured")
async def test_live_llm_does_not_invent_numeric_soon() -> None:
    intent = await parse_intent("I need it soon.", parser_mode="llm")
    assert intent.parser_metadata is not None
    if intent.parser_metadata.fallback_used:
        pytest.skip("live provider fell back; environment is not integration-ready")
    assert not any(
        item.field == ConstraintField.DELIVERY_DAYS
        for item in intent.hard_constraints
    )
