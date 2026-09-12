"""Held-out metrics. Scores are synthetic, not conversion probabilities."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)


def classification_metrics(
    y_true: np.ndarray,
    proba: np.ndarray,
    *,
    threshold: float = 0.5,
) -> dict[str, float]:
    y_hat = (proba >= threshold).astype(int)
    metrics: dict[str, float] = {
        "log_loss": float(log_loss(y_true, np.clip(proba, 1e-6, 1 - 1e-6))),
        "brier": float(brier_score_loss(y_true, proba)),
        "accuracy": float(accuracy_score(y_true, y_hat)),
        "precision": float(precision_score(y_true, y_hat, zero_division=0)),
        "recall": float(recall_score(y_true, y_hat, zero_division=0)),
        "f1": float(f1_score(y_true, y_hat, zero_division=0)),
        "positive_rate": float(np.mean(y_true)),
        "n": float(len(y_true)),
        "threshold": threshold,
    }
    if len(np.unique(y_true)) > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_true, proba))
        metrics["pr_auc"] = float(average_precision_score(y_true, proba))
    else:
        metrics["roc_auc"] = float("nan")
        metrics["pr_auc"] = float("nan")
    return metrics


def calibration_bins(
    y_true: np.ndarray,
    proba: np.ndarray,
    *,
    bins: int = 10,
) -> list[dict[str, float]]:
    edges = np.linspace(0.0, 1.0, bins + 1)
    rows: list[dict[str, float]] = []
    for index in range(bins):
        low, high = edges[index], edges[index + 1]
        if index == bins - 1:
            mask = (proba >= low) & (proba <= high)
        else:
            mask = (proba >= low) & (proba < high)
        if not np.any(mask):
            continue
        rows.append(
            {
                "low": float(low),
                "high": float(high),
                "predicted": float(np.mean(proba[mask])),
                "observed": float(np.mean(y_true[mask])),
                "count": float(np.sum(mask)),
            }
        )
    return rows


def ranking_metrics(
    y_true: np.ndarray,
    scores: np.ndarray,
    groups: list[str],
) -> dict[str, float]:
    by_group: dict[str, list[tuple[float, int]]] = defaultdict(list)
    for label, score, group in zip(y_true, scores, groups, strict=True):
        by_group[group].append((float(score), int(label)))
    top1 = 0
    mrr = 0.0
    ndcg = 0.0
    counted = 0
    for pairs in by_group.values():
        if not any(label == 1 for _score, label in pairs):
            continue
        ranked = sorted(pairs, key=lambda item: item[0], reverse=True)
        labels = [label for _score, label in ranked]
        counted += 1
        if labels[0] == 1:
            top1 += 1
        rank = labels.index(1) + 1
        mrr += 1.0 / rank
        dcg = sum(label / np.log2(idx + 2) for idx, label in enumerate(labels))
        ideal = sorted(labels, reverse=True)
        idcg = sum(label / np.log2(idx + 2) for idx, label in enumerate(ideal))
        ndcg += dcg / idcg if idcg else 0.0
    if counted == 0:
        return {"top1": 0.0, "mrr": 0.0, "ndcg": 0.0, "groups_with_positive": 0.0}
    return {
        "top1": top1 / counted,
        "mrr": mrr / counted,
        "ndcg": ndcg / counted,
        "groups_with_positive": float(counted),
    }
