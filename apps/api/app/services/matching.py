"""Deep intent analysis and semantic matching over eligible SKUs."""

from __future__ import annotations

import logging
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.eligibility.evaluator import EligibilityEvaluator
from app.decision.eligibility.models import ProductEligibilityResult
from app.decision.eligibility.snapshot import VariantSnapshot, variant_to_snapshot
from app.decision.intent.models import ShoppingIntent
from app.decision.intent.parser import parse_intent
from app.decision.retrieval.documents import (
    DOCUMENT_VERSION,
    ProductSemanticDocument,
    build_product_document,
    document_hash,
)
from app.decision.retrieval.embeddings import (
    EmbeddingProvider,
    EmbeddingResolution,
    resolve_embedding_provider,
)
from app.decision.retrieval.matcher import rank_eligible
from app.decision.retrieval.models import RankedProductMatch
from app.models import MatchResult, MatchRun
from app.repositories.embedding import EmbeddingRepository, is_current
from app.repositories.match import MatchRepository
from app.repositories.product import ProductRepository
from app.schemas.intent import QualificationSummary
from app.schemas.match import (
    AnalyseResponse,
    MatchResponse,
    MatchRunResponse,
    MatchTiming,
    SemanticMatchingBlock,
)

logger = logging.getLogger("astraos.matching")

MATCH_LIMIT_STORE = 50


