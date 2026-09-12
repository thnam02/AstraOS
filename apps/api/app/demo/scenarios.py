"""Structured hackathon demo scenarios. Expected behaviour is qualitative."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BuyerProfile = Literal[
    "INTENT_ADAPTED",
    "BALANCED",
    "URGENT_TRAVELLER",
    "BUDGET_SHOPPER",
    "ASSURANCE_BUYER",
    "QUALITY_FIRST",
]


@dataclass(frozen=True)
class DemoScenario:
    id: str
    title: str
    buyer_intent: str
    buyer_profile: BuyerProfile
    scripted_counter: str | None
    expected_behavior: str


HERO_TRAVEL = DemoScenario(
    id="HERO_TRAVEL",
    title="Urgent long-haul traveller",
    buyer_intent=(
        "I'm flying from Sydney to Singapore tomorrow and need wireless "
        "noise-cancelling headphones under A$350. I need them delivered today. "
        "I'll wear them for hours, so comfort and reliability matter more than "
        "getting the absolute cheapest option."
    ),
    buyer_profile="INTENT_ADAPTED",
    scripted_counter="Can you get this below A$315?",
    expected_behavior=(
        "Hard constraints keep same-day ANC under A$350. Optimisation prefers "
        "fulfilment/warranty over reflexive discount when that is more efficient. "
        "A policy-safe counter or alternative is returned. "
        "Exact winner is not hardcoded."
    ),
)

BUDGET_BUYER = DemoScenario(
    id="BUDGET_BUYER",
    title="Budget shopper",
    buyer_intent=(
        "Cheapest wireless ANC headphones under A$200 delivered in two days."
    ),
    buyer_profile="BUDGET_SHOPPER",
    scripted_counter="Any cheaper option?",
    expected_behavior="Price-sensitive ranking among policy-safe offers.",
)

ASSURANCE_BUYER = DemoScenario(
    id="ASSURANCE_BUYER",
    title="Assurance-sensitive buyer",
    buyer_intent=(
        "Wireless ANC headphones under A$400 with a long warranty. "
        "Reliability matters more than getting them today."
    ),
    buyer_profile="ASSURANCE_BUYER",
    scripted_counter=None,
    expected_behavior="Warranty and returns levers matter more than same-day.",
)

OUT_OF_STOCK_FAILURE = DemoScenario(
    id="OUT_OF_STOCK_FAILURE",
    title="Stale proposal after stock drop",
    buyer_intent=HERO_TRAVEL.buyer_intent,
    buyer_profile="INTENT_ADAPTED",
    scripted_counter=None,
    expected_behavior=(
        "After inventory is set to 0, acceptance revalidation fails and no order "
        "is created."
    ),
)

POLICY_CHANGE_FAILURE = DemoScenario(
    id="POLICY_CHANGE_FAILURE",
    title="Margin floor raised after proposal",
    buyer_intent=HERO_TRAVEL.buyer_intent,
    buyer_profile="INTENT_ADAPTED",
    scripted_counter=None,
    expected_behavior=(
        "Raising minimum margin to 25% after proposal makes acceptance fail "
        "if the locked offer is no longer policy-safe."
    ),
)

SCENARIOS = {
    item.id: item
    for item in (
        HERO_TRAVEL,
        BUDGET_BUYER,
        ASSURANCE_BUYER,
        OUT_OF_STOCK_FAILURE,
        POLICY_CHANGE_FAILURE,
    )
}


def get_scenario(scenario_id: str) -> DemoScenario:
    try:
        return SCENARIOS[scenario_id]
    except KeyError as exc:
        raise KeyError(f"Unknown demo scenario: {scenario_id}") from exc
