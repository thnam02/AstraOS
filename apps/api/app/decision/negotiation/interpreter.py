"""Interpret buyer language. Never constructs an offer or sets a price."""

from __future__ import annotations

import re
from typing import Protocol

from app.decision.negotiation.models import (
    BuyerAction,
    BuyerTurnInput,
    CounterConstraints,
    InterpretedBuyerTurn,
)

_INJECTION = re.compile(
    r"(ignore (all |previous |the )?(instructions|rules|merchant)|"
    r"waive (the )?(margin|policy)|"
    r"you are now|jailbreak|system prompt|"
    r"override (merchant )?policy)",
    re.IGNORECASE,
)

_ACCEPT = re.compile(
    r"\b(i('?ll take it| accept)|accepted|it'?s a deal|sounds good|"
    r"lock it in|yes,? (please|deal)|deal)\b",
    re.IGNORECASE,
)

_REJECT = re.compile(
    r"\b(no thanks|not interested|forget it|reject(ed)?|walk away|"
    r"cancel( the)? (deal|order)?)\b",
    re.IGNORECASE,
)

_PRICE = re.compile(
    r"(?:below|under|less than|max(?:imum)?(?: total)?|at most|"
    r"get (?:this|it) (?:below|under))\s*"
    r"(?:a\$|aud\s*)?\$?\s*([\d,]+)",
    re.IGNORECASE,
)

_PRICE_BARE = re.compile(
    r"(?:a\$|aud\s*|\$)\s*([\d,]+)",
    re.IGNORECASE,
)

# "I want it 180" / "want 250" / "take it for 200" — dollars without a $ mark.
_PRICE_STATED = re.compile(
    r"(?:want(?:\s+(?:it|this|them))?|for|pay(?:\s+up\s+to)?|"
    r"take(?:\s+it)?(?:\s+for)?|offer(?:\s+me)?)\s+"
    r"(?:a\$|aud\s*|\$)?\s*([\d,]+)(?!\d)(?!\s*(?:month|mo|year|yr))",
    re.IGNORECASE,
)

# Entire message is just an amount, e.g. "180" or "A$180".
_PRICE_STANDALONE = re.compile(
    r"^\s*(?:a\$|aud\s*|\$)?\s*([\d,]+)\s*[.!?]?\s*$",
    re.IGNORECASE,
)

_WARRANTY_MONTHS = re.compile(
    r"(\d+)\s*(?:month|mo)s?\s+warranty",
    re.IGNORECASE,
)
_WARRANTY_YEARS = re.compile(
    r"(\d+)\s*(?:year|yr)s?\s+warranty",
    re.IGNORECASE,
)
_LONGER_WARRANTY = re.compile(
    r"(longer|extended|better)\s+warranty",
    re.IGNORECASE,
)

_RELAX_TODAY = re.compile(
    r"(don'?t need (it )?today|standard delivery|"
    r"no longer (need )?same[ -]?day|two[ -]?day is fine)",
    re.IGNORECASE,
)

_SAME_DAY = re.compile(r"\b(today|same[ -]?day)\b", re.IGNORECASE)
_FOLDABLE = re.compile(r"\bfoldable\b", re.IGNORECASE)
_AMBIGUOUS = re.compile(
    r"\b(make it better|do better|improve it|nicer)\b",
    re.IGNORECASE,
)
_CHEAPER = re.compile(r"\b(cheaper|lower the price|discount)\b", re.IGNORECASE)


class NegotiationMessageInterpreter(Protocol):
    def interpret(self, payload: BuyerTurnInput) -> InterpretedBuyerTurn: ...


def _cents(raw: str) -> int:
    value = int(raw.replace(",", ""))
    if value < 1000:
        return value * 100
    return value


def _merge(
    structured: CounterConstraints, extracted: CounterConstraints
) -> CounterConstraints:
    data = extracted.model_dump()
    incoming = structured.model_dump(exclude_unset=False)
    for key, value in incoming.items():
        if key == "preference_changes" and value:
            data[key] = list({*data.get(key, []), *value})
        elif value not in (None, False, [], ""):
            data[key] = value
        elif key == "relax_same_day" and structured.relax_same_day:
            data[key] = True
        elif key == "alternative_product_allowed":
            data[key] = structured.alternative_product_allowed
    return CounterConstraints.model_validate(data)


