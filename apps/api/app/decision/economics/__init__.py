"""Merchant contribution accounting. Not buyer utility or P(win)."""

from app.decision.economics.calculator import compute_economics
from app.decision.economics.models import OfferEconomics

__all__ = ["OfferEconomics", "compute_economics"]
