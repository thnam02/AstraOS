"""Provider selection, fallback metadata, and mocked semantic encode."""

from __future__ import annotations

import numpy as np
import pytest

from app.decision.retrieval.embeddings import (
    HASHING_DIM,
    HASHING_MODEL,
    LocalEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
    _document_text,
    _query_text,
    cosine_similarity,
    resolve_embedding_provider,
)
from app.repositories.embedding import is_current


class _FakeModel:
    def __init__(self, dim: int = 8) -> None:
        self.dim = dim

    def get_sentence_embedding_dimension(self) -> int:
        return self.dim

    def eval(self) -> _FakeModel:
        return self

    def encode(
        self,
        texts: list[str],
        batch_size: int = 32,
        convert_to_numpy: bool = True,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
    ) -> np.ndarray:
        del batch_size, convert_to_numpy, show_progress_bar
        rows = []
        for text in texts:
            rng = np.random.default_rng(abs(hash(text)) % (2**32))
            vector = rng.random(self.dim).astype(np.float32)
            if normalize_embeddings:
                vector = vector / (np.linalg.norm(vector) or 1.0)
            rows.append(vector)
        return np.stack(rows)


def test_hashing_resolution() -> None:
    resolution = resolve_embedding_provider("hashing")
    assert resolution.requested == "hashing"
    assert resolution.used == "hashing"
    assert resolution.fallback_used is False
    assert resolution.fallback_reason is None
    assert resolution.dimension == HASHING_DIM
    assert resolution.model == HASHING_MODEL


def test_unknown_provider_falls_back() -> None:
    resolution = resolve_embedding_provider("pinecone")
    assert resolution.requested == "pinecone"
    assert resolution.used == "hashing"
    assert resolution.fallback_used is True
    assert resolution.fallback_reason == "unknown_provider"


def test_semantic_falls_back_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.decision.retrieval.embeddings.sentence_transformers_importable",
        lambda: False,
    )
    resolution = resolve_embedding_provider("sentence_transformer")
    assert resolution.requested == "sentence_transformer"
    assert resolution.used == "hashing"
    assert resolution.fallback_used is True
    assert resolution.fallback_reason == "model_unavailable"
    meta = resolution.metadata()
    assert meta["fallback_used"] is True
    assert meta["provider_used"] == "hashing"


def test_semantic_falls_back_when_uncached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.decision.retrieval.embeddings.sentence_transformers_importable",
        lambda: True,
    )
    monkeypatch.setattr(
        "app.decision.retrieval.embeddings.semantic_model_cached",
        lambda model_id=None: False,
    )
    monkeypatch.setattr(
        "app.decision.retrieval.embeddings.settings.semantic_embedding_allow_download",
        False,
    )
    resolution = resolve_embedding_provider("sentence_transformer")
    assert resolution.fallback_used is True
    assert resolution.fallback_reason == "model_unavailable"


def test_semantic_selected_when_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.decision.retrieval.embeddings.sentence_transformers_importable",
        lambda: True,
    )
    monkeypatch.setattr(
        "app.decision.retrieval.embeddings.semantic_model_cached",
        lambda model_id=None: True,
    )
    resolution = resolve_embedding_provider("sentence_transformer")
    assert resolution.used == "sentence_transformer"
    assert resolution.fallback_used is False
    assert resolution.model == "BAAI/bge-small-en-v1.5"
    assert resolution.dimension == 384


def test_mocked_semantic_encode_and_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.decision.retrieval.embeddings.load_sentence_transformer",
        lambda model_id: _FakeModel(8),
    )
    provider = SentenceTransformerEmbeddingProvider(model_id="mock-bge-small")
    query = provider.embed_query("long-haul travel headphones")
    docs = provider.embed_documents(
        [
            "travel ANC 79-hour battery 230g",
            "studio wired analog mixing",
        ]
    )
    assert len(query) == 8
    assert len(docs) == 2
    assert all(len(row) == 8 for row in docs)
    assert all(np.isfinite(row).all() for row in [query, *docs])
    magnitude = float(np.linalg.norm(query))
    assert abs(magnitude - 1.0) < 1e-5
    travel = cosine_similarity(query, docs[0])
    studio = cosine_similarity(query, docs[1])
    assert travel != studio


def test_hashing_batch_matches_single() -> None:
    provider = LocalEmbeddingProvider()
    texts = ["travel comfort", "studio mixing"]
    batched = provider.embed_documents(texts)
    singles = [provider.embed(text) for text in texts]
    assert batched == singles


def test_bge_query_prefix() -> None:
    query = _query_text("BAAI/bge-small-en-v1.5", "comfort")
    passage = _document_text("BAAI/bge-small-en-v1.5", "comfort")
    assert query.startswith("Represent this sentence for searching relevant passages:")
    assert passage == "comfort"


def test_e5_prefixes() -> None:
    assert _query_text("intfloat/e5-small-v2", "x") == "query: x"
    assert _document_text("intfloat/e5-small-v2", "x") == "passage: x"


def test_is_current_rejects_dimension_mismatch() -> None:
    class _Row:
        embedding_model = HASHING_MODEL
        semantic_document_version = "product_semantic.v1"
        document_hash = "abc"
        embedding = [0.1, 0.2]

    assert (
        is_current(
            _Row(),  # type: ignore[arg-type]
            model=HASHING_MODEL,
            version="product_semantic.v1",
            document_hash="abc",
            dimensions=384,
        )
        is False
    )


def test_is_current_rejects_model_mismatch() -> None:
    class _Row:
        embedding_model = HASHING_MODEL
        semantic_document_version = "product_semantic.v1"
        document_hash = "abc"
        embedding = [0.1] * 384

    assert (
        is_current(
            _Row(),  # type: ignore[arg-type]
            model="BAAI/bge-small-en-v1.5",
            version="product_semantic.v1",
            document_hash="abc",
            dimensions=384,
        )
        is False
    )
