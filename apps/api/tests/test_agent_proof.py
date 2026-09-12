"""Public Buyer Agent proof contract. No merchant-private economics."""

from datetime import UTC, datetime

from app.agent.proof import claims_from_bundle, merge_claims, proof_items_to_claims
from app.agent.schemas import EvidenceClaim
from app.decision.proof.compiler import attach_proof_bundle
from app.decision.proof.models import ProofItem


def test_public_proof_omits_private_economics() -> None:
    items = [
        ProofItem(
            claim_key="price",
            display_claim="A$279.00",
            value=27900,
            source_type="PRICING_FEED",
            verification_status="VERIFIED",
            freshness_status="CURRENT",
            derived=True,
            derivation_rule="variant_list_price_v1",
            group="PRICE",
        ),
        ProofItem(
            claim_key="cogs_cents",
            display_claim="hidden",
            value=14000,
            source_type="PRICING_FEED",
            verification_status="VERIFIED",
            freshness_status="CURRENT",
            group="PRICE",
        ),
        ProofItem(
            claim_key="contribution",
            display_claim="hidden",
            value=44,
            source_type="INTERNAL",
            verification_status="VERIFIED",
            freshness_status="CURRENT",
            group="PRICE",
        ),
    ]
    claims = proof_items_to_claims(items)
    keys = {item.claim for item in claims}
    assert "price" in keys
    assert "cogs_cents" not in keys
    assert "contribution" not in keys


def test_proposal_proof_snapshot_does_not_mutate() -> None:
    offer = {
        "sku": "HS-CAB-12-BLK",
        "pricing": {"total_price_cents": 27900, "product_price_cents": 27900},
        "delivery": {"code": "SAME_DAY", "name": "Same day", "days": 0},
        "warranty": {"code": "W36", "name": "36 month", "months": 36},
        "bundle": {"code": "HARD_CASE", "name": "Hard case"},
        "returns": {"code": "R30", "window_days": 30},
    }
    first = attach_proof_bundle(dict(offer))
    snapshot = first["proof_bundle"]
    offer["delivery"] = {"code": "STANDARD", "name": "Standard", "days": 3}
    second = attach_proof_bundle(dict(offer))
    claims = {item["claim_key"] for item in snapshot["items"]}
    first_delivery = next(
        item
        for item in snapshot["items"]
        if item["claim_key"] == "same_day_delivery"
    )
    later_delivery = next(
        item
        for item in second["proof_bundle"]["items"]
        if item["claim_key"] == "delivery"
    )
    assert "same_day_delivery" in claims
    assert later_delivery["source_record_id"] == "STANDARD"
    assert first_delivery["source_record_id"] == "SAME_DAY"
    assert first_delivery["source_record_id"] != later_delivery["source_record_id"]


def test_inspect_bundle_round_trip_keeps_same_day() -> None:
    claims = claims_from_bundle(
        {
            "items": [
                {
                    "claim_key": "same_day_delivery",
                    "display_claim": "Same-day delivery",
                    "value": True,
                    "source_type": "FULFILMENT_CONFIGURATION",
                    "verification_status": "VERIFIED",
                    "freshness_status": "CURRENT",
                    "derived": True,
                    "derivation_rule": "selected_delivery_option_v1",
                    "group": "DELIVERY",
                }
            ],
            "issued_at": datetime.now(UTC).isoformat(),
        }
    )
    merged = merge_claims(claims, [])
    assert merged[0].claim == "same_day_delivery"
    assert merged[0].value is True
    assert isinstance(merged[0], EvidenceClaim)
