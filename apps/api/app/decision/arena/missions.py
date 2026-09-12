"""Seeded synthetic missions. No unbounded LLM generation."""

from __future__ import annotations

import random
from datetime import UTC, datetime

from app.decision.arena.config import PROFILE_FOR_SEGMENT, SEGMENT_SHARES
from app.decision.arena.models import BuyerMission

TEMPLATES: dict[str, list[tuple[str, list[str], list[str]]]] = {
    "budget": [
        (
            "I need wireless ANC headphones under A${budget}. "
            "Cheapest option that still works is fine. Two-day delivery is ok.",
            ["price", "anc", "wireless"],
            ["budget"],
        ),
        (
            "Looking for noise-cancelling headphones, budget is A${budget} max. "
            "I care about price more than extras.",
            ["price", "anc"],
            ["budget"],
        ),
        (
            "Wireless headphones under A${budget}, ANC required. "
            "No rush on delivery.",
            ["price", "anc", "wireless"],
            ["budget"],
        ),
    ],
    "urgent": [
        (
            "I'm flying tomorrow and need wireless ANC headphones under A${budget}. "
            "I need them delivered today. Comfort matters more than cheapest.",
            ["anc", "price", "delivery_days", "wireless"],
            ["urgent", "long_haul"],
        ),
        (
            "Need ANC headphones today under A${budget}. "
            "Same-day delivery is mandatory. "
            "Reliability matters more than saving a few dollars.",
            ["anc", "price", "delivery_days"],
            ["urgent"],
        ),
        (
            "Long-haul flight tonight. Wireless noise-cancelling headphones under "
            "A${budget}, delivered today. Comfort over lowest price.",
            ["anc", "price", "delivery_days", "wireless"],
            ["urgent", "long_haul"],
        ),
    ],
    "assurance": [
        (
            "I want reliable ANC headphones under A${budget}. "
            "A long warranty matters more than getting the cheapest pair.",
            ["anc", "price"],
            ["assurance"],
        ),
        (
            "Wireless noise-cancelling headphones under A${budget}. "
            "I need a strong warranty and easy returns.",
            ["anc", "price", "wireless"],
            ["assurance"],
        ),
    ],
    "quality": [
        (
            "I want the most comfortable reliable ANC headphones under A${budget}. "
            "Price is secondary to comfort and build quality.",
            ["anc", "price"],
            ["quality"],
        ),
        (
            "Premium-feeling wireless ANC headphones under A${budget}. "
            "Comfort and reliability over cheapest price.",
            ["anc", "price", "wireless"],
            ["quality"],
        ),
    ],
    "balanced": [
        (
            "Wireless ANC headphones under A${budget}. "
            "A reasonable mix of price, delivery, and warranty is fine.",
            ["anc", "price", "wireless"],
            ["balanced"],
        ),
        (
            "I need noise-cancelling headphones under A${budget} for commuting. "
            "Comfort and a fair price both matter.",
            ["anc", "price"],
            ["balanced", "commuting"],
        ),
    ],
    "gaming_studio": [
        (
            "Looking for wireless ANC headphones under A${budget} for gaming. "
            "Comfort for long sessions matters.",
            ["anc", "price", "wireless"],
            ["gaming"],
        ),
        (
            "Studio and editing work. ANC headphones under A${budget}, "
            "comfort for long sessions.",
            ["anc", "price"],
            ["studio"],
        ),
    ],
    "difficult": [
        (
            "I need foldable wireless ANC headphones under A${strict} "
            "delivered today with a long warranty. Comfort and cheapest price "
            "both matter equally, which I know conflicts.",
            ["anc", "price", "delivery_days", "wireless", "foldable"],
            ["difficult", "strict_budget", "urgent"],
        ),
        (
            "Repairable sustainable headphones under A${budget} delivered today. "
            "Must have ANC.",
            ["anc", "price", "delivery_days"],
            ["difficult", "unsupported"],
        ),
        (
            "I need ANC headphones under A${strict} delivered today. "
            "In stock only.",
            ["anc", "price", "delivery_days", "in_stock"],
            ["difficult", "strict_budget", "low_stock"],
        ),
    ],
}

BUDGETS = {
    "budget": (18000, 22000, 26000, 30000),
    "urgent": (30000, 33000, 35000, 38000),
    "assurance": (28000, 32000, 35000),
    "quality": (30000, 35000, 40000),
    "balanced": (25000, 30000, 35000),
    "gaming_studio": (25000, 32000, 36000),
    "difficult": (20000, 22000, 24000),
}


def _counts(total: int, shares: dict[str, float]) -> dict[str, int]:
    raw = {key: total * share for key, share in shares.items()}
    counts = {key: int(value) for key, value in raw.items()}
    assigned = sum(counts.values())
    leftovers = sorted(
        shares,
        key=lambda key: (raw[key] - counts[key], key),
        reverse=True,
    )
    idx = 0
    while assigned < total:
        counts[leftovers[idx % len(leftovers)]] += 1
        assigned += 1
        idx += 1
    return counts


def generate_missions(
    count: int,
    *,
    seed: int,
    shares: dict[str, float] | None = None,
    profile_override: str | None = None,
) -> list[BuyerMission]:
    rng = random.Random(seed)
    parts = _counts(count, shares or SEGMENT_SHARES)
    missions: list[BuyerMission] = []
    seq = 0
    for segment, n in parts.items():
        templates = TEMPLATES[segment]
        budgets = BUDGETS[segment]
        profile = profile_override or PROFILE_FOR_SEGMENT[segment]
        for _ in range(n):
            text, fields, tags = templates[rng.randrange(len(templates))]
            budget = rng.choice(budgets)
            if segment == "difficult" and "strict" in text:
                budget = rng.choice((18000, 20000, 22000))
            intent = text.replace("${budget}", str(budget // 100)).replace(
                "${strict}", str(budget // 100)
            )
            seq += 1
            missions.append(
                BuyerMission(
                    id=f"m-{seed}-{seq:04d}",
                    raw_intent=intent,
                    category="headphones",
                    buyer_profile=profile,
                    scenario_tags=sorted({segment, *tags}),
                    expected_hard_constraints=fields,
                    seed=seed + seq,
                    created_at=datetime.now(UTC),
                )
            )
    rng.shuffle(missions)
    return missions


HERO_MISSION = BuyerMission(
    id="hero-long-haul",
    raw_intent=(
        "I need ANC headphones under A$350 for a long-haul flight. "
        "Delivered today. Comfort and reliability matter more than "
        "getting the cheapest option."
    ),
    category="headphones",
    buyer_profile="URGENT_TRAVELLER",
    scenario_tags=["urgent", "long_haul", "hero"],
    expected_hard_constraints=["anc", "price", "delivery_days"],
    seed=2026,
)
