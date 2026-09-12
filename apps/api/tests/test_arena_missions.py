"""Seeded mission generation. No unbounded LLM inputs."""

from app.decision.arena.config import SEGMENT_SHARES
from app.decision.arena.missions import generate_missions


def test_same_seed_same_missions() -> None:
    first = generate_missions(40, seed=2026)
    second = generate_missions(40, seed=2026)
    assert [item.raw_intent for item in first] == [item.raw_intent for item in second]
    assert [item.buyer_profile for item in first] == [
        item.buyer_profile for item in second
    ]


def test_different_seed_may_differ() -> None:
    first = generate_missions(40, seed=2026)
    second = generate_missions(40, seed=2027)
    assert [item.raw_intent for item in first] != [item.raw_intent for item in second]


def test_segment_distribution() -> None:
    missions = generate_missions(100, seed=2026)
    counts: dict[str, int] = {}
    for item in missions:
        primary = next(
            tag for tag in item.scenario_tags if tag in SEGMENT_SHARES
        )
        counts[primary] = counts.get(primary, 0) + 1
    assert counts["budget"] == 20
    assert counts["urgent"] == 20
    assert counts["assurance"] == 15
    assert counts["quality"] == 15
    assert counts["balanced"] == 15
    assert counts["gaming_studio"] == 10
    assert counts["difficult"] == 5


def test_intents_are_non_empty() -> None:
    missions = generate_missions(30, seed=2026)
    assert all(item.raw_intent.strip() for item in missions)
    assert all("headphone" in item.raw_intent.lower() for item in missions)
