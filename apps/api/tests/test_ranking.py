"""Eligible-only ranking and deterministic tie-breaks."""

from uuid import uuid4

from app.decision.eligibility.evaluator import EligibilityEvaluator
from app.decision.intent.models import (
    ConstraintField,
    ConstraintOperator,
    ContextLabel,
    DesiredOutcome,
    IntentContext,
    OutcomeLabel,
    PreferenceDirection,
    PreferenceField,
    SoftPreference,
)
from app.decision.retrieval.documents import build_product_document
from app.decision.retrieval.embeddings import LocalEmbeddingProvider
from app.decision.retrieval.matcher import rank_eligible
from tests.qualification_fixtures import CASE1_INTENT, constraint, intent_with, snapshot

evaluator = EligibilityEvaluator()
provider = LocalEmbeddingProvider()


def _vectors(variants):
    return {
        item.variant_id: provider.embed(build_product_document(item).text)
        for item in variants
    }


def test_violated_products_never_ranked() -> None:
    expensive = snapshot(name="Vanta Studio X2", price=42900)
    cheap = snapshot(name="Aurora A9", price=22900)
    ranked = rank_eligible(CASE1_INTENT, [cheap], _vectors([cheap]), provider)
    ids = {item.variant_id for item in ranked}
    assert expensive.variant_id not in ids
    assert cheap.variant_id in ids


def test_unknown_mandatory_never_ranked() -> None:
    missing = snapshot(name="Gap", deliveries=[])
    result = evaluator.evaluate_variant(missing, CASE1_INTENT)
    assert result.eligible is False
    ranked = rank_eligible(CASE1_INTENT, [], _vectors([]), provider)
    assert ranked == []


def test_ranking_is_deterministic() -> None:
    intent = intent_with(
        constraint(ConstraintField.ANC, ConstraintOperator.EQ, True),
        context_items=[
            IntentContext(
                label=ContextLabel.LONG_HAUL_TRAVEL,
                source_phrase="long flight",
            )
        ],
        desired_outcomes=[
            DesiredOutcome(
                label=OutcomeLabel.LOW_FATIGUE,
                importance=0.8,
                source_phrase="hours",
            )
        ],
        soft_preferences=[
            SoftPreference(
                id="p1",
                field=PreferenceField.COMFORT,
                direction=PreferenceDirection.MAXIMIZE,
                importance=0.9,
                source_phrase="comfort",
            )
        ],
    )
    a = snapshot(
        name="High Comfort",
        sku="AAA-1",
        attributes={
            "anc": True,
            "comfort_score": 0.95,
            "travel_score": 0.9,
            "battery_hours": 50,
            "weight_g": 200,
            "foldable": True,
            "wireless": True,
        },
    )
    b = snapshot(
        name="Low Comfort",
        sku="ZZZ-1",
        attributes={
            "anc": True,
            "comfort_score": 0.4,
            "travel_score": 0.3,
            "battery_hours": 18,
            "weight_g": 400,
            "foldable": False,
            "wireless": True,
        },
    )
    variants = [a, b]
    first = rank_eligible(intent, variants, _vectors(variants), provider)
    second = rank_eligible(intent, variants, _vectors(variants), provider)
    assert [item.sku for item in first] == [item.sku for item in second]
    assert first[0].sku == "AAA-1"


def test_tie_break_uses_sku() -> None:
    intent = intent_with()
    left = snapshot(name="Twin", sku="AAA", attributes={})
    right = snapshot(name="Twin", sku="ZZZ", attributes={})
    left.product_id = uuid4()
    ranked = rank_eligible(intent, [right, left], _vectors([right, left]), provider)
    assert [item.sku for item in ranked] == ["AAA", "ZZZ"]


def test_reasons_cite_facts() -> None:
    intent = intent_with(
        desired_outcomes=[
            DesiredOutcome(
                label=OutcomeLabel.LOW_FATIGUE,
                importance=0.9,
                source_phrase="hours",
            )
        ]
    )
    variant = snapshot(attributes={"comfort_score": 0.91, "weight_g": 238})
    ranked = rank_eligible(intent, [variant], _vectors([variant]), provider)
    assert ranked
    reason = next(item for item in ranked[0].reasons if item.need == "low_fatigue")
    attrs = {fact.attribute for fact in reason.facts}
    assert "comfort_score" in attrs
    assert "weight_g" in attrs


def test_unsupported_need_lowers_coverage() -> None:
    from app.decision.intent.models import UnsupportedSemanticNeed

    intent = intent_with(
        desired_outcomes=[
            DesiredOutcome(
                label=OutcomeLabel.LOW_FATIGUE,
                importance=1.0,
                source_phrase="hours",
            )
        ],
        unsupported_semantic_needs=[
            UnsupportedSemanticNeed(
                label="luxurious_feel",
                source_phrase="feel luxurious",
            )
        ],
    )
    variant = snapshot(attributes={"comfort_score": 0.9, "weight_g": 200})
    ranked = rank_eligible(intent, [variant], _vectors([variant]), provider)
    assert ranked[0].evidence_coverage < 1.0
    assert "luxurious_feel" in ranked[0].unsupported_needs
