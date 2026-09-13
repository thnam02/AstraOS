"""Optional live LLM buyer. Not part of default CI."""

from __future__ import annotations

import os

import pytest
from buyer_agent.config import BuyerAgentSettings
from buyer_agent.llm_buyer import LLMBuyer
from buyer_agent.llm_client import BuyerLLMClient
from buyer_agent.missions import get_mission
from buyer_agent.models import PublicProposal

pytestmark = pytest.mark.buyer_agent_llm


def _available() -> bool:
    settings = BuyerAgentSettings()
    flagged = os.environ.get("BUYER_AGENT_LLM_INTEGRATION") == "1"
    return bool(flagged and settings.api_key)


@pytest.mark.skipif(not _available(), reason="buyer LLM credentials not configured")
def test_live_llm_returns_structured_action() -> None:
    settings = BuyerAgentSettings()
    buyer = LLMBuyer(
        BuyerLLMClient(
            api_key=settings.api_key,
            model=settings.buyer_agent_model,
            base_url=settings.buyer_agent_llm_base_url,
            timeout_seconds=settings.buyer_agent_timeout,
        )
    )
    mission = get_mission("urgent-traveller")
    proposal = PublicProposal(
        total_cents=30185,
        delivery_days=0,
        warranty_months=36,
        product_name="Demo Cabin",
        proof=[{"claim": "same_day_delivery", "value": True}],
    )
    decision = buyer.decide(
        mission,
        proposal,
        capabilities={"operations": ["request_offer", "counter_offer", "accept_offer"]},
        history=[],
        turns_used=0,
    )
    assert decision.action in {"ACCEPT", "REJECT", "COUNTER", "INSPECT"}
    assert decision.reason_summary
