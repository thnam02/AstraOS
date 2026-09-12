"""Eligible-only retrieval and document versioning."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.decision.eligibility.evaluator import EligibilityEvaluator
from app.decision.intent.models import ConstraintField, ConstraintOperator
from app.decision.retrieval.documents import (
    DOCUMENT_VERSION,
    build_product_document,
    document_hash,
)
from app.decision.retrieval.embeddings import LocalEmbeddingProvider
from app.decision.retrieval.matcher import rank_by_similarity, rank_eligible
from tests.qualification_fixtures import CASE1_INTENT, constraint, intent_with, snapshot

provider = LocalEmbeddingProvider()
evaluator = EligibilityEvaluator()


def test_document_hash_changes_with_facts() -> None:
    light = snapshot(
        attributes={"wireless": True, "battery_hours": 79, "weight_g": 230}
    )
    heavy = snapshot(
        attributes={"wireless": True, "battery_hours": 12, "weight_g": 410}
    )
    first = build_product_document(light)
    second = build_product_document(heavy)
    assert first.version == DOCUMENT_VERSION
    assert document_hash(first) != document_hash(second)
    assert document_hash(first) == document_hash(first.text)


def test_expensive_product_never_enters_semantic_rank() -> None:
    intent = intent_with(
        constraint(ConstraintField.PRICE, ConstraintOperator.LT, 20000)
    )
    cheap = snapshot(name="Budget Travel", price=14900, sku="BUD-1")
    expensive = snapshot(
        name="Luxury Cabin",
        price=39900,
        sku="LUX-1",
        attributes={
            "anc": True,
            "wireless": True,
            "battery_hours": 90,
            "weight_g": 220,
            "travel_score": 0.99,
            "comfort_score": 0.99,
            "foldable": True,
        },
    )
    results = [
        evaluator.evaluate_variant(cheap, intent),
        evaluator.evaluate_variant(expensive, intent),
    ]
    eligible = [
        variant
        for variant, result in zip([cheap, expensive], results, strict=True)
        if result.outcome == "eligible"
    ]
    assert expensive.variant_id not in {item.variant_id for item in eligible}
    vectors = {
        cheap.variant_id: provider.embed(build_product_document(cheap).text),
        expensive.variant_id: provider.embed(build_product_document(expensive).text),
    }
    ranked = rank_eligible(intent, eligible, vectors, provider)
    similar = rank_by_similarity(intent, eligible, vectors, provider)
    assert all(item.variant_id == cheap.variant_id for item in ranked)
    assert all(item.variant_id == cheap.variant_id for item in similar)
    assert expensive.variant_id not in {item.variant_id for item in ranked}


def test_dimension_mismatch_is_skipped() -> None:
    variant = snapshot(name="Dim", sku="DIM-1")
    intent = CASE1_INTENT
    ranked = rank_eligible(
        intent,
        [variant],
        {variant.variant_id: [0.1, 0.2, 0.3]},
        provider,
    )
    assert ranked == []


def test_same_provider_used_for_query_and_documents() -> None:
    variant = snapshot(
        name="Cabin",
        attributes={"anc": True, "wireless": True, "battery_hours": 70},
    )
    vectors = {variant.variant_id: provider.embed(build_product_document(variant).text)}
    ranked = rank_eligible(CASE1_INTENT, [variant], vectors, provider)
    assert ranked
    assert 0.0 <= ranked[0].semantic_similarity <= 1.0


def test_match_api_exposes_embedding_metadata(client: TestClient) -> None:
    response = client.post(
        "/api/v1/match",
        json={"intent": "wireless headphones under $200", "parser_mode": "rule_based"},
    )
    assert response.status_code == 200
    block = response.json()["semantic_matching"]
    assert block["provider_requested"] == "hashing"
    assert block["provider_used"] == "hashing"
    assert block["fallback_used"] is False
    assert block["dimension"] == 384
    assert block["model"] == "hashing-vectorizer-384"
    assert block["retrieval_version"]
    assert block["rerank_version"]
    for card in block["matches"]:
        assert card["base_price_cents"] < 20000


def test_ready_reports_semantic_retrieval(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    names = {item["name"] for item in response.json()["checks"]}
    assert "semantic_retrieval" in names
    assert "embeddings" in names


def test_unique_variant_ids_do_not_leak() -> None:
    leaked = snapshot(name="Leak", price=10, sku="LEAK")
    leaked.variant_id = uuid4()
    ranked = rank_eligible(CASE1_INTENT, [], {}, provider)
    assert leaked.variant_id not in {item.variant_id for item in ranked}
