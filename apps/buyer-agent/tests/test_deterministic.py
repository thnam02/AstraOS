from buyer_agent.deterministic import DeterministicBuyer
from buyer_agent.models import (
    BuyerHardRequirements,
    BuyerMission,
    BuyerProfile,
    PublicProposal,
)


def test_hard_violation_counters() -> None:
    mission = BuyerMission(
        mission_id="t",
        request="under 100",
        hard=BuyerHardRequirements(max_total_cents=10000, same_day_required=True),
        max_turns=2,
    )
    proposal = PublicProposal(total_cents=18000, delivery_days=2, session_id="s")
    decision = DeterministicBuyer().decide(
        mission, proposal, turns_used=0, inspected=True
    )
    assert decision.action == "COUNTER"
    assert decision.counter
    assert decision.counter.max_total_price_cents == 10000


def test_good_offer_accepts() -> None:
    mission = BuyerMission(
        mission_id="t",
        request="hero",
        profile=BuyerProfile(urgency="high", reliability="high"),
        hard=BuyerHardRequirements(max_total_cents=35000, same_day_required=True),
        acceptance_threshold=0.5,
        max_turns=3,
    )
    proposal = PublicProposal(
        total_cents=30185,
        delivery_days=0,
        warranty_months=36,
        session_id="s",
        proof=[{"claim": "same_day_delivery", "value": True}],
    )
    decision = DeterministicBuyer().decide(
        mission, proposal, turns_used=0, inspected=True
    )
    assert decision.action == "ACCEPT"


def test_max_turns_rejects() -> None:
    mission = BuyerMission(
        mission_id="t",
        request="x",
        hard=BuyerHardRequirements(max_total_cents=1000),
        max_turns=1,
    )
    proposal = PublicProposal(total_cents=9000, session_id="s")
    decision = DeterministicBuyer().decide(
        mission, proposal, turns_used=1, inspected=True
    )
    assert decision.action == "REJECT"
