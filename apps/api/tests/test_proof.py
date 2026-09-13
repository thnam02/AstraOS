"""Targeted Phase 7 proof / provenance tests. No ranking or economics changes."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.decision.eligibility.snapshot import EvidenceSnapshot, InventorySnapshot
from app.decision.proof.compiler import compile_match_proof, compile_offer_proof
from app.decision.proof.coverage import coverage_of
from app.decision.proof.derived import LIGHTWEIGHT_RULE, derive_lightweight
from app.decision.proof.freshness import freshness_of
from app.decision.proof.models import ProofItem, public_verification
from app.decision.proof.resolver import resolve_attribute
from app.decision.retrieval.models import MatchFact, MatchReason, RankedProductMatch
from tests.qualification_fixtures import evidence, snapshot

NOW = datetime.now(UTC)


def _match(sku: str, *facts: MatchFact) -> RankedProductMatch:
    return RankedProductMatch(
        product_id=uuid4(),
        variant_id=uuid4(),
        sku=sku,
        product_name="Cabin",
        brand="Harbor",
        base_price_cents=27900,
        rank=1,
        semantic_similarity=0.8,
        product_fit=0.8,
        context_fit=0.8,
        preference_fit=0.8,
        evidence_coverage=0.1,
        overall_semantic_fit=0.8,
        matched_needs=["battery"],
        unsupported_needs=[],
        reasons=[MatchReason(need="battery", kind="context", facts=list(facts))],
        evidence=list(facts),
    )


def _row(
    attribute: str,
    value: object,
    *,
    source_type: str = "MERCHANT_PRODUCT_FEED",
    stale: bool = False,
    sku: str = "HS-CAB-12-BLK",
) -> EvidenceSnapshot:
    expires = NOW - timedelta(days=10) if stale else NOW + timedelta(days=180)
    return EvidenceSnapshot(
        id=str(uuid4()),
        attribute_name=attribute,
        value=value,
        source_name="Harbor product feed",
        source_type=source_type,
        source_reference=f"{sku}:{attribute}",
        verification_status="MERCHANT_DECLARED",
        observed_at=NOW - timedelta(days=1),
        expires_at=expires,
    )


def test_merchant_declared_is_verified() -> None:
    assert public_verification("MERCHANT_DECLARED") == "VERIFIED"
    assert public_verification("CONFLICTED") == "CONFLICTED"
    assert public_verification(None) == "UNKNOWN"


def test_conflicting_same_rank_is_conflicted() -> None:
    variant = snapshot(
        sku="HS-A",
        evidence=[
            _row("battery_hours", 79, sku="HS-A"),
            _row("battery_hours", 55, sku="HS-A"),
        ],
    )
    row, status = resolve_attribute(variant, "battery_hours")
    assert row is not None
    assert status == "CONFLICTED"
    match = _match(
        "HS-A",
        MatchFact(attribute="battery_hours", value=79, display="79h battery"),
    )
    bundle = compile_match_proof(variant, match)
    assert all(item.claim_key != "battery_hours" for item in bundle.items)


def test_precedence_resolves_inventory_over_feed() -> None:
    variant = snapshot(
        sku="HS-A",
        evidence=[
            _row("units_available", 2, sku="HS-A"),
            _row(
                "units_available",
                99,
                source_type="MERCHANT_INVENTORY",
                sku="HS-A",
            ),
        ],
    )
    row, status = resolve_attribute(variant, "units_available")
    assert status == "VERIFIED"
    assert row is not None
    assert row.value == 99


def test_stale_inventory_is_not_current() -> None:
    row = _row(
        "units_available",
        4,
        source_type="MERCHANT_INVENTORY",
        stale=True,
    )
    assert freshness_of(row, attribute="units_available") == "STALE"


def test_cross_product_evidence_is_isolated() -> None:
    a = snapshot(
        sku="HS-A",
        evidence=[_row("anc", True, sku="HS-A")],
    )
    b = snapshot(
        sku="HS-B",
        evidence=[_row("anc", False, sku="HS-B")],
    )
    match = _match("HS-A", MatchFact(attribute="anc", value=True, display="ANC"))
    bundle = compile_match_proof(a, match)
    assert bundle.items[0].sku == "HS-A"
    assert bundle.items[0].value is True
    other = compile_match_proof(
        b, _match("HS-B", MatchFact(attribute="anc", value=False, display="No ANC"))
    )
    assert other.items[0].sku == "HS-B"
    assert other.items[0].value is False


def test_lightweight_derivation_is_documented() -> None:
    variant = snapshot(attributes={"weight_g": "230 grams"})
    derived = derive_lightweight(variant)
    assert derived is not None
    assert derived["derivation_rule"] == LIGHTWEIGHT_RULE
    assert derived["derived"] is True


def test_offer_proof_covers_commercial_terms_without_private_keys() -> None:
    variant = snapshot(
        sku="HS-A",
        evidence=[
            _row("base_price_cents", 27900, source_type="PRICING_FEED", sku="HS-A"),
            _row(
                "units_available",
                8,
                source_type="MERCHANT_INVENTORY",
                sku="HS-A",
            ),
        ],
        inventory=InventorySnapshot(8, 0, updated_at=NOW),
    )
    offer = {
        "pricing": {"total_price_cents": 30185, "product_price_cents": 27900},
        "delivery": {"code": "SAME_DAY", "name": "Same day", "days": 0},
        "warranty": {"code": "W36", "name": "36 month", "months": 36},
        "bundle": {"code": "HARD_CASE", "name": "Hard case"},
        "returns": {"code": "R30", "name": "30 day", "window_days": 30},
        "contribution_margin_cents": 4400,
        "cogs_cents": 14000,
    }
    bundle = compile_offer_proof(variant, offer)
    keys = {item.claim_key for item in bundle.items}
    required = {
        "price",
        "delivery",
        "warranty",
        "bundle",
        "returns",
        "same_day_delivery",
    }
    assert required <= keys
    blob = str([item.model_dump() for item in bundle.items]).lower()
    assert "cogs" not in blob
    assert "contribution" not in blob
    assert "buyer_weight" not in blob
    commercial = [
        item
        for item in bundle.items
        if item.group in {"PRICE", "DELIVERY", "WARRANTY", "BUNDLE", "RETURNS"}
    ]
    assert commercial
    assert all(item.evidence_id or item.derived for item in commercial)
    assert bundle.coverage.commercial_term_proof_rate == 1.0
    assert bundle.coverage.unsupported_displayed_claim_rate == 0.0


def test_displayed_coverage_is_not_ranking_coverage() -> None:
    items = [
        ProofItem(
            claim_key="anc",
            display_claim="ANC",
            value=True,
            source_type="MERCHANT_PRODUCT_FEED",
            verification_status="VERIFIED",
            freshness_status="CURRENT",
            evidence_id="e1",
        )
    ]
    coverage = coverage_of(items)
    assert coverage.displayed_claim_count == 1
    assert coverage.match_rationale_proof_rate == 1.0
    ranking_coverage = 0.1
    assert coverage.match_rationale_proof_rate != ranking_coverage


def test_seed_fixture_evidence_helper_still_constructs() -> None:
    row = evidence("anc", True)
    assert row.source_type == "MANUFACTURER"
