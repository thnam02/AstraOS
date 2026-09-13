"""Frozen Phase 2 intent evaluation fixture stays labelled and scorable."""

from app.decision.intent.models import (
    PARSER_VERSION_RULE,
    ConstraintField,
    ConstraintOperator,
    HardConstraint,
    ShoppingIntent,
)
from app.decision.intent.parser import parse_intent
from app.eval.intent_cases import load_intent_eval_cases
from app.eval.intent_metrics import gold_sets, score_case


def test_intent_eval_fixture_is_manually_labelled() -> None:
    fixture = load_intent_eval_cases()
    assert fixture["version"] == "intent_eval_v1"
    assert fixture["label_source"] == "manual"
    cases = fixture["cases"]
    assert 100 <= len(cases) <= 160
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids))
    groups = {case["group"] for case in cases}
    assert {
        "hard_constraints",
        "soft_preferences",
        "context_outcomes",
        "tradeoffs",
        "negation",
        "ambiguity",
        "values",
        "unsupported",
        "adversarial",
        "mixed",
    }.issubset(groups)
    hero = next(case for case in cases if case["id"] == "J01")
    assert "Sydney" in hero["query"]
    assert "anc" in hero["critical_hard_fields"]


async def test_rule_based_scores_frozen_hard_constraint_case() -> None:
    fixture = load_intent_eval_cases()
    case = next(item for item in fixture["cases"] if item["id"] == "A02")
    intent = await parse_intent(case["query"], parser_mode="rule_based")
    scored = score_case(intent, case)
    assert scored["hard"]["f1"] == 1.0
    assert scored["critical_omission"] is False


def test_price_normalization_matches_cents_and_dollars() -> None:
    intent = ShoppingIntent(
        raw_text="under A$350",
        hard_constraints=[
            HardConstraint(
                id="c1",
                field=ConstraintField.PRICE,
                operator=ConstraintOperator.LT,
                value=350,
                source_phrase="under A$350",
                normalized_value=35000,
            )
        ],
        parser_type="rule_based",
        parser_version=PARSER_VERSION_RULE,
    )
    case = {
        "gold": {
            "hard_constraints": [
                {"field": "price", "operator": "LT", "value": 35000}
            ]
        },
        "critical_hard_fields": ["price"],
    }
    scored = score_case(intent, case)
    assert scored["hard"]["f1"] == 1.0


def test_gold_sets_keep_canonical_ids() -> None:
    gold = gold_sets(
        {
            "gold": {
                "hard_constraints": [],
                "soft_preferences": ["comfort"],
                "contexts": ["long_haul_travel"],
                "outcomes": ["low_fatigue"],
                "values": ["sustainability"],
                "tradeoffs": ["comfort>price"],
                "ambiguities": ["unbounded_price"],
                "unsupported_semantic_needs": ["vegan_glue"],
            }
        }
    )
    assert gold["preferences"] == {"comfort"}
    assert gold["tradeoffs"] == {"comfort>price"}
    assert gold["unsupported"] == {"vegan_glue"}
