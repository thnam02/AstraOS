"""Parse intent, scan the catalogue, persist a qualification trace."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.eligibility.evaluator import EligibilityEvaluator
from app.decision.eligibility.models import ProductEligibilityResult
from app.decision.eligibility.snapshot import variant_to_snapshot
from app.decision.intent.models import ShoppingIntent
from app.decision.intent.parser import parse_intent
from app.models import QualificationRun, QualificationVariantResult
from app.repositories.product import ProductRepository
from app.repositories.qualification import QualificationRepository
from app.schemas.intent import (
    QualificationRunResponse,
    QualificationSummary,
    QualificationTiming,
    QualificationVariantDetail,
    QualifyResponse,
    VariantQualificationCard,
)

logger = logging.getLogger("astraos.qualification")

PREVIEW_LIMIT = 30


class IntentQualificationService:
    """Application service. Routes stay thin; eligibility stays deterministic."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.products = ProductRepository(session)
        self.runs = QualificationRepository(session)
        self.evaluator = EligibilityEvaluator()

    async def qualify(
        self, text: str, parser_mode: str | None = None
    ) -> QualifyResponse:
        started = time.perf_counter()
        intent = await parse_intent(text, parser_mode)
        parse_ms = (time.perf_counter() - started) * 1000

        eligibility_started = time.perf_counter()
        variants = await self.products.list_active_variants(category=intent.category)
        results = [
            self.evaluator.evaluate_variant(variant_to_snapshot(variant), intent)
            for variant in variants
        ]
        eligibility_ms = (time.perf_counter() - eligibility_started) * 1000
        total_ms = (time.perf_counter() - started) * 1000

        eligible = [row for row in results if row.outcome == "eligible"]
        rejected = [row for row in results if row.outcome == "rejected"]
        uncertain = [row for row in results if row.outcome == "uncertain"]
        summary = QualificationSummary(
            variants_checked=len(results),
            eligible=len(eligible),
            violated=len(rejected),
            uncertain=len(uncertain),
        )
        timing = QualificationTiming(
            parse_ms=round(parse_ms, 2),
            eligibility_ms=round(eligibility_ms, 2),
            total_ms=round(total_ms, 2),
        )
        run = await self._persist(text, intent, results, summary, timing)
        logger.info(
            "qualification_completed run_id=%s parser=%s checked=%s eligible=%s "
            "violated=%s uncertain=%s parse_ms=%.2f eligibility_ms=%.2f total_ms=%.2f",
            run.id,
            intent.parser_type,
            summary.variants_checked,
            summary.eligible,
            summary.violated,
            summary.uncertain,
            timing.parse_ms,
            timing.eligibility_ms,
            timing.total_ms,
        )
        return QualifyResponse(
            run_id=run.id,
            status=intent.status.value,
            intent=intent,
            summary=summary,
            timing=timing,
            eligible_products=[_card(row) for row in eligible],
            uncertain_products=[_card(row) for row in uncertain[:PREVIEW_LIMIT]],
            rejected_products=[_card(row) for row in rejected[:PREVIEW_LIMIT]],
            rejected_truncated=len(rejected) > PREVIEW_LIMIT,
            uncertain_truncated=len(uncertain) > PREVIEW_LIMIT,
        )

    async def get_run(
        self,
        run_id: uuid.UUID,
        *,
        outcome: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> QualificationRunResponse | None:
        run = await self.runs.get(run_id)
        if run is None:
            return None
        rows, total = await self.runs.list_variant_results(
            run_id, outcome=outcome, limit=limit, offset=offset
        )
        return QualificationRunResponse(
            run_id=run.id,
            status=run.status,
            raw_intent=run.raw_intent,
            intent=ShoppingIntent.model_validate(run.parsed_intent),
            parser_type=run.parser_type,
            summary=run.summary,
            created_at=run.created_at,
            variants=[_card_from_row(row) for row in rows],
            total_variants=total,
            limit=limit,
            offset=offset,
        )

    async def get_variant(
        self, run_id: uuid.UUID, variant_id: uuid.UUID
    ) -> QualificationVariantDetail | None:
        row = await self.runs.get_variant_result(run_id, variant_id)
        if row is None:
            return None
        return QualificationVariantDetail(run_id=run_id, variant=_card_from_row(row))

    async def _persist(
        self,
        raw_text: str,
        intent: ShoppingIntent,
        results: list[ProductEligibilityResult],
        summary: QualificationSummary,
        timing: QualificationTiming,
    ) -> QualificationRun:
        run = QualificationRun(
            raw_intent=raw_text,
            parsed_intent=intent.model_dump(mode="json"),
            parser_type=intent.parser_type,
            status=intent.status.value,
            summary={
                **summary.model_dump(),
                **timing.model_dump(),
                "parser_type": intent.parser_type,
            },
        )
        for result in results:
            run.variant_results.append(
                QualificationVariantResult(
                    product_id=result.product_id,
                    variant_id=result.variant_id,
                    sku=result.sku,
                    product_name=result.product_name,
                    brand=result.brand,
                    variant_name=result.variant_name,
                    base_price_cents=result.base_price_cents,
                    eligible=result.eligible,
                    outcome=result.outcome,
                    violated_count=result.violated_count,
                    unknown_count=result.unknown_count,
                    satisfied_count=result.satisfied_count,
                    exclusion_reasons=result.exclusion_reasons,
                    evaluations=[
                        item.model_dump(mode="json") for item in result.evaluations
                    ],
                )
            )
        await self.runs.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run


def _card(result: ProductEligibilityResult) -> VariantQualificationCard:
    return VariantQualificationCard(
        product_id=result.product_id,
        variant_id=result.variant_id,
        sku=result.sku,
        product_name=result.product_name,
        brand=result.brand,
        variant_name=result.variant_name,
        base_price_cents=result.base_price_cents,
        eligible=result.eligible,
        outcome=result.outcome,
        violated_count=result.violated_count,
        unknown_count=result.unknown_count,
        satisfied_count=result.satisfied_count,
        exclusion_reasons=result.exclusion_reasons,
        evaluations=result.evaluations,
    )


def _card_from_row(row: QualificationVariantResult) -> VariantQualificationCard:
    payload: dict[str, Any] = {
        "product_id": row.product_id,
        "variant_id": row.variant_id,
        "sku": row.sku,
        "product_name": row.product_name,
        "brand": row.brand,
        "variant_name": row.variant_name,
        "base_price_cents": row.base_price_cents,
        "eligible": row.eligible,
        "outcome": row.outcome,
        "violated_count": row.violated_count,
        "unknown_count": row.unknown_count,
        "satisfied_count": row.satisfied_count,
        "exclusion_reasons": row.exclusion_reasons,
        "evaluations": row.evaluations,
    }
    return VariantQualificationCard.model_validate(payload)
