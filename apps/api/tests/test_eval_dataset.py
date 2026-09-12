"""Frozen evaluation set and metric helpers."""

from uuid import uuid4

from app.decision.retrieval.models import RankedProductMatch
from app.eval.cases import EVAL_CASES
from app.eval.metrics import ndcg_at_k, recall_at_k, set_f1


def test_dataset_has_at_least_fifty_cases() -> None:
    assert len(EVAL_CASES) >= 50
    ids = [case.id for case in EVAL_CASES]
    assert len(ids) == len(set(ids))


def test_dataset_covers_key_families() -> None:
    blob = " ".join(case.query.lower() for case in EVAL_CASES)
    for token in (
        "flight",
        "commuting",
        "gaming",
        "studio",
        "gym",
        "comfort",
        "reliability",
        "battery",
        "luxurious",
    ):
        assert token in blob


def test_recall_and_ndcg_helpers() -> None:
    winner = uuid4()
    loser = uuid4()
    matches = [
        RankedProductMatch(
            product_id=uuid4(),
            variant_id=winner,
            sku="A",
            product_name="A",
            brand="A",
            base_price_cents=10000,
            rank=1,
            semantic_similarity=0.9,
            product_fit=0.9,
            context_fit=0.9,
            preference_fit=0.9,
            evidence_coverage=1.0,
            overall_semantic_fit=0.9,
            matched_needs=[],
            unsupported_needs=[],
            reasons=[],
            evidence=[],
        ),
        RankedProductMatch(
            product_id=uuid4(),
            variant_id=loser,
            sku="B",
            product_name="B",
            brand="B",
            base_price_cents=20000,
            rank=2,
            semantic_similarity=0.1,
            product_fit=0.1,
            context_fit=0.1,
            preference_fit=0.1,
            evidence_coverage=0.1,
            overall_semantic_fit=0.1,
            matched_needs=[],
            unsupported_needs=[],
            reasons=[],
            evidence=[],
        ),
    ]
    assert recall_at_k(matches, {str(winner)}, 1) == 1.0
    assert ndcg_at_k(matches, {str(winner): 1.0, str(loser): 0.2}, 2) > 0.5


def test_set_f1_empty_gold() -> None:
    assert set_f1(set(), set())["f1"] == 1.0
    assert set_f1({"anc"}, set())["f1"] == 0.0