class SemanticMatchingService:
    def __init__(
        self,
        session: AsyncSession,
        provider: EmbeddingProvider | None = None,
    ) -> None:
        self.session = session
        self.products = ProductRepository(session)
        self.embeddings = EmbeddingRepository(session)
        self.runs = MatchRepository(session)
        self.evaluator = EligibilityEvaluator()
        if provider is not None:
            self.resolution = EmbeddingResolution(
                provider=provider,
                requested=getattr(provider, "provider_name", "injected"),
                used=getattr(provider, "provider_name", "injected"),
                fallback_used=False,
                fallback_reason=None,
                model=provider.model_name,
                dimension=provider.dimensions,
            )
            self.provider = provider
        else:
            self.resolution = resolve_embedding_provider()
            self.provider = self.resolution.provider

    async def analyse(
        self, text: str, parser_mode: str | None = None
    ) -> AnalyseResponse:
        started = time.perf_counter()
        intent = await parse_intent(text, parser_mode)
        parse_ms = (time.perf_counter() - started) * 1000
        return AnalyseResponse(intent=intent, parse_ms=round(parse_ms, 2))

    async def match(
        self,
        text: str,
        parser_mode: str | None = None,
        limit: int = 10,
    ) -> MatchResponse:
        started = time.perf_counter()
        intent = await parse_intent(text, parser_mode)
        parse_ms = (time.perf_counter() - started) * 1000
        return await self._match_intent(
            intent, raw_text=text, parse_ms=parse_ms, limit=limit, started=started
        )

    async def match_from_intent(
        self,
        intent: ShoppingIntent,
        *,
        limit: int = 10,
    ) -> MatchResponse:
        started = time.perf_counter()
        return await self._match_intent(
            intent,
            raw_text=intent.raw_text,
            parse_ms=0.0,
            limit=limit,
            started=started,
        )

    async def _match_intent(
        self,
        intent: ShoppingIntent,
        *,
        raw_text: str,
        parse_ms: float,
        limit: int,
        started: float,
    ) -> MatchResponse:
        qualify_started = time.perf_counter()
        variants = await self.products.list_active_variants(category=intent.category)
        snapshots = [variant_to_snapshot(row) for row in variants]
        results = [
            self.evaluator.evaluate_variant(snapshot, intent) for snapshot in snapshots
        ]
        snapshot_by_id = {item.variant_id: item for item in snapshots}
        eligible = [row for row in results if row.outcome == "eligible"]
        rejected = [row for row in results if row.outcome == "rejected"]
        uncertain = [row for row in results if row.outcome == "uncertain"]
        qualification_ms = (time.perf_counter() - qualify_started) * 1000

        embed_started = time.perf_counter()
        eligible_snaps = [snapshot_by_id[row.variant_id] for row in eligible]
        vectors = await self._ensure_embeddings(eligible_snaps)
        embedding_ms = (time.perf_counter() - embed_started) * 1000

        rerank_started = time.perf_counter()
        ranked = rank_eligible(intent, eligible_snaps, vectors, self.provider)
        rerank_ms = (time.perf_counter() - rerank_started) * 1000
        total_ms = (time.perf_counter() - started) * 1000

        summary = QualificationSummary(
            variants_checked=len(results),
            eligible=len(eligible),
            violated=len(rejected),
            uncertain=len(uncertain),
        )
        timing = MatchTiming(
            intent_parse_ms=round(parse_ms, 2),
            qualification_ms=round(qualification_ms, 2),
            embedding_ms=round(embedding_ms, 2),
            rerank_ms=round(rerank_ms, 2),
            total_ms=round(total_ms, 2),
        )
        top = ranked[:limit]
        run = await self._persist(raw_text, intent, results, top, summary, timing)
        logger.info(
            "match_completed run_id=%s parser=%s provider_requested=%s "
            "provider_used=%s fallback=%s model=%s checked=%s eligible=%s "
            "matched=%s parse_ms=%.2f qualify_ms=%.2f embed_ms=%.2f "
            "rerank_ms=%.2f total_ms=%.2f",
            run.id,
            intent.parser_type,
            self.resolution.requested,
            self.resolution.used,
            self.resolution.fallback_used,
            self.provider.model_name,
            summary.variants_checked,
            summary.eligible,
            len(top),
            timing.intent_parse_ms,
            timing.qualification_ms,
            timing.embedding_ms,
            timing.rerank_ms,
            timing.total_ms,
        )
        return MatchResponse(
            run_id=run.id,
            status=intent.status.value,
            intent=intent,
            qualification=summary,
            semantic_matching=self._matching_block(top),
            timing=timing,
        )

    async def get_run(self, run_id: uuid.UUID) -> MatchRunResponse | None:
        run = await self.runs.get(run_id)
        if run is None:
            return None
        matches = [
            RankedProductMatch.model_validate(row.payload)
            for row in sorted(run.matches, key=lambda item: item.rank)
        ]
        return MatchRunResponse(
            run_id=run.id,
            status=run.status,
            intent=ShoppingIntent.model_validate(run.parsed_intent),
            qualification=run.qualification_summary,
            semantic_matching=_block_from_run(run, matches),
            timing=run.timing,
            created_at=run.created_at,
        )

    async def _ensure_embeddings(
        self, snapshots: list[VariantSnapshot]
    ) -> dict[uuid.UUID, list[float]]:
        vectors: dict[uuid.UUID, list[float]] = {}
        pending: list[tuple[VariantSnapshot, ProductSemanticDocument, str]] = []
        existing = await self.embeddings.list_for_variants(
            [item.variant_id for item in snapshots]
        )
        for snapshot in snapshots:
            document = build_product_document(snapshot)
            digest = document_hash(document)
            row = existing.get(snapshot.variant_id)
            if is_current(
                row,
                model=self.provider.model_name,
                version=DOCUMENT_VERSION,
                document_hash=digest,
                dimensions=self.provider.dimensions,
            ):
                assert row is not None
                vectors[snapshot.variant_id] = [float(v) for v in row.embedding]
                continue
            pending.append((snapshot, document, digest))
        if pending:
            encode = getattr(self.provider, "embed_documents", None)
            texts = [item[1].text for item in pending]
            try:
                encoded = (
                    encode(texts)
                    if callable(encode)
                    else [self.provider.embed(text) for text in texts]
                )
            except Exception:
                logger.exception("embedding_batch_failed count=%s", len(pending))
                raise
            for (snapshot, _document, digest), vector in zip(
                pending, encoded, strict=True
            ):
                await self.embeddings.upsert(
                    variant_id=snapshot.variant_id,
                    embedding=vector,
                    embedding_model=self.provider.model_name,
                    semantic_document_version=DOCUMENT_VERSION,
                    document_hash=digest,
                )
                vectors[snapshot.variant_id] = vector
        return vectors

    def _matching_block(
        self, matches: list[RankedProductMatch]
    ) -> SemanticMatchingBlock:
        meta = self.resolution.metadata()
        return SemanticMatchingBlock(
            model=self.provider.model_name,
            document_version=DOCUMENT_VERSION,
            matches=matches,
            provider_requested=str(meta["provider_requested"]),
            provider_used=str(meta["provider_used"]),
            dimension=_as_int(meta["dimension"]),
            fallback_used=bool(meta["fallback_used"]),
            fallback_reason=(
                str(meta["fallback_reason"]) if meta["fallback_reason"] else None
            ),
            retrieval_version=str(meta["retrieval_version"]),
            rerank_version=str(meta["rerank_version"]),
        )

    async def _persist(
        self,
        raw_text: str,
        intent: ShoppingIntent,
        results: list[ProductEligibilityResult],
        ranked: list[RankedProductMatch],
        summary: QualificationSummary,
        timing: MatchTiming,
    ) -> MatchRun:
        run = MatchRun(
            raw_intent=raw_text,
            parsed_intent=intent.model_dump(mode="json"),
            parser_type=intent.parser_type,
            status=intent.status.value,
            embedding_model=self.provider.model_name,
            semantic_document_version=DOCUMENT_VERSION,
            qualification_summary=summary.model_dump(),
            timing={**timing.model_dump(), "embedding": self.resolution.metadata()},
            eligible_variant_ids=[
                str(row.variant_id) for row in results if row.outcome == "eligible"
            ],
        )
        for item in ranked[:MATCH_LIMIT_STORE]:
            run.matches.append(
                MatchResult(
                    product_id=item.product_id,
                    variant_id=item.variant_id,
                    sku=item.sku,
                    product_name=item.product_name,
                    brand=item.brand,
                    rank=item.rank,
                    scores={
                        "semantic_similarity": item.semantic_similarity,
                        "product_fit": item.product_fit,
                        "context_fit": item.context_fit,
                        "preference_fit": item.preference_fit,
                        "evidence_coverage": item.evidence_coverage,
                        "overall_semantic_fit": item.overall_semantic_fit,
                    },
                    payload=item.model_dump(mode="json"),
                )
            )
        await self.runs.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run


def _block_from_run(
    run: MatchRun, matches: list[RankedProductMatch]
) -> SemanticMatchingBlock:
    meta = {}
    if isinstance(run.timing, dict):
        stored = run.timing.get("embedding")
        if isinstance(stored, dict):
            meta = stored
    return SemanticMatchingBlock(
        model=run.embedding_model,
        document_version=run.semantic_document_version,
        matches=matches,
        provider_requested=_as_str(meta.get("provider_requested")),
        provider_used=_as_str(meta.get("provider_used"))
        or _provider_from_model(run.embedding_model),
        dimension=_as_int(meta.get("dimension")),
        fallback_used=bool(meta.get("fallback_used", False)),
        fallback_reason=_as_str(meta.get("fallback_reason")),
        retrieval_version=_as_str(meta.get("retrieval_version")),
        rerank_version=_as_str(meta.get("rerank_version")),
    )


def _provider_from_model(model: str) -> str:
    if model.startswith("hashing"):
        return "hashing"
    if model.startswith("deterministic"):
        return "mock"
    return "sentence_transformer"


def _as_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _as_int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    return None
