"""Build one shared ArenaContext. Strategies must not rebuild this."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.decision.arena.models import ArenaContext, BuyerMission
from app.decision.eligibility.evaluator import EligibilityEvaluator
from app.decision.eligibility.snapshot import variant_to_snapshot
from app.decision.intent.parser import parse_intent
from app.decision.offers.bundles import relevant_bundle_codes
from app.decision.offers.constructor import construct_variant
from app.decision.offers.feasibility import sellable_units
from app.decision.offers.models import (
    ConstructionLimits,
    FeasibilityStatus,
    OfferCandidate,
)
from app.decision.optimisation.engine import score_space
from app.decision.retrieval.embeddings import default_embedding_provider
from app.decision.retrieval.matcher import rank_eligible
from app.decision.utility.scorer import weights_for
from app.models import MerchantPolicy, ProductVariant
from app.repositories.policy import MerchantPolicyRepository
from app.services.matching import SemanticMatchingService


class ArenaCatalogueCache:
    """Catalogue snapshot shared across missions. Never mutated by strategies."""

    def __init__(self) -> None:
        self.variants: list[ProductVariant] = []
        self.by_id: dict[UUID, ProductVariant] = {}
        self.policy: MerchantPolicy | None = None
        self.embeddings: dict[UUID, list[float]] = {}
        self.inventory_fingerprint: str = ""
        self.loaded = False

    async def load(self, session: AsyncSession) -> None:
        if self.loaded:
            return
        matching = SemanticMatchingService(session)
        variants = list(await matching.products.list_active_variants())
        policy = await MerchantPolicyRepository(session).get_active()
        if policy is None:
            raise RuntimeError("No active merchant policy.")
        snapshots = [variant_to_snapshot(row) for row in variants]
        embeddings = await matching._ensure_embeddings(snapshots)
        fingerprint = "|".join(
            f"{row.sku}:{sellable_units(row)}"
            for row in sorted(variants, key=lambda item: item.sku)
        )
        self.variants = variants
        self.by_id = {row.id: row for row in variants}
        self.policy = policy
        self.embeddings = embeddings
        self.inventory_fingerprint = fingerprint
        self.loaded = True


class ArenaContextBuilder:
    def __init__(
        self,
        session: AsyncSession,
        cache: ArenaCatalogueCache | None = None,
    ) -> None:
        self.session = session
        self.cache = cache or ArenaCatalogueCache()
        self.evaluator = EligibilityEvaluator()
        self.provider = default_embedding_provider()

    async def build(
        self,
        mission: BuyerMission,
        *,
        max_products: int = 8,
    ) -> ArenaContext:
        await self.cache.load(self.session)
        policy = self.cache.policy
        assert policy is not None
        intent = await parse_intent(mission.raw_intent, "rule_based")
        snapshots = [variant_to_snapshot(row) for row in self.cache.variants]
        results = [
            self.evaluator.evaluate_variant(snapshot, intent) for snapshot in snapshots
        ]
        eligible_ids = {row.variant_id for row in results if row.outcome == "eligible"}
        eligible_snaps = [
            item for item in snapshots if item.variant_id in eligible_ids
        ]
        ranked = rank_eligible(
            intent, eligible_snaps, self.cache.embeddings, self.provider
        )
        top = ranked[:max_products]
        selected = [
            self.cache.by_id[item.variant_id]
            for item in top
            if item.variant_id in self.cache.by_id
        ]
        relevant = relevant_bundle_codes(intent)
        limits = ConstructionLimits(max_products=max_products)
        expires_at = datetime.now(UTC) + timedelta(seconds=settings.offer_ttl_seconds)
        offers = []
        for variant in selected:
            constructed, _counts = construct_variant(
                variant=variant,
                intent=intent,
                policy=policy,
                relevant_bundles=relevant,
                limits=limits,
                expires_at=expires_at,
            )
            offers.extend(constructed)
        for offer in offers:
            offer.id = _stable_offer_id(mission.id, offer)
        product_fits = {
            item.variant_id: item.overall_semantic_fit for item in top
        }
        engine = score_space(
            offers,
            intent=intent,
            policy=policy,
            variants=self.cache.by_id,
            product_fits=product_fits,
            profile_id=mission.buyer_profile,
        )
        feasible = sum(
            1
            for item in offers
            if item.feasibility_status == FeasibilityStatus.FEASIBLE
        )
        safe = sum(1 for item in engine.scored if item.policy.policy_safe)
        return ArenaContext(
            mission=mission,
            intent=intent,
            buyer_profile=mission.buyer_profile,
            weights=weights_for(intent, mission.buyer_profile),
            matches=top,
            offers=offers,
            scored=engine.scored,
            eligible_count=len(eligible_ids),
            policy_id=policy.id,
            policy_margin=float(policy.minimum_margin_rate),
            policy_max_discount=float(policy.maximum_discount_rate),
            catalogue_variant_count=len(self.cache.variants),
            construction_count=len(offers),
            feasible_count=feasible,
            policy_safe_count=safe,
            inventory_fingerprint=self.cache.inventory_fingerprint,
            recommended_offer_id=(
                engine.recommended.offer_id if engine.recommended else None
            ),
            optimisation_failure=(
                engine.failure.message if engine.failure else None
            ),
        )


def max_allowed_discount(context: ArenaContext) -> Decimal:
    return Decimal(str(context.policy_max_discount))


def _stable_offer_id(mission_id: str, offer: OfferCandidate) -> UUID:
    key = "|".join(
        [
            mission_id,
            offer.sku,
            offer.price_adjustment_type,
            str(offer.price_adjustment_rate),
            offer.delivery_code,
            offer.warranty_code,
            offer.bundle_code or "NONE",
            offer.return_policy_code or "NONE",
        ]
    )
    return uuid5(NAMESPACE_URL, f"astraos.arena.offer.{key}")
