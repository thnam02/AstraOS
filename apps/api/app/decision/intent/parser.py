"""Intent parser protocol and factory."""

from typing import Protocol

from app.config import settings
from app.decision.intent.exceptions import LLMParserUnavailable
from app.decision.intent.models import ShoppingIntent


class IntentParser(Protocol):
    """Parsers interpret language. They must not decide eligibility."""

    parser_type: str

    async def parse(self, text: str) -> ShoppingIntent: ...


def resolve_parser_mode(requested: str | None) -> str:
    mode = (requested or settings.intent_parser_mode or "rule_based").strip().lower()
    if mode not in {"rule_based", "llm"}:
        return "rule_based"
    return mode


async def parse_intent(text: str, parser_mode: str | None = None) -> ShoppingIntent:
    """Parse using the requested mode, falling back to rule-based."""
    from app.decision.intent.llm_parser import LLMIntentParser
    from app.decision.intent.normalizer import normalize_intent
    from app.decision.intent.rule_based_parser import RuleBasedIntentParser

    mode = resolve_parser_mode(parser_mode)
    if mode == "llm":
        try:
            parsed = await LLMIntentParser().parse(text)
        except LLMParserUnavailable:
            parsed = await RuleBasedIntentParser().parse(text)
    else:
        parsed = await RuleBasedIntentParser().parse(text)
    return normalize_intent(parsed)
