from buyer_agent.models import (
    BuyerDecision,
    BuyerHardRequirements,
    BuyerMission,
    PublicProposal,
)
from buyer_agent.validator import BuyerPolicyValidator


def _mission() -> BuyerMission:
    return BuyerMission(
        mission_id="t",
        request="under A$200 today",
        hard=BuyerHardRequirements(
            max_total_cents=20000,
            same_day_required=True,
            require_anc=True,
        ),
        max_turns=3,
    )


def test_over_budget_blocks_accept() -> None:
    proposal = PublicProposal(
        total_cents=25000,
        delivery_days=0,
        proof=[
            {"claim": "anc", "value": True},
            {"claim": "same_day_delivery", "value": True},
        ],
    )
    gated, notes = BuyerPolicyValidator().gate(
        BuyerDecision(action="ACCEPT", reason_summary="looks nice"),
        _mission(),
        proposal,
    )
    assert "over_budget" in notes
    assert gated.action == "COUNTER"
    assert gated.counter and gated.counter.max_total_price_cents == 20000


def test_expired_rejects() -> None:
    proposal = PublicProposal(
        total_cents=10000,
        delivery_days=0,
        expiry="2000-01-01T00:00:00+00:00",
        proof=[
            {"claim": "anc", "value": True},
            {"claim": "same_day_delivery", "value": True},
        ],
    )
    gated, notes = BuyerPolicyValidator().gate(
        BuyerDecision(action="ACCEPT", reason_summary="ok"),
        _mission(),
        proposal,
    )
    assert "expired" in notes
    assert gated.action == "REJECT"
