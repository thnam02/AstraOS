"""Construct commercial offer spaces from matched products."""

from __future__ import annotations

import logging
import time
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.decision.intent.models import ShoppingIntent
from app.decision.offers.bundles import relevant_bundle_codes
from app.decision.offers.constructor import construct_variant, prune_limits
from app.decision.offers.dimensions import (
    load_bundles,
    load_deliveries,
    load_returns,
    load_warranties,
)
from app.decision.offers.models import (
    CONSTRUCTION_VERSION,
    ConstructionLimits,
    FeasibilityStatus,
    OfferCandidate,
)
from app.decision.offers.prices import generate_price_options
from app.decision.retrieval.models import RankedProductMatch
from app.models.offer import OfferCandidateRow, OfferConstructionRun
from app.repositories.match import MatchRepository
from app.repositories.offer import OfferRepository
from app.repositories.policy import MerchantPolicyRepository
from app.repositories.product import ProductRepository
from app.schemas.offer import (
    GenerateOffersResponse,
    OfferDetailResponse,
    OfferDimensions,
    OfferRunResponse,
    OfferSummary,
    OfferTiming,
    to_public,
)
from app.services.matching import SemanticMatchingService

logger = logging.getLogger("astraos.offers")


class OfferConstructionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.products = ProductRepository(session)
        self.policy = MerchantPolicyRepository(session)
        self.matches = MatchRepository(session)
        self.offers = OfferRepository(session)
        self.matching = SemanticMatchingService(session)

    async def generate(
        self,
        *,
        intent_text: str | None = None,
        match_run_id: uuid.UUID | None = None,
        parser_mode: str | None = None,
        max_products: int = 8,
        preview_status: str = "FEASIBLE",
        preview_limit: int = 50,
        intent_override: ShoppingIntent | None = None,
    ) -> GenerateOffersResponse:
        started = time.perf_counter()
        match_started = time.perf_counter()
        ranked, intent, resolved_match_id = await self._load_matches(
            intent_text, match_run_id, parser_mode, max_products
        )
        if intent_override is not None:
            intent = intent_override
        matching_load_ms = (time.perf_counter() - match_started) * 1000

        dim_started = time.perf_counter()
        policy = await self.policy.get_active()
        if policy is None:
            raise RuntimeError("No active merchant policy.")
        variants = await self.products.list_variants_by_ids(
            [item.variant_id for item in ranked]
        )
        relevant = relevant_bundle_codes(intent)
        limits = ConstructionLimits(
            max_products=max_products,
            offer_ttl_seconds=settings.offer_ttl_seconds,
        )
        dim_counts: list[tuple[int, int, int, int, int]] = []
        for variant in variants:
            prices = generate_price_options(
                variant.base_price_cents,
                policy.maximum_discount_rate,
                limit=limits.max_price_options,
            )
            dim_counts.append(
                (
                    len(prices),
                    len(load_deliveries(variant)),
                    len(load_warranties(variant)),
                    len(load_bundles(variant, relevant)),
                    len(load_returns(variant)),
                )
            )
        limits, pruning_reason, estimated = prune_limits(
            product_count=len(variants),
            dim_counts=dim_counts,
            limits=limits,
        )
        variants = variants[: limits.max_products]
        dimension_load_ms = (time.perf_counter() - dim_started) * 1000

        gen_started = time.perf_counter()
        expires_at = datetime.now(UTC) + timedelta(seconds=limits.offer_ttl_seconds)
        constructed: list[OfferCandidate] = []
        dim_acc = {
            "prices": 0,
            "deliveries": 0,
            "warranties": 0,
            "bundles": 0,
            "returns": 0,
        }
        for variant in variants:
            rows, dims = construct_variant(
                variant=variant,
                intent=intent,
                policy=policy,
                relevant_bundles=relevant,
                limits=limits,
                expires_at=expires_at,
            )
            constructed.extend(rows)
            for key, field in (
                ("prices", "prices"),
                ("deliveries", "deliveries"),
                ("warranties", "warranties"),
                ("bundles", "bundles"),
                ("returns", "returns"),
            ):
                dim_acc[key] = max(dim_acc[key], dims[field])
        combination_generation_ms = (time.perf_counter() - gen_started) * 1000

        filter_started = time.perf_counter()
        feasible = [
            item
            for item in constructed
            if item.feasibility_status == FeasibilityStatus.FEASIBLE
        ]
        rejected = [
            item
            for item in constructed
            if item.feasibility_status == FeasibilityStatus.REJECTED
        ]
        distribution: Counter[str] = Counter()
        for item in rejected:
            if item.rejection_reasons:
                distribution[item.rejection_reasons[0].code.value] += 1
        feasibility_filter_ms = (time.perf_counter() - filter_started) * 1000

        persist_started = time.perf_counter()
        timing = OfferTiming(
            matching_load_ms=round(matching_load_ms, 2),
            dimension_load_ms=round(dimension_load_ms, 2),
            combination_generation_ms=round(combination_generation_ms, 2),
            feasibility_filter_ms=round(feasibility_filter_ms, 2),
            persistence_ms=0,
            total_ms=0,
        )
        dimensions = OfferDimensions(
            price_options=dim_acc["prices"],
            delivery_options=dim_acc["deliveries"],
            warranty_options=dim_acc["warranties"],
            bundle_options=dim_acc["bundles"],
            return_options=dim_acc["returns"],
        )
        summary = OfferSummary(
            estimated_candidates=estimated,
            generated_candidates=len(constructed),
            feasible_candidates=len(feasible),
            rejected_candidates=len(rejected),
            pruning_reason=pruning_reason,
            rejection_distribution=dict(distribution),
        )
        run = await self._persist(
            resolved_match_id,
            intent,
            intent_text or intent.raw_text,
            constructed,
            summary,
            dimensions,
            timing,
            len(variants),
        )
        timing.persistence_ms = round((time.perf_counter() - persist_started) * 1000, 2)
        timing.total_ms = round((time.perf_counter() - started) * 1000, 2)
        run.timing = timing.model_dump()
        await self.session.commit()

        preview_src = constructed if preview_status == "ALL" else (
            feasible if preview_status == "FEASIBLE" else rejected
        )
        preview = preview_src[:preview_limit]
        logger.info(
            "offers_constructed run_id=%s products=%s generated=%s feasible=%s "
            "rejected=%s total_ms=%.2f",
            run.id,
            len(variants),
            summary.generated_candidates,
            summary.feasible_candidates,
            summary.rejected_candidates,
            timing.total_ms,
        )
        return GenerateOffersResponse(
            offer_run_id=run.id,
            match_run_id=resolved_match_id,
            intent=intent,
            input={"matched_products": len(variants)},
            summary=summary,
            dimensions=dimensions,
            timing=timing,
            offers=[to_public(item) for item in preview],
            truncated=len(preview_src) > preview_limit,
        )

    async def get_run(
        self,
        run_id: uuid.UUID,
        *,
        product_id: uuid.UUID | None = None,
        delivery_code: str | None = None,
        warranty_code: str | None = None,
        bundle_code: str | None = None,
        return_policy_code: str | None = None,
        max_price_cents: int | None = None,
        status: str = "FEASIBLE",
        limit: int = 50,
        offset: int = 0,
    ) -> OfferRunResponse | None:
        run = await self.offers.get_run(run_id)
        if run is None:
            return None
        rows, total = await self.offers.list_offers(
            run_id,
            product_id=product_id,
            delivery_code=delivery_code,
            warranty_code=warranty_code,
            bundle_code=bundle_code,
            return_policy_code=return_policy_code,
            max_price_cents=max_price_cents,
            status=status,
            limit=limit,
            offset=offset,
        )
        return OfferRunResponse(
            offer_run_id=run.id,
            match_run_id=run.match_run_id,
            intent=ShoppingIntent.model_validate(run.parsed_intent),
            summary=OfferSummary(
                estimated_candidates=run.estimated_candidates,
                generated_candidates=run.generated_offer_count,
                feasible_candidates=run.feasible_offer_count,
                rejected_candidates=run.rejected_offer_count,
                pruning_reason=run.pruning_reason,
                rejection_distribution=run.rejection_distribution,
            ),
            dimensions=OfferDimensions.model_validate(run.dimensions),
            timing=run.timing,
            created_at=run.created_at,
            completed_at=run.completed_at,
            offers=[
                to_public(OfferCandidate.model_validate(row.payload)) for row in rows
            ],
            total_offers=total,
            limit=limit,
            offset=offset,
        )

    async def get_offer(self, offer_id: uuid.UUID) -> OfferDetailResponse | None:
        row = await self.offers.get_offer(offer_id)
        if row is None:
            return None
        candidate = OfferCandidate.model_validate(row.payload)
        return OfferDetailResponse(offer=candidate, public=to_public(candidate))

    async def _load_matches(
        self,
        intent_text: str | None,
        match_run_id: uuid.UUID | None,
        parser_mode: str | None,
        max_products: int,
    ) -> tuple[list[RankedProductMatch], ShoppingIntent, uuid.UUID | None]:
        if match_run_id is not None:
            run = await self.matching.get_run(match_run_id)
            if run is None:
                raise ValueError("Match run not found.")
            return run.semantic_matching.matches[:max_products], run.intent, run.run_id
        if not intent_text:
            raise ValueError("intent or match_run_id is required.")
        matched = await self.matching.match(
            intent_text, parser_mode, limit=max_products
        )
        return (
            matched.semantic_matching.matches,
            matched.intent,
            matched.run_id,
        )

    async def _persist(
        self,
        match_run_id: uuid.UUID | None,
        intent: ShoppingIntent,
        raw_text: str,
        constructed: list[OfferCandidate],
        summary: OfferSummary,
        dimensions: OfferDimensions,
        timing: OfferTiming,
        product_count: int,
    ) -> OfferConstructionRun:
        run = OfferConstructionRun(
            match_run_id=match_run_id,
            raw_intent=raw_text,
            parsed_intent=intent.model_dump(mode="json"),
            construction_version=CONSTRUCTION_VERSION,
            top_product_count=product_count,
            estimated_candidates=summary.estimated_candidates,
            generated_offer_count=summary.generated_candidates,
            feasible_offer_count=summary.feasible_candidates,
            rejected_offer_count=summary.rejected_candidates,
            pruning_reason=summary.pruning_reason,
            dimensions=dimensions.model_dump(),
            rejection_distribution=summary.rejection_distribution,
            timing=timing.model_dump(),
            construction_metadata={"version": CONSTRUCTION_VERSION},
            completed_at=datetime.now(UTC),
        )
        for item in constructed:
            item.offer_run_id = run.id
            run.offers.append(
                OfferCandidateRow(
                    id=item.id,
                    product_id=item.product_id,
                    variant_id=item.variant_id,
                    sku=item.sku,
                    product_name=item.product_name,
                    brand=item.brand,
                    construction_status=item.construction_status.value,
                    feasibility_status=item.feasibility_status.value,
                    delivery_code=item.delivery_code,
                    warranty_code=item.warranty_code,
                    bundle_code=item.bundle_code,
                    return_policy_code=item.return_policy_code,
                    final_product_price_cents=item.final_product_price_cents,
                    total_customer_price_cents=item.total_customer_price_cents,
                    direct_intervention_cost_cents=item.direct_intervention_cost_cents,
                    expires_at=item.expires_at,
                    rejection_reasons=[
                        reason.model_dump(mode="json")
                        for reason in item.rejection_reasons
                    ],
                    payload=item.model_dump(mode="json"),
                )
            )
        await self.offers.add_run(run)
        return run
