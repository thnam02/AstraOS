"""Regularised logistic regression. Synthetic selection model only."""

from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.decision.learning.evaluation import classification_metrics
from app.decision.learning.models.preprocess import (
    feature_preprocessor,
    transformed_feature_names,
)

C_GRID = (0.01, 0.1, 1.0, 10.0)


class LogisticResponseModel:
    name = "logistic.v1"
    algorithm = "LOGISTIC_REGRESSION"

    def __init__(self, *, C: float = 1.0, random_state: int = 2026) -> None:
        self.C = C
        self.random_state = random_state
        self.pipeline: Pipeline | None = None

    def fit(self, X: list[dict[str, Any]], y: np.ndarray) -> None:
        self.pipeline = Pipeline(
            [
                ("prep", feature_preprocessor(scale=True)),
                (
                    "model",
                    LogisticRegression(
                        C=self.C,
                        max_iter=400,
                        class_weight="balanced",
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
            "C": self.C,
            "random_state": self.random_state,
            "score_label": "Synthetic Response Score",
        }

    def coefficient_associations(self) -> list[dict[str, float | str]]:
        if self.pipeline is None:
            return []
        prep = self.pipeline.named_steps["prep"]
        model = self.pipeline.named_steps["model"]
        names = transformed_feature_names(prep.named_steps["columns"])
        coefs = model.coef_[0]
        rows: list[dict[str, float | str]] = [
            {"feature": name, "coefficient": float(value)}
            for name, value in zip(names, coefs, strict=True)
        ]

        def _magnitude(item: dict[str, float | str]) -> float:
            value = item["coefficient"]
            return abs(value) if isinstance(value, int | float) else 0.0

        rows.sort(key=_magnitude, reverse=True)
        return rows[:20]


def select_logistic_c(
    train_X: list[dict[str, Any]],
    train_y: np.ndarray,
    val_X: list[dict[str, Any]],
    val_y: np.ndarray,
    *,
    random_state: int = 2026,
) -> tuple[LogisticResponseModel, float]:
    best: LogisticResponseModel | None = None
    best_loss = float("inf")
    best_c = 1.0
    for candidate in C_GRID:
        model = LogisticResponseModel(C=candidate, random_state=random_state)
        model.fit(train_X, train_y)
        proba = model.predict_proba(val_X)
        loss = classification_metrics(val_y, proba)["log_loss"]
        if loss < best_loss:
            best = model
            best_loss = loss
            best_c = candidate
    assert best is not None
    return best, best_c
