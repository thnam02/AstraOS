"""Classification and ranking metric sanity."""

import numpy as np

from app.decision.learning.evaluation import (
    calibration_bins,
    classification_metrics,
    ranking_metrics,
)


def test_perfect_ranking() -> None:
    y = np.asarray([0, 1, 0, 1])
    scores = np.asarray([0.1, 0.9, 0.2, 0.8])
    groups = ["a", "a", "b", "b"]
    rank = ranking_metrics(y, scores, groups)
    assert rank["top1"] == 1.0
    assert rank["mrr"] == 1.0


def test_classification_and_calibration() -> None:
    y = np.asarray([0, 0, 1, 1])
    proba = np.asarray([0.1, 0.2, 0.8, 0.9])
    metrics = classification_metrics(y, proba)
    assert metrics["roc_auc"] == 1.0
    assert metrics["brier"] < 0.05
    bins = calibration_bins(y, proba, bins=4)
    assert bins
