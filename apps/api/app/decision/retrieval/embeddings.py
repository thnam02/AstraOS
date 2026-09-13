"""Embedding providers. Semantic model is isolated from domain ranking."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

from app.config import settings

logger = logging.getLogger("astraos.embeddings")

HASHING_MODEL = "hashing-vectorizer-384"
HASHING_DIM = 384
DEFAULT_SEMANTIC_MODEL = "BAAI/bge-small-en-v1.5"
RETRIEVAL_VERSION = "eligible-cosine.v1"
RERANK_VERSION = "grounded-rerank.v1"

_MODEL_LOCK = threading.Lock()
_LOADED_MODELS: dict[str, Any] = {}
_LOAD_TIMES_MS: dict[str, float] = {}


class EmbeddingProvider(Protocol):
    provider_name: str
    model_name: str
    dimensions: int

    def embed(self, text: str) -> list[float]: ...

    def embed_query(self, text: str) -> list[float]: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class LocalEmbeddingProvider:
    """Deterministic hashing embeddings. Offline fallback and CI default."""

    provider_name = "hashing"
    model_name = HASHING_MODEL
    dimensions = HASHING_DIM

    def __init__(self) -> None:
        self._vectorizer = HashingVectorizer(
            n_features=HASHING_DIM,
            alternate_sign=False,
            norm="l2",
            lowercase=True,
            ngram_range=(1, 2),
        )

    def embed(self, text: str) -> list[float]:
        matrix = self._vectorizer.transform([text or " "])
        vector = np.asarray(matrix.todense(), dtype=np.float32)[0]
        return [float(value) for value in vector]

    def embed_query(self, text: str) -> list[float]:
        return self.embed(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        matrix = self._vectorizer.transform([item or " " for item in texts])
        dense = np.asarray(matrix.todense(), dtype=np.float32)
        return [[float(value) for value in row] for row in dense]


HashingEmbeddingProvider = LocalEmbeddingProvider


class DeterministicEmbeddingProvider:
    """Tiny mock used when a test needs an injected provider."""

    provider_name = "mock"
    model_name = "deterministic-mock-16"
    dimensions = 16

    def embed(self, text: str) -> list[float]:
        rng = np.random.default_rng(abs(hash(text)) % (2**32))
        vector = rng.random(self.dimensions)
        norm = float(np.linalg.norm(vector)) or 1.0
        return [float(value / norm) for value in vector]

    def embed_query(self, text: str) -> list[float]:
        return self.embed(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(item) for item in texts]


class SentenceTransformerEmbeddingProvider:
    """Local sentence-transformer embeddings. Loaded once per process."""

    provider_name = "sentence_transformer"

    def __init__(
        self,
        model_id: str | None = None,
        *,
        batch_size: int | None = None,
    ) -> None:
        self.model_id = model_id or settings.semantic_embedding_model
        self.model_name = self.model_id
        self.batch_size = batch_size or settings.semantic_embedding_batch_size
        self.dimensions = _declared_dimensions(self.model_id)
        self._model: Any | None = None

    def ensure_loaded(self) -> Any:
        if self._model is not None:
            return self._model
        self._model = load_sentence_transformer(self.model_id)
        self.dimensions = _model_dimension(self._model)
        return self._model

    def embed(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_query(self, text: str) -> list[float]:
        return self._encode([_query_text(self.model_id, text)])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._encode([_document_text(self.model_id, item) for item in texts])

    def _encode(self, texts: list[str]) -> list[list[float]]:
        model = self.ensure_loaded()
        vectors = model.encode(
            texts,
            batch_size=max(1, self.batch_size),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        array = np.asarray(vectors, dtype=np.float32)
        if array.ndim == 1:
            array = array.reshape(1, -1)
        self.dimensions = int(array.shape[1])
        return [[float(value) for value in row] for row in array]


@dataclass
class EmbeddingResolution:
    provider: EmbeddingProvider
    requested: str
    used: str
    fallback_used: bool
    fallback_reason: str | None
    model: str
    dimension: int

    def metadata(self) -> dict[str, object]:
        return {
            "provider_requested": self.requested,
            "provider_used": self.used,
            "model": self.model,
            "dimension": self.dimension,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "retrieval_version": RETRIEVAL_VERSION,
            "rerank_version": RERANK_VERSION,
        }


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    a = np.asarray(left, dtype=np.float64)
    b = np.asarray(right, dtype=np.float64)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.clip(np.dot(a, b) / denom, -1.0, 1.0))


def resolve_embedding_provider(
    requested: str | None = None,
) -> EmbeddingResolution:
    mode = (requested or settings.semantic_embedding_provider or "hashing").strip()
    mode = mode.lower().replace("-", "_")
    provider: EmbeddingProvider
    if mode in {"hashing", "hash", "local"}:
        provider = LocalEmbeddingProvider()
        return EmbeddingResolution(
            provider=provider,
            requested="hashing",
            used="hashing",
            fallback_used=False,
            fallback_reason=None,
            model=provider.model_name,
            dimension=provider.dimensions,
        )
    if mode not in {"sentence_transformer", "sentence_transformers", "st"}:
        provider = LocalEmbeddingProvider()
        return EmbeddingResolution(
            provider=provider,
            requested=mode,
            used="hashing",
            fallback_used=True,
            fallback_reason="unknown_provider",
            model=provider.model_name,
            dimension=provider.dimensions,
        )
    try:
        if not sentence_transformers_importable():
            raise RuntimeError("sentence_transformers_missing")
        if (
            not semantic_model_cached()
            and not settings.semantic_embedding_allow_download
        ):
            raise RuntimeError("semantic_model_not_cached")
        provider = SentenceTransformerEmbeddingProvider()
        return EmbeddingResolution(
            provider=provider,
            requested="sentence_transformer",
            used="sentence_transformer",
            fallback_used=False,
            fallback_reason=None,
            model=provider.model_name,
            dimension=provider.dimensions,
        )
    except Exception as exc:  # noqa: BLE001
        reason = _fallback_reason(exc)
        logger.warning("semantic_embedding_fallback reason=%s", reason)
        provider = LocalEmbeddingProvider()
        return EmbeddingResolution(
            provider=provider,
            requested="sentence_transformer",
            used="hashing",
            fallback_used=True,
            fallback_reason=reason,
            model=provider.model_name,
            dimension=provider.dimensions,
        )


def default_embedding_provider() -> EmbeddingProvider:
    return resolve_embedding_provider().provider


def sentence_transformers_importable() -> bool:
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        return False
    return True


def load_sentence_transformer(model_id: str) -> Any:
    import time

    with _MODEL_LOCK:
        cached = _LOADED_MODELS.get(model_id)
        if cached is not None:
            return cached
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("sentence_transformers_missing") from exc
        started = time.perf_counter()
        local_only = not settings.semantic_embedding_allow_download
        model = SentenceTransformer(model_id, local_files_only=local_only)
        model.eval()
        _LOADED_MODELS[model_id] = model
        _LOAD_TIMES_MS[model_id] = (time.perf_counter() - started) * 1000
        logger.info(
            "semantic_model_loaded model=%s dim=%s load_ms=%.1f",
            model_id,
            _model_dimension(model),
            _LOAD_TIMES_MS[model_id],
        )
        return model


def last_model_load_ms(model_id: str | None = None) -> float | None:
    key = model_id or settings.semantic_embedding_model
    return _LOAD_TIMES_MS.get(key)


def semantic_model_cached(model_id: str | None = None) -> bool:
    name = model_id or settings.semantic_embedding_model
    if name in _LOADED_MODELS:
        return True
    slug = name.replace("/", "--")
    hub = Path.home() / ".cache" / "huggingface" / "hub" / f"models--{slug}"
    return hub.exists()


def _model_dimension(model: Any) -> int:
    getter = getattr(model, "get_embedding_dimension", None)
    if callable(getter):
        return int(getter())
    return int(model.get_sentence_embedding_dimension())


def _declared_dimensions(model_id: str) -> int:
    lowered = model_id.lower()
    if "minilm-l6" in lowered or "bge-small" in lowered or "e5-small" in lowered:
        return 384
    if "bge-base" in lowered or "e5-base" in lowered:
        return 768
    return 384


def _query_text(model_id: str, text: str) -> str:
    body = text or " "
    lowered = model_id.lower()
    if "bge-" in lowered:
        return (
            "Represent this sentence for searching relevant passages: " + body
        )
    if "e5-" in lowered:
        return f"query: {body}"
    return body


def _document_text(model_id: str, text: str) -> str:
    body = text or " "
    if "e5-" in model_id.lower():
        return f"passage: {body}"
    return body


def _fallback_reason(exc: Exception) -> str:
    message = str(exc).lower()
    if "sentence_transformers_missing" in message or "no module" in message:
        return "model_unavailable"
    if "offline" in message or "connect" in message or "timed out" in message:
        return "model_unavailable"
    if "not found" in message or "does not exist" in message:
        return "model_unavailable"
    return "model_unavailable"


# Backwards-compatible names.
EMBEDDING_MODEL = HASHING_MODEL
EMBEDDING_DIM = HASHING_DIM
