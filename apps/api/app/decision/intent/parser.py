"""Intent parser protocol and factory."""

from __future__ import annotations

import logging
import time
from typing import Protocol

from app.config import settings
from app.decision.intent.exceptions import LLMParserUnavailable
from app.decision.intent.models import ParserMetadata, ShoppingIntent

logger = logging.getLogger("astraos.intent")


class IntentParser(Protocol):
    """Parsers interpret language. They must not decide eligibility."""

    parser_type: str

    async def parse(self, text: str) -> ShoppingIntent: ...


def resolve_parser_mode(requested: str | None) -> str:
    mode = (requested or settings.intent_parser_mode or "rule_based").strip().lower()
    if mode not in {"rule_based", "llm"}:
        return "rule_based"
    return mode


def _fallback_reason(exc: Exception) -> str:
    message = str(exc).lower()
    if "timed out" in message or "timeout" in message:
        return "timeout"
    if "auth" in message:
        return "authentication"
    if "credentials" in message or "no client" in message:
        return "provider_unconfigured"
    if "unavailable" in message or "returned an error" in message:
        return "provider_unavailable"
    return "validation_failed"


async def parse_intent(text: str, parser_mode: str | None = None) -> ShoppingIntent:
    """Parse using the requested mode, falling back to rule-based."""
    from app.decision.intent.faithfulness import apply_faithfulness
    from app.decision.intent.llm_parser import LLMIntentParser
    from app.decision.intent.normalizer import normalize_intent
    from app.decision.intent.rule_based_parser import RuleBasedIntentParser

    mode = resolve_parser_mode(parser_mode)
    started = time.perf_counter()
    fallback_used = False
    fallback_reason: str | None = None
    llm_parser: LLMIntentParser | None = None
    if mode == "llm":
        llm_parser = LLMIntentParser()
        try:
            parsed = await llm_parser.parse(text)
            if not _has_actionable_constraints(parsed):
                rules = apply_faithfulness(await RuleBasedIntentParser().parse(text))
                if _has_actionable_constraints(rules):
                    parsed = rules
                    fallback_used = True
                    fallback_reason = "empty_extraction"
        except LLMParserUnavailable as exc:
            parsed = await RuleBasedIntentParser().parse(text)
            parsed = apply_faithfulness(parsed)
            fallback_used = True
            fallback_reason = _fallback_reason(exc)
    else:
        parsed = await RuleBasedIntentParser().parse(text)
        parsed = apply_faithfulness(parsed)
    normalized = normalize_intent(parsed)
    extra: dict[str, object] = {}
    if llm_parser is not None:
        extra.update(llm_parser.metadata_fields())
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    metadata = ParserMetadata(
        parser_requested=mode,
        parser_used=normalized.parser_type,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        provider=(
            extra.get("provider")
            if isinstance(extra.get("provider"), str)
            else None
        ),
        model=extra.get("model") if isinstance(extra.get("model"), str) else None,
        prompt_version=(
            extra.get("prompt_version")
            if isinstance(extra.get("prompt_version"), str)
            else None
        ),
        schema_version=(
            extra.get("schema_version")
            if isinstance(extra.get("schema_version"), str)
            else None
        ),
        repair_count=_as_int(extra.get("repair_count")) or 0,
        latency_ms=latency_ms,
        input_tokens=_as_int(extra.get("input_tokens")),
        output_tokens=_as_int(extra.get("output_tokens")),
        total_tokens=_as_int(extra.get("total_tokens")),
    )
    normalized.parser_metadata = metadata
    logger.info(
        "intent_parsed parser_requested=%s parser_used=%s provider=%s model=%s "
        "prompt_version=%s fallback_used=%s fallback_reason=%s repair_count=%s "
        "latency_ms=%.2f input_tokens=%s output_tokens=%s total_tokens=%s",
        metadata.parser_requested,
        metadata.parser_used,
        metadata.provider,
        metadata.model,
        metadata.prompt_version,
        metadata.fallback_used,
        metadata.fallback_reason,
        metadata.repair_count,
        metadata.latency_ms or 0.0,
        metadata.input_tokens,
        metadata.output_tokens,
        metadata.total_tokens,
    )
    return normalized


def _has_actionable_constraints(intent: ShoppingIntent) -> bool:
    return bool(intent.hard_constraints) or any(
        item.appears_mandatory for item in intent.ambiguities
    )


def _as_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    return None
