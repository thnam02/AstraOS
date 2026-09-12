"""Run the frozen Stage 3 evaluation suite."""

from __future__ import annotations

import argparse
import asyncio
import json

from app.db.session import AsyncSessionLocal
from app.decision.eligibility.evaluator import EligibilityEvaluator
from app.decision.eligibility.snapshot import VariantSnapshot, variant_to_snapshot
from app.decision.intent.parser import parse_intent
from app.decision.retrieval.documents import DOCUMENT_VERSION, build_product_document
from app.decision.retrieval.embeddings import default_embedding_provider
from app.decision.retrieval.matcher import (
    rank_by_price,
    rank_by_similarity,
    rank_eligible,
)
from app.eval.cases import EVAL_CASES
from app.eval.metrics import (
    mean,
    ndcg_at_k,
    recall_at_k,
    relevance_grade,
    score_extraction,
)
from app.repositories.product import ProductRepository


async def _catalogue() -> list[VariantSnapshot]:
    async with AsyncSessionLocal() as session:
        rows = await ProductRepository(session).list_active_variants()
        return [variant_to_snapshot(row) for row in rows]


async def run_eval(k: int = 10) -> dict[str, object]:
    snapshots = await _catalogue()
    provider = default_embedding_provider()
    embeddings = {
        item.variant_id: provider.embed(build_product_document(item).text)
        for item in snapshots
    }
    evaluator = EligibilityEvaluator()
    extract_scores: dict[str, list[float]] = {
        "constraints": [],
        "contexts": [],
        "outcomes": [],
        "preferences": [],
    }
    recalls: dict[str, list[float]] = {
        "astraos": [],
        "price": [],
        "similarity": [],
    }
    ndcgs: dict[str, list[float]] = {
        "astraos": [],
        "price": [],
        "similarity": [],
    }
    violations = 0
    ranked_cases = 0

    for case in EVAL_CASES:
        intent = await parse_intent(case.query, "rule_based")
        extracted = score_extraction(intent, case)
        for key in extract_scores:
            extract_scores[key].append(extracted[key]["f1"])
        results = [evaluator.evaluate_variant(item, intent) for item in snapshots]
        eligible_ids = {row.variant_id for row in results if row.outcome == "eligible"}
        eligible = [item for item in snapshots if item.variant_id in eligible_ids]
        grades = {
            str(item.variant_id): relevance_grade(item, case.relevance)
            for item in eligible
        }
        relevant = {vid for vid, grade in grades.items() if grade > 0}
        if not relevant or not case.relevance:
            continue
        ranked_cases += 1
        astraos = rank_eligible(intent, eligible, embeddings, provider)
        price = rank_by_price(eligible)
        similar = rank_by_similarity(intent, eligible, embeddings, provider)
        for name, ranked in (
            ("astraos", astraos),
            ("price", price),
            ("similarity", similar),
        ):
            recalls[name].append(recall_at_k(ranked, relevant, k))
            ndcgs[name].append(ndcg_at_k(ranked, grades, k))
        for match in astraos[:k]:
            if match.variant_id not in eligible_ids:
                violations += 1

    report = {
        "cases": len(EVAL_CASES),
        "ranked_cases": ranked_cases,
        "document_version": DOCUMENT_VERSION,
        "embedding_model": provider.model_name,
        "extraction_f1": {
            key: round(mean(vals), 4) for key, vals in extract_scores.items()
        },
        "recall_at_k": {key: round(mean(vals), 4) for key, vals in recalls.items()},
        "ndcg_at_k": {key: round(mean(vals), 4) for key, vals in ndcgs.items()},
        "k": k,
        "hard_constraint_violations_in_matches": violations,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="AstraOS Stage 3 evaluation")
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()
    report = asyncio.run(run_eval(args.k))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
