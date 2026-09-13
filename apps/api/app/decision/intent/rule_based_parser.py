"""Deterministic pattern parser for demos, tests, and LLM fallback."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.decision.intent.models import (
    PARSER_VERSION_RULE,
    ConstraintField,
    ConstraintOperator,
    DesiredOutcome,
    HardConstraint,
    IntentAmbiguity,
    IntentContext,
    PreferenceDirection,
    PreferenceField,
    ShoppingIntent,
    SoftPreference,
    TradeoffPreference,
    UnsupportedSemanticNeed,
)
from app.decision.intent.normalizer import parse_money_to_cents, parse_number
from app.decision.intent.taxonomy import (
    ContextLabel,
    OutcomeLabel,
    TradeoffDimension,
)

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
        context_items: list[IntentContext] = []
        outcomes: list[DesiredOutcome] = []
        tradeoffs: list[TradeoffPreference] = []
        unsupported: list[UnsupportedSemanticNeed] = []
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

        seen_ctx: set[str] = set()
        for pattern, ctx_label, importance in _CONTEXT_ITEMS:
            for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                if ctx_label.value in seen_ctx:
                    continue
                seen_ctx.add(ctx_label.value)
                tags.append(ctx_label.value)
                context_items.append(
                    IntentContext(
                        label=ctx_label,
                        importance=importance,
                        source_phrase=match.group(0).strip(),
                        confidence=0.85,
                    )
                )

        seen_out: set[str] = set()
        for pattern, out_label, importance in _OUTCOME_PATTERNS:
            for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                if out_label.value in seen_out:
                    continue
                seen_out.add(out_label.value)
                outcomes.append(
                    DesiredOutcome(
                        label=out_label,
                        importance=importance,
                        source_phrase=match.group(0).strip(),
                        confidence=0.8,
                    )
                )

        seen_trade: set[tuple[str, str]] = set()
        for pattern, preferred, over, strength in _TRADEOFF_PATTERNS:
            for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                key = (preferred.value, over.value)
                if key in seen_trade:
                    continue
                seen_trade.add(key)
                tradeoffs.append(
                    TradeoffPreference(
                        preferred_dimension=preferred,
                        over_dimension=over,
                        strength=strength,
                        source_phrase=match.group(0).strip(),
                    )
                )

        if (
            ContextLabel.LONG_HAUL_TRAVEL.value in seen_ctx
            and OutcomeLabel.TRAVEL_CONVENIENCE.value not in seen_out
        ):
            source = next(
                item.source_phrase
                for item in context_items
                if item.label == ContextLabel.LONG_HAUL_TRAVEL
            )
            seen_out.add(OutcomeLabel.TRAVEL_CONVENIENCE.value)
            outcomes.append(
                DesiredOutcome(
                    label=OutcomeLabel.TRAVEL_CONVENIENCE,
                    importance=0.75,
                    source_phrase=source,
                    confidence=0.75,
                )
            )
        pref_fields = {item.field for item in preferences}
        if (
            PreferenceField.RELIABILITY in pref_fields
            and ContextLabel.EXTENDED_CONTINUOUS_USE.value in seen_ctx
            and OutcomeLabel.RELIABLE_EXTENDED_USE.value not in seen_out
        ):
            source = next(
                (
                    item.source_phrase
                    for item in context_items
                    if item.label == ContextLabel.EXTENDED_CONTINUOUS_USE
                ),
                "reliability",
            )
            seen_out.add(OutcomeLabel.RELIABLE_EXTENDED_USE.value)
            outcomes.append(
                DesiredOutcome(
                    label=OutcomeLabel.RELIABLE_EXTENDED_USE,
                    importance=0.8,
                    source_phrase=source,
                    confidence=0.75,
                )
            )

        for pattern, need_label, reason in _UNSUPPORTED_SEMANTIC:
            for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                if _overlaps(_Span(match.start(), match.end()), consumed):
                    continue
                consumed.append(_Span(match.start(), match.end()))
                unsupported.append(
                    UnsupportedSemanticNeed(
                        label=need_label,
                        source_phrase=match.group(0).strip(),
                        reason=reason,
                    )
                )

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
            context_items=context_items,
            desired_outcomes=outcomes,
            values=[],
            tradeoffs=tradeoffs,
            unsupported_semantic_needs=unsupported,
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
        rf"\b(?:base(?:\s+product)?\s+price|product[- ]only(?:\s+price)?)\s+"
        rf"(?:under|less than|below)\s+{_MONEY}",
        ConstraintField.PRICE,
        ConstraintOperator.LT,
        None,
        "AUD_CENTS",
    ),
    (
        rf"\b(?:base(?:\s+product)?\s+price|product[- ]only(?:\s+price)?)\s+"
        rf"(?:up to|at most|no more than|maximum(?:\s+of)?)\s+{_MONEY}",
        ConstraintField.PRICE,
        ConstraintOperator.LTE,
        None,
        "AUD_CENTS",
    ),
    (
        rf"\b(?:under|less than|below)\s+{_MONEY}",
        ConstraintField.PRICE,
        ConstraintOperator.LT,
        None,
        "AUD_CENTS",
    ),
    (
        rf"\b(?:up to|at most|no more than|maximum(?:\s+of)?|max(?:imum)?)\s+{_MONEY}"
        rf"|{_MONEY}\s+or less\b",
        ConstraintField.PRICE,
        ConstraintOperator.LTE,
        None,
        "AUD_CENTS",
    ),
    (
        rf"\bbudget(?:\s+is|\s+of)?\s+{_MONEY}",
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
        r"\b(?:deliver(?:ed|y)?|arrive)\s+(?:by\s+)?tomorrow\b"
        r"|\btomorrow(?:'s)?\s+delivery\b",
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

_CONTEXT_ITEMS: list[tuple[str, ContextLabel, float]] = [
    (
        r"\b(?:12[-\s]?hour flight|long(?:er)? (?:haul )?flight|"
        r"long[-\s]?haul|international flight|"
        r"sydney to singapore|singapore to sydney)\b",
        ContextLabel.LONG_HAUL_TRAVEL,
        0.9,
    ),
    (
        r"\bwear (?:them|it) for hours\b|\bfor hours\b|"
        r"\bextended (?:wear|use|listening)\b",
        ContextLabel.EXTENDED_CONTINUOUS_USE,
        0.85,
    ),
    (r"\bfrequent(?:ly)? travel", ContextLabel.FREQUENT_TRAVEL, 0.75),
    (r"\bshort (?:trip|flight|commute)\b", ContextLabel.SHORT_TRAVEL, 0.7),
    (r"\bcommut", ContextLabel.COMMUTING, 0.75),
    (r"\bgaming\b", ContextLabel.GAMING, 0.8),
    (r"\bstudio\b", ContextLabel.STUDIO, 0.8),
    (r"\b(?:sports?|running|gym)\b", ContextLabel.SPORTS, 0.75),
    (r"\boffice\b", ContextLabel.OFFICE, 0.7),
]

_OUTCOME_PATTERNS: list[tuple[str, OutcomeLabel, float]] = [
    (
        r"\bwear (?:them|it) for hours\b|\bcomfort matters\b|"
        r"\blow fatigue\b|\bfor hours\b",
        OutcomeLabel.LOW_FATIGUE,
        0.85,
    ),
    (
        r"\breliab(?:le|ility).{0,40}(?:hours|extended|flight|travel)"
        r"|(?:hours|extended|flight).{0,40}reliab(?:le|ility)"
        r"|\breliable extended\b|\bneed them (?:to )?last\b",
        OutcomeLabel.RELIABLE_EXTENDED_USE,
        0.8,
    ),
    (
        r"\bnoise[-\s]?cancell|\banc\b|\bisolation\b",
        OutcomeLabel.STRONG_NOISE_ISOLATION,
        0.7,
    ),
    (
        r"\blong(?:er)? battery\b|\bbattery (?:life )?matters\b",
        OutcomeLabel.LONG_BATTERY_ENDURANCE,
        0.75,
    ),
    (
        r"\b(?:12[-\s]?hour flight|long(?:er)? (?:haul )?flight|"
        r"long[-\s]?haul|international flight|sydney to singapore|"
        r"travel convenien)",
        OutcomeLabel.TRAVEL_CONVENIENCE,
        0.8,
    ),
    (r"\bfoldable\b|\bpack(?:able)?\b", OutcomeLabel.EASY_STORAGE, 0.65),
    (r"\bportable\b|\blightweight travel\b", OutcomeLabel.PORTABLE_TRAVEL, 0.7),
    (r"\bcalls?\b|\bmicrophone\b|\bpodcast", OutcomeLabel.CLEAR_CALLS, 0.7),
    (r"\bimmersive\b|\bgaming\b", OutcomeLabel.IMMERSIVE_AUDIO, 0.65),
    (r"\bwaterproof\b|\bIPX", OutcomeLabel.WEATHER_RESILIENCE, 0.65),
]

_TRADEOFF_PATTERNS: list[tuple[str, TradeoffDimension, TradeoffDimension, float]] = [
    (
        r"comfort and reliability matter more than getting the absolute cheapest"
        r"|comfort and reliability matter more than .{0,20}cheapest",
        TradeoffDimension.COMFORT,
        TradeoffDimension.PRICE,
        0.8,
    ),
    (
        r"reliability matter more than .{0,30}cheapest"
        r"|rather pay more for reliability"
        r"|reliability than get the cheapest",
        TradeoffDimension.RELIABILITY,
        TradeoffDimension.PRICE,
        0.8,
    ),
    (
        r"comfort matters more than .{0,20}(?:price|cheapest)",
        TradeoffDimension.COMFORT,
        TradeoffDimension.PRICE,
        0.75,
    ),
]

_UNSUPPORTED_SEMANTIC: list[tuple[str, str, str]] = [
    (
        r"\bfeel luxurious\b|\bluxury feel\b",
        "luxurious_feel",
        "no_merchant_attribute",
    ),
    (
        r"\bsustainab(?:le|ility)\b",
        "sustainability",
        "no_merchant_attribute",
    ),
    (
        r"\brepairab(?:le|ility)\b",
        "repairability",
        "no_merchant_attribute",
    ),
    (
        r"\bdurab(?:le|ility)\b",
        "durability",
        "no_merchant_attribute",
    ),
]

_AMBIGUITY_PATTERNS: list[tuple[str, str, bool, str]] = [
    (
        r"\b(?:must look |must feel )?luxurious(?: appearance| feel)?\b"
        r"|\blook luxurious\b|\bfeel luxurious\b",
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
