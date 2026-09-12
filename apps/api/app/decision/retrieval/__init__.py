"""Semantic retrieval over products that already passed hard eligibility."""

from app.decision.retrieval.matcher import rank_eligible
from app.decision.retrieval.models import RankedProductMatch

__all__ = ["RankedProductMatch", "rank_eligible"]
