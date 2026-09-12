"""LLM ShoppingIntent objects must feed unchanged deterministic services."""

from datetime import UTC, datetime, timedelta

from app.decision.eligibility.evaluator import EligibilityEvaluator
from app.decision.intent.llm_parser import LLMIntentParser
from app.decision.intent.normalizer import normalize_intent
from app.decision.offers.bundles import relevant_bundle_codes
from app.decision.offers.constructor import construct_variant
from app.decision.offers.models import ConstructionLimits
from app.decision.optimisation.engine import score_space
from app.decision.retrieval.documents import build_product_document
from app.decision.retrieval.embeddings import LocalEmbeddingProvider
from app.decision.retrieval.matcher import rank_eligible
from tests.offer_fixtures import wired_variant
from tests.qualification_fixtures import snapshot
from tests.test_llm_parser import _FakeClient


def _hero_payload() -> dict[str, object]:
    return {
        "category": "headphones",
        "hard_constraints": [
            {
                "field": "anc",
                "operator": "EQ",
                "value": True,
                "source_phrase": "noise-cancelling",
                "explicit_mandatory": True,
            },
            {
                "field": "wireless",
                "operator": "EQ",
                "value": True,
                "source_phrase": "wireless",
                "explicit_mandatory": True,
            },
            {
                "field": "price",
                "operator": "LT",
                "value": 350,
                "source_phrase": "under A$350",
                "explicit_mandatory": True,
            },
            {
                "field": "delivery_days",
                "operator": "LTE",
                "value": 0,
                "source_phrase": "delivered today",
                "explicit_mandatory": True,
            },
        ],
        "soft_preferences": [
            {
                "field": "comfort",
                "direction": "MAXIMIZE",
                "importance": 0.9,
                "source_phrase": "comfort and reliability matter",
            }
        ],
        "context_items": [
            {
                "label": "long_haul_travel",
                "importance": 0.8,
                "source_phrase": "flying from Sydney to Singapore",
            }
        ],
        "desired_outcomes": [
            {
                "label": "low_fatigue",
                "importance": 0.8,
                "source_phrase": "wear them for hours",
            }
        ],
        "values": [],
        "tradeoffs": [
            {
                "preferred_dimension": "comfort",
                "over_dimension": "price",
                "strength": 0.8,
                "source_phrase": "comfort and reliability matter more",
            }
        ],
        "ambiguities": [],
        "unsupported_semantic_needs": [],
        "context_tags": ["long_haul_travel"],
    }


async def test_llm_intent_qualifies_without_conversion_hacks() -> None:
    parsed = await LLMIntentParser(client=_FakeClient(_hero_payload())).parse(
        "wireless ANC headphones under A$350"
    )
    intent = normalize_intent(parsed)
    result = EligibilityEvaluator().evaluate_variant(snapshot(), intent)
    assert result.outcome in {"eligible", "violated", "uncertain"}
    assert result.evaluations


async def test_llm_intent_survives_qualify_match_construct_optimise() -> None:
    parsed = await LLMIntentParser(client=_FakeClient(_hero_payload())).parse(
        "wireless ANC under A$350 delivered today"
    )
    intent = normalize_intent(parsed)
    eligible = snapshot(
        name="Aurora Commute 06",
        price=28900,
        attributes={"anc": True, "wireless": True, "foldable": True},
    )
    result = EligibilityEvaluator().evaluate_variant(eligible, intent)
    assert result.outcome in {"eligible", "uncertain"}

    provider = LocalEmbeddingProvider()
    ranked = rank_eligible(intent, [eligible], {eligible.variant_id: provider.embed(
        build_product_document(eligible).text
    )}, provider)
    assert ranked
    assert ranked[0].variant_id == eligible.variant_id

    variant, policy = wired_variant()
    offers, dims = construct_variant(
        variant=variant,
        intent=intent,
        policy=policy,
        relevant_bundles=relevant_bundle_codes(intent),
        limits=ConstructionLimits(),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    assert dims["estimated"] >= 1
    assert offers

    engine = score_space(
        offers,
        intent=intent,
        policy=policy,
        variants={variant.id: variant},
        product_fits={variant.id: 0.8},
        profile_id="INTENT_ADAPTED",
    )
    assert engine.recommended is not None or engine.scored
