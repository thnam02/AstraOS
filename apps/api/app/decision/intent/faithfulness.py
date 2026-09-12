"""Deterministic safety checks on extracted intent. No commercial authority."""

from __future__ import annotations

import re

from app.decision.intent.models import (
    ConstraintField,
    ConstraintOperator,
    HardConstraint,
    IntentAmbiguity,
    PreferenceDirection,
    PreferenceField,
    ShoppingIntent,
    SoftPreference,
)

_SOFT_ONLY = re.compile(
    r"\b(prefer|preferably|nice if|would be nice|it would be nice|"
    r"i like|i'd like|would like|optional|if possible)\b",
    flags=re.IGNORECASE,
)
_MANDATORY = re.compile(
    r"\b(must|need|needed|require|required|only|mandatory|have to|"
    r"has to|under|no more than|at most|at least|within|today|"
    r"same[- ]day|don't want|do not want|no )\b",
    flags=re.IGNORECASE,
)
_INJECTION = re.compile(
    r"(ignore .{0,48}(instructions|polic|prompt))"
    r"|(reveal (your )?(hidden )?prompt)"
    r"|(return sql)"
    r"|((give|set) (me )?(a )?(90|99)% discount)"
    r"|(set price to)"
    r"|(mark every product eligible)"
    r"|(policy does not apply)"
    r"|(margin floor)"
    r"|(sell this for a dollar)"
    r"|(pretend .{0,40}(policy|margin|eligible))",
    flags=re.IGNORECASE,
)
_DELIVERY_CONFLICT = re.compile(
    r"delivery speed (does not|doesn't) matter|don'?t care about delivery",
    flags=re.IGNORECASE,
)
_PREF_FIELD = {
    ConstraintField.ANC: None,
    ConstraintField.PRICE: PreferenceField.PRICE,
    ConstraintField.BATTERY_HOURS: PreferenceField.BATTERY,
    ConstraintField.WEIGHT_G: PreferenceField.WEIGHT,
    ConstraintField.DELIVERY_DAYS: PreferenceField.DELIVERY,
    ConstraintField.SAME_DAY_DELIVERY: PreferenceField.DELIVERY,
}


def apply_faithfulness(intent: ShoppingIntent) -> ShoppingIntent:
    """Demote inferred-as-mandatory constraints and record injection attempts."""
    kept: list[HardConstraint] = []
    preferences = list(intent.soft_preferences)
    ambiguities = list(intent.ambiguities)
    for constraint in intent.hard_constraints:
        phrase = constraint.source_phrase or ""
        if _SOFT_ONLY.search(phrase) and not _MANDATORY.search(phrase):
            mapped = _PREF_FIELD.get(constraint.field)
            if mapped is not None:
                preferences.append(
                    SoftPreference(
                        id=f"faithful_{constraint.id}",
                        field=mapped,
                        direction=(
                            PreferenceDirection.MINIMIZE
                            if constraint.field
                            in {
                                ConstraintField.PRICE,
                                ConstraintField.WEIGHT_G,
                                ConstraintField.DELIVERY_DAYS,
                            }
                            else PreferenceDirection.MAXIMIZE
                        ),
                        importance=0.6,
                        source_phrase=constraint.source_phrase,
                    )
                )
            ambiguities.append(
                IntentAmbiguity(
                    source_phrase=constraint.source_phrase,
                    reason="inferred_preference_not_mandatory",
                    suggested_resolution="Kept as a soft preference.",
                    appears_mandatory=False,
                )
            )
            continue
        kept.append(constraint)

    if _INJECTION.search(intent.raw_text) and not any(
        item.reason == "prompt_injection" for item in ambiguities
    ):
        ambiguities.append(
            IntentAmbiguity(
                source_phrase=intent.raw_text[:160],
                reason="prompt_injection",
                suggested_resolution=(
                    "Buyer instructions cannot change merchant policy."
                ),
                appears_mandatory=False,
            )
        )
    _flag_price_contradiction(kept, ambiguities)
    _flag_brand_contradiction(kept, ambiguities)
    if _DELIVERY_CONFLICT.search(intent.raw_text) and any(
        item.field
        in {ConstraintField.DELIVERY_DAYS, ConstraintField.SAME_DAY_DELIVERY}
        for item in kept
    ):
        ambiguities.append(
            IntentAmbiguity(
                source_phrase=intent.raw_text[:160],
                reason="contradictory_constraints",
                suggested_resolution=(
                    "Same-day is required, but delivery was also dismissed."
                ),
                appears_mandatory=True,
            )
        )
    return intent.model_copy(
        update={
            "hard_constraints": kept,
            "soft_preferences": preferences,
            "ambiguities": ambiguities,
        }
    )


def _flag_price_contradiction(
    constraints: list[HardConstraint], ambiguities: list[IntentAmbiguity]
) -> None:
    prices = [item for item in constraints if item.field == ConstraintField.PRICE]
    if len(prices) < 2:
        return
    values = []
    for item in prices:
        try:
            values.append(
                (
                    item.operator.value,
                    float(item.normalized_value or item.value),
                )
            )
        except (TypeError, ValueError):
            return
    max_caps = [v for op, v in values if op in {"LT", "LTE"}]
    min_floors = [v for op, v in values if op in {"GT", "GTE"}]
    if max_caps and min_floors and min(min_floors) >= max(max_caps):
        ambiguities.append(
            IntentAmbiguity(
                source_phrase="price constraints",
                reason="contradictory_constraints",
                suggested_resolution="Buyer stated incompatible price bounds.",
                appears_mandatory=True,
            )
        )


def _flag_brand_contradiction(
    constraints: list[HardConstraint], ambiguities: list[IntentAmbiguity]
) -> None:
    brands = [item for item in constraints if item.field == ConstraintField.BRAND]
    if len(brands) < 2:
        return
    positives = {
        str(item.normalized_value if item.normalized_value is not None else item.value)
        .strip()
        .lower()
        for item in brands
        if item.operator in {ConstraintOperator.EQ, ConstraintOperator.IN}
    }
    negatives = {
        str(item.normalized_value if item.normalized_value is not None else item.value)
        .strip()
        .lower()
        for item in brands
        if item.operator in {ConstraintOperator.NE, ConstraintOperator.NOT_IN}
    }
    if positives & negatives:
        ambiguities.append(
            IntentAmbiguity(
                source_phrase="brand constraints",
                reason="contradictory_constraints",
                suggested_resolution="Buyer both required and excluded the same brand.",
                appears_mandatory=True,
            )
        )
