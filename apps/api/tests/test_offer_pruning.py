"""Deterministic candidate-space pruning."""

from app.decision.offers.constructor import prune_limits
from app.decision.offers.models import ConstructionLimits


def test_pruning_is_recorded() -> None:
    limits = ConstructionLimits(max_products=8, max_total_candidates=20)
    dim_counts = [(5, 3, 3, 4, 2)] * 8
    pruned, reason, estimated = prune_limits(
        product_count=8, dim_counts=dim_counts, limits=limits
    )
    assert reason is not None
    assert estimated <= pruned.max_total_candidates
    assert pruned.max_products < 8 or pruned.max_price_options < 5


def test_no_pruning_when_under_cap() -> None:
    limits = ConstructionLimits(max_products=2, max_total_candidates=5000)
    dim_counts = [(5, 3, 2, 3, 2), (5, 2, 2, 2, 1)]
    pruned, reason, estimated = prune_limits(
        product_count=2, dim_counts=dim_counts, limits=limits
    )
    assert reason is None
    assert estimated > 0
    assert pruned.max_products == 2
