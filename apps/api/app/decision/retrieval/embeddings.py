"""Embedding providers. Tests never require a hosted model."""

from __future__ import annotations

from typing import Protocol

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

EMBEDDING_MODEL = "hashing-vectorizer-384"
EMBEDDING_DIM = 384


class EmbeddingProvider(Protocol):
    model_name: str
    dimensions: int

    def embed(self, text: str) -> list[float]: ...


class LocalEmbeddingProvider:
    """Deterministic local embeddings. No download, no API key."""

    model_name = EMBEDDING_MODEL
    dimensions = EMBEDDING_DIM

    def __init__(self) -> None:
        self._vectorizer = HashingVectorizer(
            n_features=EMBEDDING_DIM,
            alternate_sign=False,
            norm="l2",
            lowercase=True,
            ngram_range=(1, 2),
        )

    def embed(self, text: str) -> list[float]:
        matrix = self._vectorizer.transform([text or " "])
        vector = np.asarray(matrix.todense(), dtype=np.float32)[0]
        return [float(value) for value in vector]


class DeterministicEmbeddingProvider:
    """Tiny mock used when a test needs an injected provider."""

    model_name = "deterministic-mock-16"
    dimensions = 16

    def embed(self, text: str) -> list[float]:
        rng = np.random.default_rng(abs(hash(text)) % (2**32))
        vector = rng.random(self.dimensions)
        norm = float(np.linalg.norm(vector)) or 1.0
        return [float(value / norm) for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    a = np.asarray(left, dtype=np.float64)
    b = np.asarray(right, dtype=np.float64)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.clip(np.dot(a, b) / denom, -1.0, 1.0))


def default_embedding_provider() -> LocalEmbeddingProvider:
    return LocalEmbeddingProvider()
