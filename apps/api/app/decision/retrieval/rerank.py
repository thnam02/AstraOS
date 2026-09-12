"""Grounded reranking from merchant facts. Not purchase probability."""

from __future__ import annotations

from app.decision.eligibility.snapshot import VariantSnapshot
from app.decision.intent.models import ShoppingIntent
from app.decision.retrieval.embeddings import cosine_similarity
from app.decision.retrieval.mapping import (
    features_for,
    semantic_needs,
    support_hits,
    weighted_score,
)
from app.decision.retrieval.models import MatchFact, MatchReason, RankedProductMatch

# Interpretable matching weights. Not calibrated probabilities.
_W_SIM = 0.15
_W_PRODUCT = 0.30
_W_CONTEXT = 0.25
_W_PREF = 0.20
_W_COVER = 0.10


def evidence_for(
    snapshot: VariantSnapshot, attribute: str
) -> tuple[str | None, str | None]:
    for row in snapshot.evidence:
        if row.attribute_name == attribute and not row.is_stale:
            return row.id, row.source_name
    return None, None


def rerank_variant(
    *,
    snapshot: VariantSnapshot,
    intent: ShoppingIntent,
    semantic_similarity: float,
) -> RankedProductMatch:
    needs = semantic_needs(intent)
    reasons: list[MatchReason] = []
    matched: list[str] = []
    unsupported: list[str] = [item.label for item in intent.unsupported_semantic_needs]
    product_scores: list[float] = []
    context_scores: list[float] = []
    pref_scores: list[float] = []
    supported_weight = 0.0
    total_weight = 0.0
    evidence_facts: list[MatchFact] = []

    for kind, label, importance in needs:
        total_weight += importance
        if kind == "unsupported":
            unsupported.append(label)
            continue
        hits = support_hits(snapshot, features_for(kind, label))
        score = weighted_score(hits)
        if score is None:
            unsupported.append(label)
            continue
        supported_weight += importance
        matched.append(label)
        facts = []
        for hit in hits:
            ev_id, source = evidence_for(snapshot, hit.attribute)
            fact = MatchFact(
                attribute=hit.attribute,
                value=hit.value,
                display=f"{hit.display}: {hit.value}",
                evidence_id=ev_id,
                source_name=source,
            )
            facts.append(fact)
            evidence_facts.append(fact)
        reasons.append(MatchReason(need=label, kind=kind, facts=facts))
        if kind == "context":
            context_scores.append(score)
        elif kind == "preference":
            pref_scores.append(score)
        else:
            product_scores.append(score)

    product_fit = _mean(product_scores)
    context_fit = _mean(context_scores)
    preference_fit = _mean(pref_scores)
    coverage = (supported_weight / total_weight) if total_weight else 1.0
    similarity = max(0.0, semantic_similarity)
    overall = (
        _W_SIM * similarity
        + _W_PRODUCT * product_fit
        + _W_CONTEXT * context_fit
        + _W_PREF * preference_fit
        + _W_COVER * coverage
    )
    return RankedProductMatch(
        product_id=snapshot.product_id,
        variant_id=snapshot.variant_id,
        sku=snapshot.sku,
        product_name=snapshot.product_name,
        brand=snapshot.brand,
        variant_name=snapshot.variant_name,
        base_price_cents=snapshot.base_price_cents,
        rank=0,
        semantic_similarity=round(similarity, 4),
        product_fit=round(product_fit, 4),
        context_fit=round(context_fit, 4),
        preference_fit=round(preference_fit, 4),
        evidence_coverage=round(coverage, 4),
        overall_semantic_fit=round(overall, 4),
        matched_needs=matched,
        unsupported_needs=sorted(set(unsupported)),
        reasons=reasons,
        evidence=evidence_facts,
    )


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def sort_matches(matches: list[RankedProductMatch]) -> list[RankedProductMatch]:
    ordered = sorted(
        matches,
        key=lambda item: (
            -item.overall_semantic_fit,
            -item.evidence_coverage,
            item.base_price_cents,
            item.sku,
        ),
    )
    ranked: list[RankedProductMatch] = []
    for index, item in enumerate(ordered, start=1):
        ranked.append(item.model_copy(update={"rank": index}))
    return ranked


def similarity_only(
    snapshot: VariantSnapshot,
    intent: ShoppingIntent,
    left: list[float],
    right: list[float],
) -> RankedProductMatch:
    score = max(0.0, cosine_similarity(left, right))
    match = rerank_variant(snapshot=snapshot, intent=intent, semantic_similarity=score)
    return match.model_copy(
        update={
            "overall_semantic_fit": round(score, 4),
            "product_fit": 0.0,
            "context_fit": 0.0,
            "preference_fit": 0.0,
        }
    )
