"""Deterministic pattern parser for demos, tests, and LLM fallback."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.decision.intent.models import (
    PARSER_VERSION_RULE,
    ConstraintField,
    ConstraintOperator,
    HardConstraint,
    IntentAmbiguity,
    PreferenceDirection,
    PreferenceField,
    ShoppingIntent,
    SoftPreference,
)
from app.decision.intent.normalizer import parse_money_to_cents, parse_number

PARSER_TYPE = "rule_based"


@dataclass
class _Span:
    start: int
    end: int


def _overlaps(span: _Span, others: list[_Span]) -> bool:
    return any(span.start < other.end and span.end > other.start for other in others)


class RuleBasedIntentParser:
    """Recognizes defined phrases. Not a general NLP engine."""

    parser_type = PARSER_TYPE

    async def parse(self, text: str) -> ShoppingIntent:
        consumed: list[_Span] = []
        constraints: list[HardConstraint] = []
        preferences: list[SoftPreference] = []
        tags: list[str] = []
        ambiguities: list[IntentAmbiguity] = []
        counter = 0

        def next_id(prefix: str) -> str:
            nonlocal counter
            counter += 1
            return f"{prefix}_{counter}"

        def take(match: re.Match[str]) -> bool:
            span = _Span(match.start(), match.end())
            if _overlaps(span, consumed):
                return False
            consumed.append(span)
            return True

        lowered = text

        category = None
        if re.search(r"\bheadphone", lowered, flags=re.IGNORECASE):
            category = "headphones"

        for pattern, field, operator, raw, unit in _HARD_PATTERNS:
            for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                if not take(match):
                    continue
                value: object = raw
                if field == ConstraintField.PRICE:
                    cents = parse_money_to_cents(match.group(0))
                    if cents is None:
                        continue
                    value = cents
                    unit = "AUD_CENTS"
                elif (
                    field
                    in {
                        ConstraintField.BATTERY_HOURS,
                        ConstraintField.DELIVERY_DAYS,
                        ConstraintField.WEIGHT_G,
                    }
                    and raw is None
                ):
                    number = parse_number(match.group(0))
                    if number is None:
                        continue
                    value = number
                constraints.append(
                    HardConstraint(
                        id=next_id("c"),
                        field=field,
                        operator=operator,
                        value=value,
                        unit=unit,
                        source_phrase=match.group(0).strip(),
                    )
                )

        for pattern, pref_field, direction, importance in _SOFT_PATTERNS:
            for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                if not take(match):
                    continue
                preferences.append(
                    SoftPreference(
                        id=next_id("p"),
                        field=pref_field,
                        direction=direction,
                        importance=importance,
                        source_phrase=match.group(0).strip(),
                    )
                )

        for pattern, tag in _CONTEXT_PATTERNS:
            for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                if not take(match):
                    continue
                if tag not in tags:
                    tags.append(tag)

        for pattern, reason, mandatory, suggestion in _AMBIGUITY_PATTERNS:
            for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                if not take(match):
                    continue
                ambiguities.append(
                    IntentAmbiguity(
                        source_phrase=match.group(0).strip(),
                        reason=reason,
                        appears_mandatory=mandatory,
                        suggested_resolution=suggestion,
                    )
                )

        for match in re.finditer(r"\bmust\b[^.\n]{0,40}", lowered, flags=re.IGNORECASE):
            if _overlaps(_Span(match.start(), match.end()), consumed):
                continue
            phrase = match.group(0).strip()
            if len(phrase.split()) < 2:
                continue
            consumed.append(_Span(match.start(), match.end()))
            ambiguities.append(
                IntentAmbiguity(
                    source_phrase=phrase,
                    reason="unsupported_attribute",
                    appears_mandatory=True,
                    suggested_resolution=(
                        "No supported catalogue field matches this requirement."
                    ),
                )
            )

        return ShoppingIntent(
            raw_text=text,
            category=category,
            hard_constraints=constraints,
            soft_preferences=preferences,
            context_tags=tags,
            ambiguities=ambiguities,
            parser_type=PARSER_TYPE,
            parser_version=PARSER_VERSION_RULE,
        )


_MONEY = r"(?:a\$|aud\s+|\$)\s*\d[\d,]*(?:\.\d{1,2})?"

_HARD_PATTERNS: list[
    tuple[str, ConstraintField, ConstraintOperator, object | None, str | None]
] = [
    (
        r"\b(?:no|without|not)\s+(?:noise[-\s]?cancell(?:ing|ation)|anc)\b",
        ConstraintField.ANC,
        ConstraintOperator.EQ,
        False,
        "BOOL",
    ),
    (
        r"(?:must have |need |needs |with )?(?:noise[-\s]?cancell(?:ing|ation)|anc)\b",
        ConstraintField.ANC,
        ConstraintOperator.EQ,
        True,
        "BOOL",
    ),
    (
        rf"\b(?:under|less than|below)\s+{_MONEY}",
        ConstraintField.PRICE,
        ConstraintOperator.LT,
        None,
        "AUD_CENTS",
    ),
    (
        rf"\b(?:up to|at most|no more than)\s+{_MONEY}|{_MONEY}\s+or less\b",
        ConstraintField.PRICE,
        ConstraintOperator.LTE,
        None,
        "AUD_CENTS",
    ),
    (
        rf"\b(?:more than|over|above)\s+{_MONEY}",
        ConstraintField.PRICE,
        ConstraintOperator.GT,
        None,
        "AUD_CENTS",
    ),
    (
        rf"\b(?:at least|minimum)\s+{_MONEY}",
        ConstraintField.PRICE,
        ConstraintOperator.GTE,
        None,
        "AUD_CENTS",
    ),
    (
        r"\b(?:at least|minimum)\s+\d+(?:\.\d+)?\s*"
        r"(?:hours?|hrs?)\s*(?:of\s+)?battery\b"
        r"|\bbattery(?: life)?\s*(?:of\s+)?(?:at least|minimum)\s+"
        r"\d+(?:\.\d+)?\s*(?:hours?|hrs?)\b",
        ConstraintField.BATTERY_HOURS,
        ConstraintOperator.GTE,
        None,
        "HOURS",
    ),
    (
        r"\b(?:more than|over)\s+\d+(?:\.\d+)?\s*(?:hours?|hrs?)\s*(?:of\s+)?battery\b",
        ConstraintField.BATTERY_HOURS,
        ConstraintOperator.GT,
        None,
        "HOURS",
    ),
    (
        r"\bbattery(?: life)?\s*(?:>=|at least)\s*\d+(?:\.\d+)?\s*(?:hours?|hrs?|h)?",
        ConstraintField.BATTERY_HOURS,
        ConstraintOperator.GTE,
        None,
        "HOURS",
    ),
    (
        r"\b(?:delivered|deliver|delivery|need them(?:\s+delivered)?|needed)\s+today\b"
        r"|\bsame[-\s]?day(?:\s+delivery)?\b",
        ConstraintField.DELIVERY_DAYS,
        ConstraintOperator.LTE,
        0,
        "DAYS",
    ),
    (
        r"\b(?:tomorrow|next day|next-day)\b",
        ConstraintField.DELIVERY_DAYS,
        ConstraintOperator.LTE,
        1,
        "DAYS",
    ),
    (
        r"\bwithin\s+(?:one|two|three|1|2|3)\s+days?\b",
        ConstraintField.DELIVERY_DAYS,
        ConstraintOperator.LTE,
        None,
        "DAYS",
    ),
    (r"\bin stock\b", ConstraintField.IN_STOCK, ConstraintOperator.EQ, True, "BOOL"),
    (
        r"\bout of stock\b",
        ConstraintField.IN_STOCK,
        ConstraintOperator.EQ,
        False,
        "BOOL",
    ),
    (
        r"\bwireless\b|\bbluetooth\b",
        ConstraintField.WIRELESS,
        ConstraintOperator.EQ,
        True,
        "BOOL",
    ),
    (
        r"\bwired\b",
        ConstraintField.WIRELESS,
        ConstraintOperator.EQ,
        False,
        "BOOL",
    ),
    (
        r"\bnot foldable\b|\bnon-foldable\b",
        ConstraintField.FOLDABLE,
        ConstraintOperator.EQ,
        False,
        "BOOL",
    ),
    (
        r"\bfoldable\b",
        ConstraintField.FOLDABLE,
        ConstraintOperator.EQ,
        True,
        "BOOL",
    ),
    (
        r"\b(?:under|less than)\s+\d+(?:\.\d+)?\s*(?:g|grams|kg)\b",
        ConstraintField.WEIGHT_G,
        ConstraintOperator.LT,
        None,
        "G",
    ),
    (
        r"\bmicrophone\b|\b\bmic\b",
        ConstraintField.MICROPHONE,
        ConstraintOperator.EQ,
        True,
        "BOOL",
    ),
]

_SOFT_PATTERNS: list[tuple[str, PreferenceField, PreferenceDirection, float]] = [
    (
        r"\bcomfort(?:able)?(?:\s+matters(?:\s+a lot)?)?",
        PreferenceField.COMFORT,
        PreferenceDirection.MAXIMIZE,
        0.9,
    ),
    (
        r"\breliab(?:le|ility)",
        PreferenceField.RELIABILITY,
        PreferenceDirection.MAXIMIZE,
        0.85,
    ),
    (
        r"\b(?:prefer(?:ably)?\s+)?light(?:weight)?\b",
        PreferenceField.WEIGHT,
        PreferenceDirection.MINIMIZE,
        0.7,
    ),
    (
        r"\bcheapest is not\b"
        r"|\bnot (?:that |the )?absolute cheapest\b"
        r"|\bmore than getting the absolute cheapest\b",
        PreferenceField.PRICE,
        PreferenceDirection.MINIMIZE,
        0.3,
    ),
    (
        r"\bcheapest\b|\bbudget\b",
        PreferenceField.PRICE,
        PreferenceDirection.MINIMIZE,
        0.85,
    ),
    (
        r"\blong(?:er)? battery\b|\bbattery (?:life )?matters\b",
        PreferenceField.BATTERY,
        PreferenceDirection.MAXIMIZE,
        0.7,
    ),
    (
        r"\btravel(?:[- ]suitable| suitability)?\b",
        PreferenceField.TRAVEL,
        PreferenceDirection.MAXIMIZE,
        0.7,
    ),
    (
        r"\bwarranty matters\b|\bprefer(?:ably)? (?:a )?longer warranty\b",
        PreferenceField.WARRANTY,
        PreferenceDirection.MAXIMIZE,
        0.65,
    ),
    (
        r"\bprefer(?:ably)? (?:fast|faster|quick)(?:er)? delivery\b",
        PreferenceField.DELIVERY,
        PreferenceDirection.MINIMIZE,
        0.65,
    ),
]

_CONTEXT_PATTERNS: list[tuple[str, str]] = [
    (
        r"\b(?:12[-\s]?hour flight|long(?:er)? (?:haul )?flight|"
        r"long[-\s]?haul)\b",
        "long_haul_travel",
    ),
    (r"\bfrequent(?:ly)? travel", "frequent_travel"),
    (r"\bcommut", "commuting"),
    (r"\bgaming\b", "gaming"),
    (r"\bstudio\b", "studio"),
    (r"\b(?:sports?|running|gym)\b", "sports"),
    (r"\boffice\b", "office"),
]

_AMBIGUITY_PATTERNS: list[tuple[str, str, bool, str]] = [
    (
        r"\b(?:must look )?luxurious(?: appearance)?\b|\blook luxurious\b",
        "unsupported_attribute",
        True,
        "Appearance is not a catalogue field.",
    ),
    (
        r"\b(?:no )?animal leather\b|\bleather[-\s]?free\b",
        "unsupported_attribute",
        True,
        "Material/composition is not an authoritative catalogue field.",
    ),
]
