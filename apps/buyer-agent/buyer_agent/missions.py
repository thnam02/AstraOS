"""A few buyer personas. They change buyer behavior only."""

from __future__ import annotations

from buyer_agent.models import (
    BuyerHardRequirements,
    BuyerMission,
    BuyerProfile,
    Persona,
)

HERO_REQUEST = (
    "I'm flying from Sydney to Singapore tomorrow and need wireless "
    "noise-cancelling headphones under A$350. I need them delivered today. "
    "I'll wear them for hours, so comfort and reliability matter more than "
    "getting the absolute cheapest option."
)

_PERSONAS: dict[Persona, BuyerMission] = {
    "URGENT_TRAVELLER": BuyerMission(
        mission_id="urgent-traveller",
        request=HERO_REQUEST,
        persona="URGENT_TRAVELLER",
        profile=BuyerProfile(
            urgency="high",
            comfort="high",
            reliability="high",
            price_sensitivity="medium",
            quality="high",
        ),
        hard=BuyerHardRequirements(
            max_total_cents=35000,
            same_day_required=True,
            require_anc=True,
            require_wireless=True,
        ),
        acceptance_threshold=0.62,
        max_turns=4,
        negotiation_style="urgent",
    ),
    "BUDGET_BUYER": BuyerMission(
        mission_id="budget-buyer",
        request=(
            "I want wireless headphones under A$150. Same-day is nice but "
            "I will not pay more than my budget."
        ),
        persona="BUDGET_BUYER",
        profile=BuyerProfile(
            urgency="low",
            comfort="medium",
            reliability="medium",
            price_sensitivity="high",
            quality="low",
        ),
        hard=BuyerHardRequirements(
            max_total_cents=15000,
            require_wireless=True,
        ),
        acceptance_threshold=0.70,
        max_turns=3,
        negotiation_style="price_first",
    ),
    "ASSURANCE_BUYER": BuyerMission(
        mission_id="assurance-buyer",
        request=(
            "I need reliable wireless ANC headphones under A$400 with a long "
            "warranty. Delivery within two days is fine."
        ),
        persona="ASSURANCE_BUYER",
        profile=BuyerProfile(
            urgency="medium",
            comfort="medium",
            reliability="high",
            price_sensitivity="low",
            quality="high",
        ),
        hard=BuyerHardRequirements(
            max_total_cents=40000,
            max_delivery_days=2,
            require_anc=True,
            require_wireless=True,
        ),
        acceptance_threshold=0.60,
        max_turns=4,
        negotiation_style="assurance",
    ),
    "QUALITY_BUYER": BuyerMission(
        mission_id="quality-buyer",
        request=(
            "I want comfortable wireless noise-cancelling headphones under "
            "A$400 that I can wear for hours. Comfort matters more than price."
        ),
        persona="QUALITY_BUYER",
        profile=BuyerProfile(
            urgency="low",
            comfort="high",
            reliability="high",
            price_sensitivity="low",
            quality="high",
        ),
        hard=BuyerHardRequirements(
            max_total_cents=40000,
            require_anc=True,
            require_wireless=True,
        ),
        acceptance_threshold=0.64,
        max_turns=4,
        negotiation_style="quality",
    ),
    "BALANCED": BuyerMission(
        mission_id="balanced",
        request=(
            "Looking for wireless ANC headphones under A$280 for commuting. "
            "A good mix of comfort and value."
        ),
        persona="BALANCED",
        profile=BuyerProfile(),
        hard=BuyerHardRequirements(
            max_total_cents=28000,
            require_anc=True,
            require_wireless=True,
        ),
        acceptance_threshold=0.66,
        max_turns=4,
        negotiation_style="balanced",
    ),
}

SCENARIO_ALIASES = {
    "urgent-traveller": "URGENT_TRAVELLER",
    "hero": "URGENT_TRAVELLER",
    "budget-buyer": "BUDGET_BUYER",
    "budget": "BUDGET_BUYER",
    "assurance-buyer": "ASSURANCE_BUYER",
    "assurance": "ASSURANCE_BUYER",
    "quality-buyer": "QUALITY_BUYER",
    "quality": "QUALITY_BUYER",
    "balanced": "BALANCED",
}


def get_mission(scenario: str) -> BuyerMission:
    key = SCENARIO_ALIASES.get(scenario.strip().lower(), scenario.strip().upper())
    if key not in _PERSONAS:
        raise KeyError(f"Unknown buyer scenario: {scenario}")
    return _PERSONAS[key].model_copy(deep=True)


def all_personas() -> list[BuyerMission]:
    return [item.model_copy(deep=True) for item in _PERSONAS.values()]
