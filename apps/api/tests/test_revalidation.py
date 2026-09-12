"""Live revalidation of an immutable proposal."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.decision.offers.models import (
    ConstructionStatus,
    FeasibilityStatus,
    OfferCandidate,
)
from app.decision.transaction.models import TransactionFailureCode
from app.decision.transaction.revalidation import TransactionRevalidationService
from app.models.inventory import InventoryRecord
from app.models.negotiation import MerchantProposal, NegotiationSession


def _offer(**overrides: object) -> OfferCandidate:
    base = dict(
        id=uuid4(),
        product_id=uuid4(),
        variant_id=uuid4(),
        sku="AUR-T06-BLK",
        product_name="Aurora Commute 06",
        brand="Aurora",
        base_price_cents=32000,
        price_adjustment_cents=0,
        final_product_price_cents=32000,
        price_adjustment_type="LIST",
        price_adjustment_rate=0,
        delivery_code="SAME_DAY",
        delivery_name="Same day",
        delivery_days=0,
        delivery_customer_charge_cents=0,
        delivery_merchant_cost_cents=800,
        warranty_code="STANDARD_12",
        warranty_name="12 month",
        warranty_months=12,
        warranty_customer_price_cents=0,
        warranty_merchant_cost_cents=200,
        total_customer_price_cents=32000,
        direct_intervention_cost_cents=0,
        construction_status=ConstructionStatus.GENERATED,
        feasibility_status=FeasibilityStatus.FEASIBLE,
    )
    base.update(overrides)
    return OfferCandidate.model_validate(base)


def _session(proposal_id: object, **overrides: object) -> NegotiationSession:
    now = datetime.now(UTC)
    row = NegotiationSession(
        initial_intent_run_id=None,
        match_run_id=None,
        offer_run_id=None,
        optimisation_run_id=None,
        current_offer_id=None,
        current_proposal_id=proposal_id,  # type: ignore[arg-type]
        current_state="READY_FOR_CHECKOUT",
        buyer_agent_type="MANUAL",
        buyer_profile="INTENT_ADAPTED",
        merchant_policy_version="v1",
        original_intent={
            "raw_text": "x",
            "category": "headphones",
            "hard_constraints": [],
            "soft_preferences": [],
            "context_tags": [],
            "context_items": [],
            "desired_outcomes": [],
            "values": [],
            "tradeoffs": [],
            "unsupported_semantic_needs": [],
            "ambiguities": [],
            "parser_type": "rule_based",
            "parser_version": "1",
            "status": "READY",
        },
        working_intent={
            "raw_text": "x",
            "category": "headphones",
            "hard_constraints": [],
            "soft_preferences": [],
            "context_tags": [],
            "context_items": [],
            "desired_outcomes": [],
            "values": [],
            "tradeoffs": [],
            "unsupported_semantic_needs": [],
            "ambiguities": [],
            "parser_type": "rule_based",
            "parser_version": "1",
            "status": "READY",
        },
        delta_history=[],
        events=[],
        raw_intent="x",
        turn_count=1,
        max_turns=5,
        expires_at=now + timedelta(minutes=5),
        session_metadata={
            "policy_snapshot": {
                "minimum_margin_rate": "0.1500",
                "maximum_discount_rate": "0.1000",
            }
        },
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def _proposal(session_id: object, **overrides: object) -> MerchantProposal:
    now = datetime.now(UTC)
    row = MerchantProposal(
        session_id=session_id,  # type: ignore[arg-type]
        version=1,
        proposal_type="INITIAL",
        outcome="INITIAL",
        offer_id=uuid4(),
        offer_snapshot={},
        reason_codes=[],
        explanation=[],
        next_allowed_actions=["ACCEPT"],
        expires_at=now + timedelta(minutes=5),
        created_at=now,
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def _variant(*, available: int = 4, reserved: int = 0, active: bool = True):
    inventory = InventoryRecord(
        variant_id=uuid4(),
        units_available=available,
        units_reserved=reserved,
        warehouse_code="SYD",
    )
    product = SimpleNamespace(is_active=True)
    delivery = SimpleNamespace(
        available=True,
        delivery_option=SimpleNamespace(
            id=uuid4(), code="SAME_DAY", enabled=True
        ),
    )
    warranty = SimpleNamespace(
        available=True,
        warranty_option=SimpleNamespace(
            id=uuid4(), code="STANDARD_12", enabled=True
        ),
    )
    return SimpleNamespace(
        id=uuid4(),
        sku="AUR-T06-BLK",
        is_active=active,
        base_price_cents=32000,
        cogs_cents=25000,
        product=product,
        inventory=inventory,
        delivery_options=[delivery],
        warranty_options=[warranty],
        bundle_options=[],
        return_policies=[],
    )


def _policy(*, margin: str = "0.1500", discount: str = "0.1000"):
    from decimal import Decimal

    return SimpleNamespace(
        minimum_margin_rate=Decimal(margin),
        maximum_discount_rate=Decimal(discount),
        delivery_subsidy_enabled=True,
        warranty_upgrade_enabled=True,
        bundle_enabled=True,
        flexible_returns_enabled=True,
        maximum_delivery_subsidy_cents=None,
        maximum_warranty_subsidy_cents=None,
        maximum_bundle_subsidy_cents=None,
    )


def _pair() -> tuple[NegotiationSession, MerchantProposal]:
    session = _session(uuid4())
    proposal = _proposal(session.id)
    session.current_proposal_id = proposal.id
    return session, proposal


def _run(**kwargs: object):
    service = TransactionRevalidationService()
    proposal = kwargs.pop("proposal")
    session = kwargs.pop("session")
    return service.validate(
        session=session,  # type: ignore[arg-type]
        proposal=proposal,  # type: ignore[arg-type]
        variant=kwargs.get("variant"),  # type: ignore[arg-type]
        policy=kwargs.get("policy"),  # type: ignore[arg-type]
        offer=kwargs.get("offer"),  # type: ignore[arg-type]
        quantity=int(kwargs.get("quantity") or 1),
        honor_locked_price=kwargs.get("honor_locked_price"),  # type: ignore[arg-type]
        now=kwargs.get("now"),  # type: ignore[arg-type]
    )


def test_valid_proposal() -> None:
    offer = _offer()
    session, proposal = _pair()
    variant = _variant()
    variant.cogs_cents = 18000
    result = _run(
        session=session,
        proposal=proposal,
        variant=variant,
        policy=_policy(),
        offer=offer,
    )
    assert result.valid
    assert result.failure_codes == []


def test_expired_proposal() -> None:
    offer = _offer()
    session, proposal = _pair()
    proposal.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    result = _run(
        session=session,
        proposal=proposal,
        variant=_variant(),
        policy=_policy(),
        offer=offer,
    )
    assert not result.valid
    assert TransactionFailureCode.PROPOSAL_EXPIRED in result.failure_codes


def test_inactive_product() -> None:
    offer = _offer()
    session, proposal = _pair()
    variant = _variant()
    variant.product.is_active = False
    result = _run(
        session=session,
        proposal=proposal,
        variant=variant,
        policy=_policy(),
        offer=offer,
    )
    assert TransactionFailureCode.PRODUCT_INACTIVE in result.failure_codes


def test_price_changed_when_lock_disabled() -> None:
    offer = _offer(base_price_cents=32000)
    session, proposal = _pair()
    variant = _variant()
    variant.base_price_cents = 40000
    result = _run(
        session=session,
        proposal=proposal,
        variant=variant,
        policy=_policy(),
        offer=offer,
        honor_locked_price=False,
    )
    assert TransactionFailureCode.PRICE_CHANGED in result.failure_codes


def test_locked_price_honoured_until_expiry() -> None:
    offer = _offer(base_price_cents=32000)
    session, proposal = _pair()
    variant = _variant()
    variant.base_price_cents = 40000
    result = _run(
        session=session,
        proposal=proposal,
        variant=variant,
        policy=_policy(),
        offer=offer,
        honor_locked_price=True,
    )
    assert TransactionFailureCode.PRICE_CHANGED not in result.failure_codes


def test_out_of_stock() -> None:
    offer = _offer()
    session, proposal = _pair()
    result = _run(
        session=session,
        proposal=proposal,
        variant=_variant(available=0),
        policy=_policy(),
        offer=offer,
    )
    assert TransactionFailureCode.OUT_OF_STOCK in result.failure_codes


def test_delivery_unavailable() -> None:
    offer = _offer()
    session, proposal = _pair()
    variant = _variant()
    variant.delivery_options[0].available = False
    result = _run(
        session=session,
        proposal=proposal,
        variant=variant,
        policy=_policy(),
        offer=offer,
    )
    assert TransactionFailureCode.DELIVERY_NO_LONGER_AVAILABLE in result.failure_codes


def test_warranty_unavailable() -> None:
    offer = _offer()
    session, proposal = _pair()
    variant = _variant()
    variant.warranty_options[0].available = False
    result = _run(
        session=session,
        proposal=proposal,
        variant=variant,
        policy=_policy(),
        offer=offer,
    )
    assert TransactionFailureCode.WARRANTY_NO_LONGER_AVAILABLE in result.failure_codes


def test_bundle_unavailable() -> None:
    offer = _offer(bundle_code="HARD_CASE", bundle_option_id=uuid4())
    session, proposal = _pair()
    variant = _variant()
    result = _run(
        session=session,
        proposal=proposal,
        variant=variant,
        policy=_policy(),
        offer=offer,
    )
    assert TransactionFailureCode.BUNDLE_NO_LONGER_AVAILABLE in result.failure_codes


def test_return_policy_changed() -> None:
    offer = _offer(return_policy_code="FLEX_60", return_policy_id=uuid4())
    session, proposal = _pair()
    variant = _variant()
    result = _run(
        session=session,
        proposal=proposal,
        variant=variant,
        policy=_policy(),
        offer=offer,
    )
    assert TransactionFailureCode.RETURN_POLICY_CHANGED in result.failure_codes


def test_merchant_policy_changed() -> None:
    offer = _offer()
    session, proposal = _pair()
    result = _run(
        session=session,
        proposal=proposal,
        variant=_variant(),
        policy=_policy(margin="0.2500"),
        offer=offer,
    )
    assert TransactionFailureCode.MARGIN_POLICY_VIOLATION in result.failure_codes
    assert TransactionFailureCode.MERCHANT_POLICY_CHANGED in result.failure_codes
