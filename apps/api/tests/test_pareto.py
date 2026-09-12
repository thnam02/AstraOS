"""Pareto dominance and frontier correctness."""

from uuid import uuid4

import numpy as np

from app.decision.pareto.dominance import dominates, pareto_mask
from app.decision.pareto.frontier import build_frontier


def test_simple_dominance() -> None:
    assert dominates((0.80, 100), (0.72, 90), maximize=(True, True))
    assert not dominates((0.80, 100), (0.90, 82), maximize=(True, True))
    assert not dominates((0.90, 82), (0.80, 100), maximize=(True, True))


def test_identical_offers_neither_dominates() -> None:
    assert not dominates((0.5, 10), (0.5, 10), maximize=(True, True))


def test_epsilon_near_identical() -> None:
    near = dominates(
        (0.80, 100),
        (0.80 + 1e-12, 100),
        maximize=(True, True),
        epsilon=1e-9,
    )
    assert not near
    assert dominates((0.81, 100), (0.80, 100), maximize=(True, True), epsilon=1e-9)


def test_frontier_mask() -> None:
    values = np.array(
        [
            [0.80, 100],
            [0.72, 90],
            [0.90, 82],
            [0.80, 100],
        ],
        dtype=np.float64,
    )
    mask = pareto_mask(values, maximize=(True, True))
    assert mask[0]
    assert not mask[1]
    assert mask[2]
    assert mask[3]


def test_build_frontier_ids() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    result = build_frontier([a, b, c], [0.80, 0.72, 0.90], [10000, 9000, 8200])
    assert a in result.efficient_offer_ids
    assert c in result.efficient_offer_ids
    assert b in result.dominated_offer_ids
    assert result.dominated_by[str(b)] in {a, c}


def test_three_objectives_supported() -> None:
    values = np.array([[1.0, 10, -5], [0.9, 9, -4], [0.8, 12, -8]], dtype=np.float64)
    mask = pareto_mask(values, maximize=(True, True, False))
    assert mask[0]
    assert mask[2]
