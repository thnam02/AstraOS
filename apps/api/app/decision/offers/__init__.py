"""Offer construction. Builds configurations; does not choose a winner."""

from app.decision.offers.constructor import construct_variant
from app.decision.offers.models import OfferCandidate

__all__ = ["OfferCandidate", "construct_variant"]
