"""Merchant policy persistence and validation."""

from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MerchantPolicy
from app.schemas.merchant import MerchantPolicyUpdate
from app.services.policy import MerchantPolicyService, PolicyValidationError
from tests.factories import make_merchant, make_policy


@pytest.mark.asyncio
async def test_policy_loads(db_session: AsyncSession) -> None:
    service = MerchantPolicyService(db_session)
    policy = await service.get_active()
    assert policy is not None
    assert policy.name == "Astra Electronics Default Policy"
    assert policy.minimum_margin_rate == 0.15
    assert policy.maximum_discount_rate == 0.10


@pytest.mark.asyncio
async def test_min_margin_validation() -> None:
    payload = MerchantPolicyUpdate.model_validate({"minimum_margin_rate": 0.2})
    assert payload.minimum_margin_rate == 0.2
    with pytest.raises(ValidationError):
        MerchantPolicyUpdate.model_validate({"minimum_margin_rate": 1.5})


@pytest.mark.asyncio
async def test_max_discount_validation() -> None:
    with pytest.raises(ValidationError):
        MerchantPolicyUpdate.model_validate({"maximum_discount_rate": 1.2})


@pytest.mark.asyncio
async def test_invalid_policy_rejected_by_db(db_session: AsyncSession) -> None:
    merchant = make_merchant()
    policy = make_policy(merchant.id, minimum_margin_rate=Decimal("1.5000"))
    db_session.add_all([merchant, policy])
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_policy_service_rejects_invalid_margin(db_session: AsyncSession) -> None:
    service = MerchantPolicyService(db_session)
    payload = MerchantPolicyUpdate.model_construct(minimum_margin_rate=1.2)
    with pytest.raises(PolicyValidationError):
        await service.update_active(payload)


@pytest.mark.asyncio
async def test_inactive_policy_can_exist(db_session: AsyncSession) -> None:
    merchant = make_merchant()
    policy = make_policy(merchant.id, is_active=False)
    db_session.add_all([merchant, policy])
    await db_session.flush()
    loaded = await db_session.get(MerchantPolicy, policy.id)
    assert loaded is not None
    assert loaded.is_active is False
