"""Common response-model contract. Outputs are synthetic scores."""

from typing import Any, Protocol

import numpy as np


class ResponseModel(Protocol):
    name: str
    algorithm: str

    def fit(self, X: list[dict[str, Any]], y: np.ndarray) -> None: ...

    def predict_proba(self, X: list[dict[str, Any]]) -> np.ndarray: ...

    def predict_score(self, X: list[dict[str, Any]]) -> np.ndarray: ...

    def metadata(self) -> dict[str, Any]: ...
