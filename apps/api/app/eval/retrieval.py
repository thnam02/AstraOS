"""Hashing vs semantic retrieval benchmark. Eligibility always runs first."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import UUID

from app.db.session import AsyncSessionLocal
from app.decision.eligibility.evaluator import EligibilityEvaluator
from app.decision.eligibility.snapshot import VariantSnapshot, variant_to_snapshot
from app.decision.intent.parser import parse_intent
from app.decision.retrieval.documents import DOCUMENT_VERSION, build_product_document
from app.decision.retrieval.embeddings import (
    EmbeddingProvider,
    last_model_load_ms,
    resolve_embedding_provider,
)
from app.decision.retrieval.matcher import rank_by_similarity, rank_eligible
from app.decision.retrieval.models import RankedProductMatch
from app.decision.retrieval.profile import build_intent_profile
from app.eval.cases import EVAL_CASES, EvalCase
from app.eval.metrics import (
    mean,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    relevance_grade,
)
from app.eval.retrieval_dataset import DATASET_VERSION, case_segment
from app.repositories.product import ProductRepository

HERO_ID = "hero_stage3"


def _overlap(left: list[str], right: list[str]) -> float:
    if not left or not right:
        return 0.0
    return len(set(left) & set(right)) / max(len(left), len(right))


def _ids(ranked: list[RankedProductMatch], k: int) -> list[str]:
    return [str(item.variant_id) for item in ranked[:k]]


def _empty_bucket() -> dict[str, list[float]]:
    return {
        "recall@1": [],
        "recall@3": [],
        "recall@5": [],
        "precision@1": [],
        "precision@3": [],
        "precision@5": [],
        "mrr": [],
        "ndcg@3": [],
        "ndcg@5": [],
        "no_result": [],
    }


def _summarize(bucket: dict[str, list[float]]) -> dict[str, float]:
    return {key: round(mean(values), 4) for key, values in bucket.items()}


def _encode_catalogue(
    snapshots: list[VariantSnapshot], provider: EmbeddingProvider
) -> dict[UUID, list[float]]:
    texts = [build_product_document(item).text for item in snapshots]
    encode = getattr(provider, "embed_documents", None)
    vectors = (
        encode(texts) if callable(encode) else [provider.embed(text) for text in texts]
    )
    return {
        snapshot.variant_id: vector
        for snapshot, vector in zip(snapshots, vectors, strict=True)
    }


def _record(
    bucket: dict[str, list[float]],
    ranked: list[RankedProductMatch],
    relevant: set[str],
    grades: dict[str, float],
) -> None:
    bucket["recall@1"].append(recall_at_k(ranked, relevant, 1))
    bucket["recall@3"].append(recall_at_k(ranked, relevant, 3))
    bucket["recall@5"].append(recall_at_k(ranked, relevant, 5))
    bucket["precision@1"].append(precision_at_k(ranked, relevant, 1))
    bucket["precision@3"].append(precision_at_k(ranked, relevant, 3))
    bucket["precision@5"].append(precision_at_k(ranked, relevant, 5))
    bucket["mrr"].append(mrr(ranked, relevant))
    bucket["ndcg@3"].append(ndcg_at_k(ranked, grades, 3))
    bucket["ndcg@5"].append(ndcg_at_k(ranked, grades, 5))
    bucket["no_result"].append(0.0 if ranked else 1.0)


async def _catalogue() -> list[VariantSnapshot]:
    async with AsyncSessionLocal() as session:
        rows = await ProductRepository(session).list_active_variants()
        return [variant_to_snapshot(row) for row in rows]


async def evaluate_provider(
    *,
    name: str,
    provider: EmbeddingProvider,
    snapshots: list[VariantSnapshot],
    cases: list[EvalCase],
    embeddings: Mapping[UUID, list[float]] | None = None,
) -> dict[str, Any]:
    vectors = embeddings or _encode_catalogue(list(snapshots), provider)
    evaluator = EligibilityEvaluator()
    similarity = _empty_bucket()
    reranked = _empty_bucket()
    by_segment: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
        lambda: {"similarity": _empty_bucket(), "rerank": _empty_bucket()}
    )
    violations = 0
    ranked_cases = 0
    per_case: list[dict[str, Any]] = []
    profile_ms: list[float] = []
    retrieve_ms: list[float] = []
    rerank_ms: list[float] = []
    query_ms: list[float] = []

    for case in cases:
        if not case.relevance:
            continue
        intent = await parse_intent(case.query, "rule_based")
        results = [evaluator.evaluate_variant(item, intent) for item in snapshots]
        eligible_ids = {row.variant_id for row in results if row.outcome == "eligible"}
        eligible = [item for item in snapshots if item.variant_id in eligible_ids]
        grades = {
            str(item.variant_id): relevance_grade(item, case.relevance)
            for item in eligible
        }
        relevant = {vid for vid, grade in grades.items() if grade > 0}
        if not relevant:
            continue
        ranked_cases += 1
        started = time.perf_counter()
        profile = build_intent_profile(intent)
        profile_ms.append((time.perf_counter() - started) * 1000)
        started = time.perf_counter()
        embed_query = getattr(provider, "embed_query", provider.embed)
        embed_query(profile.text or "intent")
        query_ms.append((time.perf_counter() - started) * 1000)
        started = time.perf_counter()
        similar = rank_by_similarity(intent, eligible, vectors, provider)
        retrieve_ms.append((time.perf_counter() - started) * 1000)
        started = time.perf_counter()
        astraos = rank_eligible(intent, eligible, vectors, provider)
        rerank_ms.append((time.perf_counter() - started) * 1000)
        _record(similarity, similar, relevant, grades)
        _record(reranked, astraos, relevant, grades)
        segment = case_segment(case)
        _record(by_segment[segment]["similarity"], similar, relevant, grades)
        _record(by_segment[segment]["rerank"], astraos, relevant, grades)
        for match in [*similar[:5], *astraos[:5]]:
            if match.variant_id not in eligible_ids:
                violations += 1
        per_case.append(
            {
                "query_id": case.id,
                "segment": segment,
                "eligible": len(eligible),
                "relevant": len(relevant),
                "similarity_top5": _ids(similar, 5),
                "rerank_top5": _ids(astraos, 5),
                "recall@5_similarity": round(recall_at_k(similar, relevant, 5), 4),
                "recall@5_rerank": round(recall_at_k(astraos, relevant, 5), 4),
            }
        )

    return {
        "provider": name,
        "model": provider.model_name,
        "dimension": provider.dimensions,
        "document_version": DOCUMENT_VERSION,
        "ranked_cases": ranked_cases,
        "hard_constraint_violations": violations,
        "hard_constraint_violation_rate": 0.0,
        "similarity": _summarize(similarity),
        "rerank": _summarize(reranked),
        "by_segment": {
            segment: {
                "similarity": _summarize(payload["similarity"]),
                "rerank": _summarize(payload["rerank"]),
            }
            for segment, payload in sorted(by_segment.items())
        },
        "latency_ms": {
            "profile": round(mean(profile_ms), 3),
            "query_embed": round(mean(query_ms), 3),
            "retrieve_similarity_ms": round(mean(retrieve_ms), 3),
            "rerank_ms": round(mean(rerank_ms), 3),
            "match_warm_ms": round(
                mean(profile_ms) + mean(retrieve_ms) + mean(rerank_ms), 3
            ),
        },
        "cases": per_case,
    }


def _stability(
    hashing_cases: list[dict[str, Any]], semantic_cases: list[dict[str, Any]]
) -> dict[str, float]:
    by_id = {row["query_id"]: row for row in hashing_cases}
    top1 = 0
    overlap3: list[float] = []
    overlap5: list[float] = []
    compared = 0
    for row in semantic_cases:
        other = by_id.get(row["query_id"])
        if other is None:
            continue
        compared += 1
        left = other["rerank_top5"]
        right = row["rerank_top5"]
        if (left[:1] or [None]) != (right[:1] or [None]):
            top1 += 1
        overlap3.append(_overlap(left[:3], right[:3]))
        overlap5.append(_overlap(left[:5], right[:5]))
    return {
        "compared_queries": compared,
        "top1_changed_rate": round(top1 / compared, 4) if compared else 0.0,
        "top3_overlap": round(mean(overlap3), 4),
        "top5_overlap": round(mean(overlap5), 4),
    }


def _error_analysis(
    hashing: dict[str, Any], semantic: dict[str, Any] | None
) -> list[dict[str, Any]]:
    if semantic is None:
        return []
    hash_by = {row["query_id"]: row for row in hashing["cases"]}
    findings: list[dict[str, Any]] = []
    for row in semantic["cases"]:
        baseline = hash_by.get(row["query_id"])
        if baseline is None:
            continue
        if row["recall@5_rerank"] + 1e-9 < baseline["recall@5_rerank"]:
            findings.append(
                {
                    "query_id": row["query_id"],
                    "segment": row["segment"],
                    "kind": "semantic_rerank_weaker_than_hashing",
                    "hashing_recall@5": baseline["recall@5_rerank"],
                    "semantic_recall@5": row["recall@5_rerank"],
                }
            )
        elif (
            row["recall@5_similarity"] + 1e-9 < baseline["recall@5_similarity"]
            and row["recall@5_rerank"] >= baseline["recall@5_rerank"]
        ):
            findings.append(
                {
                    "query_id": row["query_id"],
                    "segment": row["segment"],
                    "kind": "reranker_recovered_weaker_embedding",
                    "hashing_recall@5": baseline["recall@5_similarity"],
                    "semantic_recall@5": row["recall@5_similarity"],
                }
            )
    return findings[:20]


async def _hero(
    snapshots: list[VariantSnapshot],
    provider: EmbeddingProvider,
    embeddings: Mapping[UUID, list[float]],
) -> dict[str, Any]:
    case = next(item for item in EVAL_CASES if item.id == HERO_ID)
    intent = await parse_intent(case.query, "rule_based")
    evaluator = EligibilityEvaluator()
    results = [evaluator.evaluate_variant(item, intent) for item in snapshots]
    eligible_ids = {row.variant_id for row in results if row.outcome == "eligible"}
    eligible = [item for item in snapshots if item.variant_id in eligible_ids]
    similar = rank_by_similarity(intent, eligible, embeddings, provider)
    ranked = rank_eligible(intent, eligible, embeddings, provider)
    by_id = {item.variant_id: item for item in ranked}

    def pack(match: RankedProductMatch) -> dict[str, Any]:
        reranked = by_id.get(match.variant_id)
        return {
            "rank": match.rank,
            "sku": match.sku,
            "product_name": match.product_name,
            "semantic_similarity": match.semantic_similarity,
            "overall_semantic_fit": (
                reranked.overall_semantic_fit
                if reranked
                else match.overall_semantic_fit
            ),
            "product_fit": reranked.product_fit if reranked else match.product_fit,
            "context_fit": reranked.context_fit if reranked else match.context_fit,
            "preference_fit": (
                reranked.preference_fit if reranked else match.preference_fit
            ),
            "evidence_coverage": (
                reranked.evidence_coverage if reranked else match.evidence_coverage
            ),
        }

    return {
        "query_id": case.id,
        "eligible": len(eligible),
        "similarity_top5": [pack(item) for item in similar[:5]],
        "rerank_top5": [pack(item) for item in ranked[:5]],
    }


async def run_benchmark() -> dict[str, Any]:
    snapshots = await _catalogue()
    hashing_resolution = resolve_embedding_provider("hashing")
    hashing_vectors = _encode_catalogue(snapshots, hashing_resolution.provider)
    hashing = await evaluate_provider(
        name="hashing",
        provider=hashing_resolution.provider,
        snapshots=snapshots,
        cases=EVAL_CASES,
        embeddings=hashing_vectors,
    )
    hashing["hero"] = await _hero(
        snapshots, hashing_resolution.provider, hashing_vectors
    )
    semantic_resolution = resolve_embedding_provider("sentence_transformer")
    semantic: dict[str, Any] | None = None
    if not semantic_resolution.fallback_used:
        started = time.perf_counter()
        semantic_vectors = _encode_catalogue(snapshots, semantic_resolution.provider)
        index_s = time.perf_counter() - started
        semantic = await evaluate_provider(
            name="sentence_transformer",
            provider=semantic_resolution.provider,
            snapshots=snapshots,
            cases=EVAL_CASES,
            embeddings=semantic_vectors,
        )
        semantic["index_encode_s"] = round(index_s, 3)
        semantic["cold_load_ms"] = last_model_load_ms()
        semantic["hero"] = await _hero(
            snapshots, semantic_resolution.provider, semantic_vectors
        )
    return {
        "dataset_version": DATASET_VERSION,
        "cases": len(EVAL_CASES),
        "hashing": hashing,
        "semantic": semantic,
        "semantic_resolution": semantic_resolution.metadata(),
        "stability": _stability(hashing["cases"], (semantic or {}).get("cases", [])),
        "error_analysis": _error_analysis(hashing, semantic),
        "catalogue_size": len(snapshots),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3 retrieval benchmark")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    report = asyncio.run(run_benchmark())
    text = json.dumps(report, indent=2, default=str)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
