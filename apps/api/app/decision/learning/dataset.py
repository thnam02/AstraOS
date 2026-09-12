"""Build ML matrices from CommerceInteraction rows. Split by mission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

from app.decision.learning import FEATURE_SCHEMA_VERSION, TARGET_NAME
from app.decision.learning.features import (
    CATEGORICAL_FEATURES,
    FEATURE_NAMES,
    NUMERIC_FEATURES,
)
from app.decision.learning.leakage import assert_no_leakage


@dataclass
class LearningDataset:
    X: list[dict[str, Any]]
    y: np.ndarray
    groups: list[str]
    utility_scores: np.ndarray
    prices: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)
    feature_schema_version: str = FEATURE_SCHEMA_VERSION
    numeric_features: tuple[str, ...] = NUMERIC_FEATURES
    categorical_features: tuple[str, ...] = CATEGORICAL_FEATURES

    @property
    def size(self) -> int:
        return len(self.y)


@dataclass
class DatasetSplit:
    train: LearningDataset
    validation: LearningDataset
    test: LearningDataset


def _row_features(payload: dict[str, Any]) -> dict[str, Any]:
    return {name: payload.get(name) for name in FEATURE_NAMES}


def build_dataset(
    interactions: list[dict[str, Any]],
    *,
    seed: int = 2026,
) -> LearningDataset:
    """Keep only valid synthetic rows. Never include FUTURE_REAL_COMMERCE."""
    features: list[dict[str, Any]] = []
    labels: list[int] = []
    groups: list[str] = []
    utilities: list[float] = []
    prices: list[float] = []
    for item in interactions:
        source = item.get("outcome_source")
        if source == "FUTURE_REAL_COMMERCE":
            continue
        if not item.get("policy_safe") or not item.get("hard_constraints_satisfied"):
            continue
        if item.get("features") is None:
            continue
        feat = _row_features(item["features"])
        features.append(feat)
        labels.append(1 if item.get("selected") else 0)
        groups.append(str(item.get("group_id") or item.get("mission_id") or item["id"]))
        utilities.append(float(item.get("buyer_utility") or 0.0))
        prices.append(float(item.get("total_price_cents") or 0.0))
    assert_no_leakage(features)
    return LearningDataset(
        X=features,
        y=np.asarray(labels, dtype=int),
        groups=groups,
        utility_scores=np.asarray(utilities, dtype=float),
        prices=np.asarray(prices, dtype=float),
        metadata={
            "target": TARGET_NAME,
            "seed": seed,
            "positive_rate": float(np.mean(labels)) if labels else 0.0,
            "size": len(labels),
        },
    )


def _subset(dataset: LearningDataset, index: np.ndarray) -> LearningDataset:
    chosen = [dataset.X[int(i)] for i in index]
    return LearningDataset(
        X=chosen,
        y=dataset.y[index],
        groups=[dataset.groups[int(i)] for i in index],
        utility_scores=dataset.utility_scores[index],
        prices=dataset.prices[index],
        metadata={**dataset.metadata, "size": len(index)},
    )


def _indices_for_groups(groups: list[str], chosen: set[str]) -> np.ndarray:
    return np.asarray(
        [index for index, group in enumerate(groups) if group in chosen],
        dtype=int,
    )


def grouped_split(
    dataset: LearningDataset,
    *,
    seed: int = 2026,
    train_size: float = 0.70,
    validation_size: float = 0.15,
) -> DatasetSplit:
    """No offer from the same mission appears in more than one split."""
    unique = list(dict.fromkeys(dataset.groups))
    rng = np.random.RandomState(seed)
    rng.shuffle(unique)
    n_groups = len(unique)
    if n_groups < 3:
        raise ValueError("Need at least three missions for a grouped split.")
    if n_groups >= 10:
        groups = np.asarray(dataset.groups)
        splitter = GroupShuffleSplit(
            n_splits=1, train_size=train_size, random_state=seed
        )
        train_idx, rest_idx = next(splitter.split(dataset.X, dataset.y, groups))
        rest = _subset(dataset, rest_idx)
        rest_groups = list(dict.fromkeys(rest.groups))
        if len(rest_groups) < 2:
            n_train = max(1, n_groups - 2)
            train_g = set(unique[:n_train])
            val_g = {unique[n_train]}
            test_g = {unique[n_train + 1]}
            train_idx = _indices_for_groups(dataset.groups, train_g)
            val_idx = _indices_for_groups(dataset.groups, val_g)
            test_idx = _indices_for_groups(dataset.groups, test_g)
        else:
            val_frac = validation_size / max(1.0 - train_size, 1e-9)
            rest_split = GroupShuffleSplit(
                n_splits=1, train_size=val_frac, random_state=seed + 1
            )
            val_rel, test_rel = next(
                rest_split.split(rest.X, rest.y, np.asarray(rest.groups))
            )
            val_idx = rest_idx[val_rel]
            test_idx = rest_idx[test_rel]
    else:
        n_train = max(1, int(round(n_groups * train_size)))
        n_val = max(1, int(round(n_groups * validation_size)))
        if n_train + n_val >= n_groups:
            n_train = n_groups - 2
            n_val = 1
        train_g = set(unique[:n_train])
        val_g = set(unique[n_train : n_train + n_val])
        test_g = set(unique[n_train + n_val :])
        train_idx = _indices_for_groups(dataset.groups, train_g)
        val_idx = _indices_for_groups(dataset.groups, val_g)
        test_idx = _indices_for_groups(dataset.groups, test_g)
    split = DatasetSplit(
        train=_subset(dataset, train_idx),
        validation=_subset(dataset, val_idx),
        test=_subset(dataset, test_idx),
    )
    train_g = set(split.train.groups)
    val_g = set(split.validation.groups)
    test_g = set(split.test.groups)
    if train_g & val_g or train_g & test_g or val_g & test_g:
        raise RuntimeError("Mission leakage across dataset splits.")
    return split
