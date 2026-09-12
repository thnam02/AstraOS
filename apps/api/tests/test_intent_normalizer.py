"""Normalisation layer tests."""

from app.decision.intent.models import (
    PARSER_VERSION_RULE,
    ConstraintField,
    ConstraintOperator,
    HardConstraint,
    IntentAmbiguity,
    IntentStatus,
    ShoppingIntent,
)
from app.decision.intent.normalizer import (
    dollars_to_cents,
    normalize_intent,
    normalize_weight_grams,
    parse_money_to_cents,
)


def test_dollars_to_cents() -> None:
    assert dollars_to_cents(350) == 35000
    assert dollars_to_cents("350.00") == 35000


def test_parse_money_australian_forms() -> None:
    assert parse_money_to_cents("A$350") == 35000
    assert parse_money_to_cents("AUD 350") == 35000
    assert parse_money_to_cents("$350") == 35000


def test_kg_to_grams() -> None:
    assert normalize_weight_grams("0.25kg") == 250
    assert normalize_weight_grams("250g") == 250


def test_normalize_price_and_today() -> None:
    raw = ShoppingIntent(
        raw_text="under $350 delivered today",
        hard_constraints=[
            HardConstraint(
                id="c1",
                field=ConstraintField.PRICE,
                operator=ConstraintOperator.LT,
                value=350,
                source_phrase="under $350",
            ),
            HardConstraint(
                id="c2",
                field=ConstraintField.SAME_DAY_DELIVERY,
                operator=ConstraintOperator.EQ,
                value=True,
                source_phrase="today",
            ),
        ],
        parser_type="rule_based",
        parser_version=PARSER_VERSION_RULE,
    )
    normalized = normalize_intent(raw)
    price = next(
        item
        for item in normalized.hard_constraints
        if item.field == ConstraintField.PRICE
    )
    delivery = next(
        item
        for item in normalized.hard_constraints
        if item.field == ConstraintField.DELIVERY_DAYS
    )
    assert price.normalized_value == 35000
    assert price.unit == "AUD_CENTS"
    assert delivery.operator == ConstraintOperator.LTE
    assert delivery.normalized_value == 0


def test_normalize_weight_from_phrase() -> None:
    raw = ShoppingIntent(
        raw_text="under 0.25kg",
        hard_constraints=[
            HardConstraint(
                id="c1",
                field=ConstraintField.WEIGHT_G,
                operator=ConstraintOperator.LT,
                value=0.25,
                source_phrase="under 0.25kg",
            )
        ],
        parser_type="rule_based",
        parser_version=PARSER_VERSION_RULE,
    )
    normalized = normalize_intent(raw)
    assert normalized.hard_constraints[0].normalized_value == 250
    assert normalized.hard_constraints[0].unit == "G"


def test_mandatory_ambiguity_needs_clarification() -> None:
    raw = ShoppingIntent(
        raw_text="ANC and must look luxurious",
        category="headphones",
        hard_constraints=[
            HardConstraint(
                id="c1",
                field=ConstraintField.ANC,
                operator=ConstraintOperator.EQ,
                value=True,
                source_phrase="ANC",
            )
        ],
        ambiguities=[
            IntentAmbiguity(
                source_phrase="must look luxurious",
                reason="unsupported_attribute",
                appears_mandatory=True,
            )
        ],
        parser_type="rule_based",
        parser_version=PARSER_VERSION_RULE,
    )
    assert normalize_intent(raw).status == IntentStatus.NEEDS_CLARIFICATION