class RuleBasedNegotiationInterpreter:
    """Deterministic classifier used by tests and the default API path."""

    def interpret(self, payload: BuyerTurnInput) -> InterpretedBuyerTurn:
        text = (payload.message or "").strip()
        extracted = CounterConstraints()
        notes: list[str] = []
        injection = bool(text and _INJECTION.search(text))
        if injection:
            notes.append("Ignored an instruction that tried to override policy.")

        if text:
            priced = (
                _PRICE.search(text)
                or _PRICE_BARE.search(text)
                or _PRICE_STATED.search(text)
                or _PRICE_STANDALONE.search(text)
            )
            if priced:
                extracted.max_total_price_cents = _cents(priced.group(1))
            if match := _WARRANTY_MONTHS.search(text):
                extracted.requested_warranty_months = int(match.group(1))
            elif match := _WARRANTY_YEARS.search(text):
                extracted.requested_warranty_months = int(match.group(1)) * 12
            elif _LONGER_WARRANTY.search(text):
                extracted.requested_warranty_months = 24
            if _RELAX_TODAY.search(text):
                extracted.relax_same_day = True
                extracted.requested_delivery_days = 2
            elif _SAME_DAY.search(text) and extracted.max_total_price_cents is None:
                extracted.requested_delivery_days = 0
            if _FOLDABLE.search(text):
                extracted.foldable_required = True
            if _CHEAPER.search(text):
                extracted.preference_changes.append("lower_price")

        constraints = _merge(payload.constraints, extracted)
        actionable = _has_commercial_ask(constraints)

        if payload.action is not None:
            return InterpretedBuyerTurn(
                action=payload.action,
                constraints=constraints,
                raw_message=payload.message,
                prompt_injection=injection,
                ambiguous=payload.action == BuyerAction.ASK_CLARIFICATION,
                source="structured",
                notes=notes,
            )

        if injection and not actionable:
            return InterpretedBuyerTurn(
                action=BuyerAction.ASK_CLARIFICATION,
                constraints=constraints,
                raw_message=payload.message,
                prompt_injection=True,
                ambiguous=True,
                notes=[*notes, "No supported commercial change was extracted."],
            )
        if text and _ACCEPT.search(text) and not actionable:
            return InterpretedBuyerTurn(
                action=BuyerAction.ACCEPT,
                constraints=constraints,
                raw_message=payload.message,
                prompt_injection=injection,
                notes=notes,
            )
        if text and _REJECT.search(text) and not actionable:
            return InterpretedBuyerTurn(
                action=BuyerAction.REJECT,
                constraints=constraints,
                raw_message=payload.message,
                prompt_injection=injection,
                notes=notes,
            )
        if actionable:
            return InterpretedBuyerTurn(
                action=BuyerAction.COUNTER,
                constraints=constraints,
                raw_message=payload.message,
                prompt_injection=injection,
                notes=notes,
            )
        if text and _AMBIGUOUS.search(text):
            return InterpretedBuyerTurn(
                action=BuyerAction.ASK_CLARIFICATION,
                constraints=constraints,
                raw_message=payload.message,
                ambiguous=True,
                notes=["Message is not machine-actionable."],
            )
        if text:
            return InterpretedBuyerTurn(
                action=BuyerAction.ASK_CLARIFICATION,
                constraints=constraints,
                raw_message=payload.message,
                ambiguous=True,
                notes=["Could not extract a commercial action."],
            )
        return InterpretedBuyerTurn(
            action=BuyerAction.ASK_CLARIFICATION,
            constraints=constraints,
            raw_message=payload.message,
            ambiguous=True,
        )


def _has_commercial_ask(constraints: CounterConstraints) -> bool:
    return any(
        [
            constraints.max_total_price_cents is not None,
            constraints.requested_delivery_days is not None,
            constraints.relax_same_day,
            constraints.requested_warranty_months is not None,
            constraints.requested_bundle is not None,
            constraints.requested_return_window_days is not None,
            constraints.foldable_required is not None,
            bool(constraints.preference_changes),
        ]
    )


def default_interpreter() -> RuleBasedNegotiationInterpreter:
    return RuleBasedNegotiationInterpreter()
