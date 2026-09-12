"""Cached product embeddings. Not offer or outcome records."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class VariantEmbedding(UUIDPrimaryKeyMixin, Base):
    """One embedding per variant and document version."""

    __tablename__ = "variant_embeddings"

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    embedding: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(80), nullable=False)
    semantic_document_version: Mapped[str] = mapped_column(String(64), nullable=False)
    document_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
