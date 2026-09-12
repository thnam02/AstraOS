"""Embedding provider tests. No live model."""

from app.decision.retrieval.embeddings import (
    DeterministicEmbeddingProvider,
    LocalEmbeddingProvider,
    cosine_similarity,
)


def test_local_provider_is_deterministic() -> None:
    provider = LocalEmbeddingProvider()
    first = provider.embed("Long-haul travel. Low fatigue.")
    second = provider.embed("Long-haul travel. Low fatigue.")
    assert first == second
    assert len(first) == provider.dimensions


def test_similar_text_outranks_unrelated() -> None:
    provider = LocalEmbeddingProvider()
    intent = provider.embed("long haul travel comfort low fatigue")
    close = provider.embed("travel comfort extended wear low fatigue")
    far = provider.embed("studio mixing cable analog")
    assert cosine_similarity(intent, close) > cosine_similarity(intent, far)


def test_mock_provider_normalized() -> None:
    provider = DeterministicEmbeddingProvider()
    vector = provider.embed("abc")
    total = sum(value * value for value in vector) ** 0.5
    assert abs(total - 1.0) < 1e-6


def test_mismatched_dimensions_are_zero() -> None:
    assert cosine_similarity([1.0], [1.0, 0.0]) == 0.0
