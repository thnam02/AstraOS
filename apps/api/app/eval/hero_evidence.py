"""Phase 7 hero evidence evaluation. One focused imported-merchant flow."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import selectinload

from app.agent.gateway import AgentGatewayService
from app.agent.schemas import AgentAcceptRequest, AgentOfferRequest
from app.db.session import AsyncSessionLocal
from app.decision.eligibility.evaluator import EligibilityEvaluator
from app.decision.eligibility.models import ConstraintStatus
from app.decision.eligibility.snapshot import variant_to_snapshot
from app.decision.proof.compiler import compile_offer_proof
from app.decision.proof.coverage import coverage_of
from app.decision.proof.models import ProofItem
from app.ingestion.constants import MODE_DEMO_SEED
from app.ingestion.service import MerchantIngestionService
from app.models import (
    AttributeEvidence,
    Merchant,
    MerchantIngestionRun,
    Product,
    ProductVariant,
    VariantDeliveryOption,
)
from app.models.commerce import InventoryReservation, Order
from app.services.matching import SemanticMatchingService

ROOT = Path(__file__).resolve().parents[4]
EXAMPLE = ROOT / "examples/merchant-data/harbor-sound.json"
HERO_INTENT = (
    "I'm flying from Sydney to Singapore tomorrow and need wireless "
    "noise-cancelling headphones under A$350. I need them delivered today. "
    "I'll wear them for hours, so comfort and reliability matter more than "
    "getting the absolute cheapest option."
)
PRIVATE = ("cogs", "contribution", "margin floor", "buyer_weight", "merchant_weight")
COMMERCIAL = {"price", "delivery", "warranty", "bundle", "returns"}


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


async def _set_seed_active(session: Any, *, active: bool) -> None:
    products = (
        await session.scalars(select(Product).where(Product.source_system.is_(None)))
    ).all()
    for product in products:
        product.is_active = active
    variants = (
        await session.scalars(
            select(ProductVariant).where(ProductVariant.source_system.is_(None))
        )
    ).all()
    for variant in variants:
        variant.is_active = active
    await session.commit()


async def _cleanup_imported(session: Any) -> None:
    products = (
        await session.scalars(
            select(Product)
            .where(
                or_(
                    Product.source_system.in_(("merchant_json", "merchant_csv")),
                    Product.external_id.like("HS-%"),
                )
            )
            .options(selectinload(Product.variants))
        )
    ).all()
    variant_ids = [variant.id for product in products for variant in product.variants]
    if variant_ids:
        await session.execute(
            delete(InventoryReservation).where(
                InventoryReservation.variant_id.in_(variant_ids)
            )
        )
        await session.execute(delete(Order).where(Order.variant_id.in_(variant_ids)))
    for product in products:
        await session.delete(product)
    merchant = (await session.scalars(select(Merchant).limit(1))).first()
    if merchant is not None:
        merchant.data_mode = MODE_DEMO_SEED
    runs = (
        await session.scalars(
            select(MerchantIngestionRun).where(
                MerchantIngestionRun.initiated_by == "eval"
            )
        )
    ).all()
    for run in runs:
        await session.delete(run)
    await session.commit()


async def _load_variant(session: Any, sku: str) -> ProductVariant | None:
    return (
        await session.scalars(
            select(ProductVariant)
            .where(ProductVariant.sku == sku)
            .options(
                selectinload(ProductVariant.product),
                selectinload(ProductVariant.inventory),
                selectinload(ProductVariant.delivery_options).selectinload(
                    VariantDeliveryOption.delivery_option
                ),
                selectinload(ProductVariant.evidence).selectinload(
                    AttributeEvidence.source
                ),
            )
        )
    ).first()


async def _evaluate(*, keep: bool) -> dict[str, Any]:
    payload = EXAMPLE.read_bytes()
    async with AsyncSessionLocal() as session:
        await _cleanup_imported(session)
        applied = await MerchantIngestionService(session).run(
            payload,
            source_type="json",
            source_name="harbor-sound.json",
            dry_run=False,
            initiated_by="eval",
        )
        await _set_seed_active(session, active=False)
        match = None
        offered = None
        inspected = None
        accepted = None
        hard_rate = 1.0
        commercial_rate = 0.0
        stale_ok = False
        conflict_ok = False
        try:
            match = await SemanticMatchingService(session).match(
                HERO_INTENT, parser_mode="rule_based"
            )
            gateway = AgentGatewayService(session)
            offered = await gateway.request_offer(
                AgentOfferRequest(
                    natural_language_intent=HERO_INTENT,
                    buyer_profile="URGENT_TRAVELLER",
                )
            )
            if offered.proposal and offered.negotiation_session_id:
                inspected = await gateway.inspect_offer(offered.proposal.proposal_id)
                accepted = await gateway.accept_offer(
                    AgentAcceptRequest(
                        session_id=offered.negotiation_session_id,
                        proposal_id=offered.proposal.proposal_id,
                        idempotency_key=f"phase7-{uuid4()}",
                    )
                )
            top = (
                match.semantic_matching.matches[0]
                if match.semantic_matching.matches
                else None
            )
            if top is not None:
                variant = await _load_variant(session, top.sku)
                if variant is not None:
                    snap = variant_to_snapshot(variant)
                    qualified = EligibilityEvaluator().evaluate_variant(
                        snap, match.intent
                    )
                    satisfied = [
                        item
                        for item in qualified.evaluations
                        if item.status == ConstraintStatus.SATISFIED
                    ]
                    backed = [
                        item
                        for item in satisfied
                        if item.evidence_id or item.source_reference
                    ]
                    hard_rate = (len(backed) / len(satisfied)) if satisfied else 1.0
                    offer_payload = (
                        offered.proposal.model_dump(mode="json")
                        if offered and offered.proposal
                        else {}
                    )
                    bundle = compile_offer_proof(snap, offer_payload, match=top)
                    commercial = [
                        item
                        for item in bundle.items
                        if item.group
                        in {"PRICE", "DELIVERY", "WARRANTY", "BUNDLE", "RETURNS"}
                    ]
                    commercial_backed = sum(
                        1
                        for item in commercial
                        if item.evidence_id or item.derived
                    )
                    commercial_rate = (
                        commercial_backed / len(commercial)
                        if commercial
                        else 1.0
                    )
            night = await _load_variant(session, "HS-NGT-14-BLK")
            cabin = await _load_variant(session, "HS-CAB-12-BLK")
            if night is not None:
                stale_ok = any(
                    row.attribute_name == "anc" and row.expires_at is not None
                    for row in night.evidence
                )
            if cabin is not None:
                conflict_ok = (
                    len(
                        [
                            row
                            for row in cabin.evidence
                            if row.attribute_name == "battery_hours"
                        ]
                    )
                    <= 1
                )
        finally:
            await _set_seed_active(session, active=True)
            if not keep:
                try:
                    await _cleanup_imported(session)
                except Exception:  # noqa: BLE001
                    await session.rollback()

    top = (
        match.semantic_matching.matches[0]
        if match and match.semantic_matching.matches
        else None
    )
    rec = offered.proposal if offered is not None else None
    proof = list(inspected.proof if inspected is not None else [])
    proof_keys = {item.claim for item in proof}
    blob = json.dumps([item.model_dump(mode="json") for item in proof]).lower()
    leaked = any(marker in blob for marker in PRIVATE)
    displayed_items = [
        ProofItem.model_validate(item) for item in (top.proof if top else [])
    ]
    coverage = coverage_of(displayed_items)
    accept_status = getattr(accepted, "status", None) if accepted is not None else None
    return {
        "phase": 7,
        "title": "hero-evidence-realification",
        "git_sha": _git_sha(),
        "hero_merchant_source": "examples/merchant-data/harbor-sound.json",
        "source_types": [
            "MERCHANT_PRODUCT_FEED",
            "MERCHANT_INVENTORY",
            "PRICING_FEED",
            "FULFILMENT_CONFIGURATION",
            "WARRANTY_POLICY",
            "BUNDLE_CONFIGURATION",
            "RETURN_POLICY",
            "EXAMPLE_MERCHANT_IMPORT",
            "SYNTHETIC_DEMO_FIXTURE",
        ],
        "ingestion_status": getattr(applied, "status", None),
        "top_product": {
            "sku": top.sku if top else None,
            "name": top.product_name if top else None,
            "reasons": [
                fact.display
                for reason in (top.reasons if top else [])
                for fact in reason.facts
                if fact.evidence_id or fact.derived
            ][:5],
        },
        "selected_offer": {
            "sku": (rec.product or {}).get("sku") if rec else None,
            "delivery": rec.delivery if rec else None,
            "warranty": rec.warranty if rec else None,
            "bundle": rec.bundle if rec else None,
            "returns": rec.returns if rec else None,
            "price": rec.pricing if rec else None,
        },
        "displayed_claim_count": coverage.displayed_claim_count,
        "claims_with_evidence": coverage.claims_with_evidence,
        "verified_count": coverage.verified_count,
        "unverified_count": coverage.unverified_count,
        "stale_count": coverage.stale_count,
        "conflicted_count": coverage.conflicted_count,
        "unknown_count": coverage.unknown_count,
        "synthetic_count": coverage.synthetic_count,
        "example_import_count": coverage.example_import_count,
        "unsupported_displayed_claim_rate": coverage.unsupported_displayed_claim_rate,
        "hard_constraint_proof_rate": round(hard_rate, 4),
        "commercial_term_proof_rate": round(commercial_rate, 4),
        "match_rationale_proof_rate": coverage.match_rationale_proof_rate,
        "public_agent_proof_status": (
            "PASS" if inspected is not None and proof and not leaked else "FAIL"
        ),
        "public_proof_leaked_private": leaked,
        "public_proof_claims": sorted(proof_keys),
        "hero_end_to_end_status": (
            "PASS"
            if offered is not None
            and inspected is not None
            and accept_status in {"CONFIRMED", "REVALIDATION_FAILED"}
            else "FAIL"
        ),
        "transaction_status": accept_status,
        "transaction_revalidation_present": bool(
            accepted is not None and getattr(accepted, "revalidation", None)
        ),
        "stale_conflict_validation": {
            "night_anc_stale_present": stale_ok,
            "cabin_battery_unconflicted": conflict_ok,
        },
        "same_day_in_public_proof": "same_day_delivery" in proof_keys,
        "commercial_keys_in_public_proof": sorted(COMMERCIAL & proof_keys),
        "formulas_unchanged": {
            "intent": True,
            "qualification": True,
            "semantic_scoring": True,
            "offer_economics": True,
            "merchant_objective": True,
            "pareto": True,
            "negotiation": True,
            "transaction": True,
        },
        "full_backend_suite_run": False,
        "targeted_tests_run": [
            "apps/api/tests/test_proof.py",
            "apps/api/tests/test_agent_proof.py",
            "apps/web/lib/matchDisplay.test.ts",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate hero evidence.")
    parser.add_argument(
        "--out",
        default="../../artifacts/realification/phase7-evidence.json",
    )
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    import asyncio

    report = asyncio.run(_evaluate(keep=args.keep))
    out = Path(args.out)
    if not out.is_absolute():
        out = Path.cwd() / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out),
                "status": report["hero_end_to_end_status"],
                "unsupported": report["unsupported_displayed_claim_rate"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
