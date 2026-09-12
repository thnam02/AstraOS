"""Non-learned ranking baselines for comparison. Not trained models."""

from typing import Any

import numpy as np


class PriceHeuristic:
    name = "price_heuristic.v1"
    algorithm = "PRICE_HEURISTIC"

    def predict_score(self, X: list[dict[str, Any]]) -> np.ndarray:
        prices = np.asarray(
            [float(row.get("total_price_cents") or 0.0) for row in X], dtype=float
        )
        if len(prices) == 0:
            return prices
        span = float(np.max(prices) - np.min(prices)) or 1.0
        return np.asarray(1.0 - (prices - np.min(prices)) / span, dtype=float)

    def predict_proba(self, X: list[dict[str, Any]]) -> np.ndarray:
        return self.predict_score(X)

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "algorithm": self.algorithm,
            "score_label": "Inverse-price heuristic",
        }


class ColdStartUtilityBaseline:
    name = "cold_start_utility.v1"
    algorithm = "COLD_START_UTILITY"

    def __init__(self, scores: np.ndarray) -> None:
        self.scores = scores

    def predict_score(self, X: list[dict[str, Any]]) -> np.ndarray:
        if len(X) != len(self.scores):
            raise ValueError("Utility baseline is bound to a fixed evaluation set.")
        return self.scores

    def predict_proba(self, X: list[dict[str, Any]]) -> np.ndarray:
        return self.predict_score(X)

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "algorithm": self.algorithm,
            "score_label": "Transparent cold-start utility",
        }
