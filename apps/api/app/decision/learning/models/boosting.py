"""Histogram gradient boosting. Synthetic selection model only."""

from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import Pipeline

from app.decision.learning.models.preprocess import feature_preprocessor


class BoostingResponseModel:
    name = "hist_gbdt.v1"
    algorithm = "GRADIENT_BOOSTING"

    def __init__(
        self,
        *,
        max_depth: int = 3,
        learning_rate: float = 0.08,
        max_iter: int = 120,
        random_state: int = 2026,
    ) -> None:
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.max_iter = max_iter
        self.random_state = random_state
        self.pipeline: Pipeline | None = None

    def fit(self, X: list[dict[str, Any]], y: np.ndarray) -> None:
        self.pipeline = Pipeline(
            [
                ("prep", feature_preprocessor(scale=False)),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        max_depth=self.max_depth,
                        learning_rate=self.learning_rate,
                        max_iter=self.max_iter,
                        random_state=self.random_state,
                    ),
                ),
            ]
        )
        self.pipeline.fit(X, y)

    def predict_proba(self, X: list[dict[str, Any]]) -> np.ndarray:
        if self.pipeline is None:
            raise RuntimeError("Model is not fitted.")
        return np.asarray(self.pipeline.predict_proba(X)[:, 1], dtype=float)

    def predict_score(self, X: list[dict[str, Any]]) -> np.ndarray:
        return self.predict_proba(X)

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "algorithm": self.algorithm,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "max_iter": self.max_iter,
            "random_state": self.random_state,
            "score_label": "Synthetic Response Score",
        }

    def feature_associations(self) -> list[dict[str, float | str]]:
        """Permutation-free proxy: use absolute logistic-style names if present."""
        return []
