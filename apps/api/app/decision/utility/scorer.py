"""Transparent simulated buyer utility. Never a win or purchase probability."""

from app.decision.economics.normalization import clamp01
from app.decision.intent.models import ShoppingIntent
from app.decision.offers.models import OfferCandidate
from app.decision.utility.feature_mapping import fit_components, resolve_weights
from app.decision.utility.models import (
    UTILITY_DISCLAIMER,
    UTILITY_VERSION,
    SimulatedBuyerUtility,
    UtilityContribution,
    UtilityTrace,
    UtilityWeights,
)


def score_offer(
    offer: OfferCandidate,
    *,
    intent: ShoppingIntent,
    product_fit: float,
    price_low: int,
    price_high: int,
    weights: UtilityWeights,
    profile_id: str,
) -> SimulatedBuyerUtility:
    fits = fit_components(
        offer,
        intent=intent,
        product_fit_score=product_fit,
        price_low=price_low,
        price_high=price_high,
    )
    mapping = (
        ("product", fits.product, weights.product),
        ("price", fits.price, weights.price),
        ("delivery", fits.delivery, weights.delivery),
        ("warranty", fits.warranty, weights.warranty),
        ("bundle", fits.bundle, weights.bundle),
        ("returns", fits.returns, weights.returns),
    )
    contributions = [
        UtilityContribution(
            component=name,
            fit=round(fit, 6),
            weight=round(weight, 6),
            weighted=round(fit * weight, 6),
        )
        for name, fit, weight in mapping
    ]
    total = clamp01(sum(item.weighted for item in contributions))
    return SimulatedBuyerUtility(
        score=round(total, 6),
        fits=fits,
        weights=weights,
        trace=UtilityTrace(
            components=contributions, total=round(total, 6), version=UTILITY_VERSION
        ),
        profile_id=profile_id,
        disclaimer=UTILITY_DISCLAIMER,
    )


def weights_for(intent: ShoppingIntent, profile_id: str) -> UtilityWeights:
    return resolve_weights(intent, profile_id)
