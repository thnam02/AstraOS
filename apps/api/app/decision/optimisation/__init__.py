"""Merchant selection over a Pareto frontier. Not negotiation."""

from app.decision.optimisation.engine import score_space
from app.decision.optimisation.models import ALGORITHM_VERSION, ScoredOffer

__all__ = ["ALGORITHM_VERSION", "ScoredOffer", "score_space"]
