"""Merchant strategy registry. AstraOS reuses the live Stage 5 engine."""

from app.decision.arena.models import MerchantStrategy
from app.decision.arena.strategies.astraos import AstraOSStrategy
from app.decision.arena.strategies.cheapest import CheapestEligibleStrategy
from app.decision.arena.strategies.default import DefaultMerchantStrategy
from app.decision.arena.strategies.discount import AlwaysDiscountStrategy
from app.decision.arena.strategies.semantic import SemanticOnlyStrategy

STRATEGY_FACTORIES: dict[str, type] = {
    "DEFAULT": DefaultMerchantStrategy,
    "ALWAYS_DISCOUNT": AlwaysDiscountStrategy,
    "CHEAPEST_ELIGIBLE": CheapestEligibleStrategy,
    "SEMANTIC_ONLY": SemanticOnlyStrategy,
    "ASTRAOS": AstraOSStrategy,
}


def get_strategy(name: str) -> MerchantStrategy:
    factory = STRATEGY_FACTORIES.get(name)
    if factory is None:
        raise KeyError(f"Unknown arena strategy: {name}")
    strategy: MerchantStrategy = factory()
    return strategy


def strategy_set(names: list[str]) -> list[MerchantStrategy]:
    return [get_strategy(name) for name in names]
