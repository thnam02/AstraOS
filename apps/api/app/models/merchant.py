"""Single-merchant identity for the hackathon MVP."""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.objective import MerchantObjective
    from app.models.policy import MerchantPolicy


class Merchant(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """The merchant that owns catalogue and policy data."""

    __tablename__ = "merchants"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="AUD")
    data_mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default="DEMO_SEED"
    )

    policies: Mapped[list["MerchantPolicy"]] = relationship(
        back_populates="merchant",
    )
    objectives: Mapped[list["MerchantObjective"]] = relationship(
        back_populates="merchant",
    )
