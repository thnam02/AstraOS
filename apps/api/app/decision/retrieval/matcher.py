"""Rank only Stage 2-eligible variants. Semantic score never overrides eligibility."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from app.decision.eligibility.snapshot import VariantSnapshot
from app.decision.intent.models import ShoppingIntent
from app.decision.retrieval.embeddings import (
    EmbeddingProvider,
    cosine_similarity,
)
from app.decision.retrieval.models import RankedProductMatch
from app.decision.retrieval.profile import build_intent_profile
from app.decision.proof.enrich import enrich_match
from app.decision.retrieval.rerank import rerank_variant, sort_matches


def rank_eligible(
    intent: ShoppingIntent,
    snapshots: list[VariantSnapshot],
    embeddings: Mapping[UUID, list[float]],
    provider: EmbeddingProvider,
) -> list[RankedProductMatch]:
    """Grounded semantic rank of already-eligible variants."""
    profile = build_intent_profile(intent)
    embed_query = getattr(provider, "embed_query", provider.embed)
    intent_vector = embed_query(profile.text or "intent")
    matches: list[RankedProductMatch] = []
    for snapshot in snapshots:
        vector = embeddings.get(snapshot.variant_id)
        if vector is None:
            continue
        if len(vector) != len(intent_vector):
            continue
        similarity = cosine_similarity(intent_vector, vector)
        matches.append(
            enrich_match(
                snapshot,
                rerank_variant(
                    snapshot=snapshot,
                    intent=intent,
                    semantic_similarity=similarity,
                ),
            )
        )
    return sort_matches(matches)


def rank_by_price(snapshots: list[VariantSnapshot]) -> list[RankedProductMatch]:
    """Baseline A: eligibility already applied, then cheapest first."""
    ordered = sorted(snapshots, key=lambda item: (item.base_price_cents, item.sku))
    matches: list[RankedProductMatch] = []
    for index, snapshot in enumerate(ordered, start=1):
        score = max(0.0, 1.0 - (index - 1) / max(len(ordered), 1))
        matches.append(
            RankedProductMatch(
                product_id=snapshot.product_id,
                variant_id=snapshot.variant_id,
                sku=snapshot.sku,
                product_name=snapshot.product_name,
                brand=snapshot.brand,
                variant_name=snapshot.variant_name,
                base_price_cents=snapshot.base_price_cents,
                rank=index,
                semantic_similarity=0.0,
                product_fit=0.0,
                context_fit=0.0,
                preference_fit=0.0,
                evidence_coverage=0.0,
                overall_semantic_fit=round(score, 4),
                matched_needs=[],
                unsupported_needs=[],
                reasons=[],
                evidence=[],
            )
        )
    return matches


def rank_by_similarity(
    intent: ShoppingIntent,
    snapshots: list[VariantSnapshot],
    embeddings: Mapping[UUID, list[float]],
    provider: EmbeddingProvider,
) -> list[RankedProductMatch]:
    """Baseline B: eligibility + raw embedding similarity only."""
    profile = build_intent_profile(intent)
    embed_query = getattr(provider, "embed_query", provider.embed)
    intent_vector = embed_query(profile.text or "intent")
    matches: list[RankedProductMatch] = []
    for snapshot in snapshots:
        vector = embeddings.get(snapshot.variant_id)
        if vector is None:
            continue
        if len(vector) != len(intent_vector):
            continue
        similarity = max(0.0, cosine_similarity(intent_vector, vector))
        matches.append(
            RankedProductMatch(
                product_id=snapshot.product_id,
                variant_id=snapshot.variant_id,
                sku=snapshot.sku,
                product_name=snapshot.product_name,
                brand=snapshot.brand,
                variant_name=snapshot.variant_name,
                base_price_cents=snapshot.base_price_cents,
                rank=0,
                semantic_similarity=round(similarity, 4),
                product_fit=0.0,
                context_fit=0.0,
                preference_fit=0.0,
                evidence_coverage=0.0,
                overall_semantic_fit=round(similarity, 4),
                matched_needs=[],
                unsupported_needs=[],
                reasons=[],
                evidence=[],
            )
        )
    return sort_matches(matches)
