"""LLM parser architecture tests. No live model calls."""

import pytest

from app.decision.intent.exceptions import LLMParserUnavailable
from app.decision.intent.llm_parser import LLMIntentParser
from app.decision.intent.models import ConstraintField
from app.decision.intent.parser import parse_intent


class _FakeClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls = 0

    async def complete_json(self, **_kwargs: object) -> dict[str, object]:
        self.calls += 1
        return self.payload


class _InvalidThenValid:
    def __init__(self) -> None:
        self.calls = 0

    async def complete_json(self, **_kwargs: object) -> dict[str, object]:
        self.calls += 1
        if self.calls == 1:
            return {
                "hard_constraints": [
                    {
                        "field": "aura",
                        "operator": "EQ",
                        "value": True,
                        "source_phrase": "vibes",
                    }
                ]
            }
        return {
            "category": "headphones",
            "hard_constraints": [
                {
                    "id": "c1",
                    "field": "anc",
                    "operator": "EQ",
                    "value": True,
                    "source_phrase": "ANC",
                }
            ],
            "soft_preferences": [],
            "context_tags": [],
            "ambiguities": [],
        }


@pytest.mark.asyncio
async def test_llm_unavailable_without_client() -> None:
    parser = LLMIntentParser(client=None)
    parser.client = None
    with pytest.raises(LLMParserUnavailable):
        await parser.parse("under $100")


@pytest.mark.asyncio
async def test_llm_mode_falls_back_without_credentials() -> None:
    intent = await parse_intent("headphones under $350", parser_mode="llm")
    assert intent.parser_type == "rule_based"
    assert any(item.field == ConstraintField.PRICE for item in intent.hard_constraints)


@pytest.mark.asyncio
async def test_llm_validates_allow_list_and_retries() -> None:
    client = _InvalidThenValid()
    parsed = await LLMIntentParser(client=client).parse("must have ANC")
    assert client.calls == 2
    assert parsed.parser_type == "llm"
    assert parsed.hard_constraints[0].field == ConstraintField.ANC


@pytest.mark.asyncio
async def test_llm_rejects_invented_field_after_retry() -> None:
    client = _FakeClient(
        {
            "hard_constraints": [
                {
                    "field": "luxury_score",
                    "operator": "EQ",
                    "value": True,
                    "source_phrase": "luxurious",
                }
            ]
        }
    )
    parsed = await LLMIntentParser(client=client).parse("must look luxurious")
    assert client.calls == 2
    assert parsed.parser_type == "rule_based"
    assert any(item.reason == "llm_validation_failed" for item in parsed.ambiguities)
