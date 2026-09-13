"""Optional live sentence-transformer inference. Not part of default CI."""

from __future__ import annotations

import os

import numpy as np
import pytest

from app.decision.retrieval.embeddings import (
    SentenceTransformerEmbeddingProvider,
    cosine_similarity,
    semantic_model_cached,
    sentence_transformers_importable,
)

pytestmark = pytest.mark.semantic_model_integration


def _available() -> bool:
    return (
        os.environ.get("SEMANTIC_MODEL_INTEGRATION") == "1"
        and sentence_transformers_importable()
        and semantic_model_cached()
    )


@pytest.mark.skipif(not _available(), reason="semantic model not cached")
def test_live_semantic_sanity() -> None:
    provider = SentenceTransformerEmbeddingProvider()
    documents = provider.embed_documents(
        [
            "Product: Sonic Cabin 32\nCategory: wireless over-ear headphones\n"
            "Verified facts:\n- active noise cancellation\n- 79-hour battery\n"
            "- 230g\n- foldable\nUse-case representation: Lightweight ANC "
            "headphones suited to long-duration travel, extended wear.",
            "Product: Vanta Studio X2\nCategory: wired over-ear headphones\n"
            "Verified facts:\n- no active noise cancellation\n- wired\n"
            "Use-case representation: headphones suited to studio work.",
            "Product: Pulse Gym 11\nCategory: wireless over-ear headphones\n"
            "Verified facts:\n- water resistance IPX4\n- 18-hour battery",
        ]
    )
    queries = [
        provider.embed_query(
            "Long-haul travel.\nExtended continuous use.\nComfort high.\n"
            "Reliability is more important than minimum price."
        ),
        provider.embed_query("Studio mixing. Wired. Critical listening."),
    ]
    assert all(len(row) == provider.dimensions for row in [*documents, *queries])
    assert all(np.isfinite(row).all() for row in [*documents, *queries])
    for row in [*documents, *queries]:
        assert abs(float(np.linalg.norm(row)) - 1.0) < 1e-4
    travel = cosine_similarity(queries[0], documents[0])
    unrelated = cosine_similarity(queries[0], documents[1])
    assert travel > unrelated
