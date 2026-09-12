"""Simulated buyer-utility models. These scores are not probabilities."""

from pydantic import BaseModel, Field

UTILITY_DISCLAIMER = (
    "The utility model is a transparent cold-start simulation. "
    "It is not a prediction of proprietary shopping-agent behaviour."
)

UTILITY_VERSION = "simulated.v1"


class UtilityWeights(BaseModel):
    """Component weights. Must sum to 1 after resolution."""

    product: float = Field(ge=0, le=1)
    price: float = Field(ge=0, le=1)
    delivery: float = Field(ge=0, le=1)
    warranty: float = Field(ge=0, le=1)
    bundle: float = Field(ge=0, le=1)
    returns: float = Field(ge=0, le=1)

    def as_dict(self) -> dict[str, float]:
        return {
            "product": self.product,
            "price": self.price,
            "delivery": self.delivery,
            "warranty": self.warranty,
            "bundle": self.bundle,
            "returns": self.returns,
        }

    def total(self) -> float:
        return sum(self.as_dict().values())


class FitComponents(BaseModel):
    product: float = Field(ge=0, le=1)
    price: float = Field(ge=0, le=1)
    delivery: float = Field(ge=0, le=1)
    warranty: float = Field(ge=0, le=1)
    bundle: float = Field(ge=0, le=1)
    returns: float = Field(ge=0, le=1)


class UtilityContribution(BaseModel):
    component: str
    fit: float
    weight: float
    weighted: float


class UtilityTrace(BaseModel):
    """Decomposable simulated utility. Not a win or purchase probability."""

    components: list[UtilityContribution]
    total: float
    version: str = UTILITY_VERSION


class SimulatedBuyerUtility(BaseModel):
    score: float
    fits: FitComponents
    weights: UtilityWeights
    trace: UtilityTrace
    profile_id: str
    disclaimer: str = UTILITY_DISCLAIMER
