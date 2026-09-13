"""Semantic retrieval over products that already passed hard eligibility."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.decision.retrieval.models import RankedProductMatch

if TYPE_CHECKING:
    from app.decision.retrieval.matcher import rank_eligible as rank_eligible

__all__ = ["RankedProductMatch", "rank_eligible"]


def __getattr__(name: str) -> Any:
    if name == "rank_eligible":
        from app.decision.retrieval.matcher import rank_eligible as _rank_eligible

        return _rank_eligible
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
