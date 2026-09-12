"""Top Stage 3 semantic product with the default commercial configuration."""

from app.decision.arena.models import ArenaContext, StrategyResponse
from app.decision.arena.strategies.default import DefaultMerchantStrategy


class SemanticOnlyStrategy:
    name = "SEMANTIC_ONLY"

    def generate_response(self, context: ArenaContext) -> StrategyResponse:
        response = DefaultMerchantStrategy().generate_response(context)
        return response.model_copy(update={"strategy_name": self.name})
