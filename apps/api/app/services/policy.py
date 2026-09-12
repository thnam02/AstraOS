"""Merchant policy updates. Validates bounds only — no offer evaluation."""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MerchantPolicy
from app.repositories.policy import MerchantPolicyRepository
from app.schemas.merchant import MerchantPolicyResponse, MerchantPolicyUpdate


class PolicyValidationError(ValueError):
    """Raised when a policy update is out of bounds."""


class MerchantPolicyService:
    """Read and persist the active merchant policy."""

    def __init__(self, session: AsyncSession) -> None:
        self.repository = MerchantPolicyRepository(session)
        self.session = session

    async def get_active(self) -> MerchantPolicyResponse | None:
        policy = await self.repository.get_active()
        if policy is None:
            return None
        return self._to_response(policy)

    async def update_active(
        self, payload: MerchantPolicyUpdate
    ) -> MerchantPolicyResponse:
        policy = await self.repository.get_active()
        if policy is None:
            raise PolicyValidationError("No active merchant policy is configured.")

        data = payload.model_dump(exclude_unset=True)
        if "minimum_margin_rate" in data:
            rate = data["minimum_margin_rate"]
            if rate < 0 or rate >= 1:
                raise PolicyValidationError("minimum_margin_rate must be >= 0 and < 1.")
            policy.minimum_margin_rate = Decimal(str(rate))
        if "maximum_discount_rate" in data:
            rate = data["maximum_discount_rate"]
            if rate < 0 or rate > 1:
                raise PolicyValidationError(
                    "maximum_discount_rate must be >= 0 and <= 1."
                )
            policy.maximum_discount_rate = Decimal(str(rate))
        if "delivery_subsidy_enabled" in data:
            policy.delivery_subsidy_enabled = data["delivery_subsidy_enabled"]
        if "warranty_upgrade_enabled" in data:
            policy.warranty_upgrade_enabled = data["warranty_upgrade_enabled"]
        if "bundle_enabled" in data:
            policy.bundle_enabled = data["bundle_enabled"]
        if "flexible_returns_enabled" in data:
            policy.flexible_returns_enabled = data["flexible_returns_enabled"]

        await self.repository.update_active(policy)
        await self.session.commit()
        return self._to_response(policy)

    def _to_response(self, policy: MerchantPolicy) -> MerchantPolicyResponse:
        return MerchantPolicyResponse(
            id=policy.id,
            merchant_id=policy.merchant_id,
            name=policy.name,
            is_active=policy.is_active,
            minimum_margin_rate=float(policy.minimum_margin_rate),
            maximum_discount_rate=float(policy.maximum_discount_rate),
            delivery_subsidy_enabled=policy.delivery_subsidy_enabled,
            warranty_upgrade_enabled=policy.warranty_upgrade_enabled,
            bundle_enabled=policy.bundle_enabled,
            flexible_returns_enabled=policy.flexible_returns_enabled,
            loyalty_enabled=policy.loyalty_enabled,
            maximum_delivery_subsidy_cents=policy.maximum_delivery_subsidy_cents,
            maximum_warranty_subsidy_cents=policy.maximum_warranty_subsidy_cents,
            maximum_bundle_subsidy_cents=policy.maximum_bundle_subsidy_cents,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )
