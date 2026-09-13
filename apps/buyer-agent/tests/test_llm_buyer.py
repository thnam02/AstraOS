from buyer_agent.llm_buyer import LLMBuyer
from buyer_agent.models import BuyerHardRequirements, BuyerMission, PublicProposal


class _ValidLLM:
    def complete_json(self, *, system: str, user: str) -> dict[str, object]:
        assert "chain-of-thought" in system.lower() or "JSON only" in system
        return {
            "action": "COUNTER",
            "reason_summary": "Ask for a lower total.",
            "counter": {
                "max_total_price_cents": 29000,
                "message": "Can you get the total below A$290?",
            },
        }


def test_structured_counter() -> None:
    mission = BuyerMission(
        mission_id="t",
        request="under 350",
        hard=BuyerHardRequirements(max_total_cents=35000),
    )
    proposal = PublicProposal(total_cents=30185, delivery_days=0, session_id="s")
    decision = LLMBuyer(_ValidLLM()).decide(
        mission, proposal, capabilities={}, history=[], turns_used=0
    )
    assert decision.action == "COUNTER"
    assert decision.counter
    assert decision.counter.max_total_price_cents == 29000
