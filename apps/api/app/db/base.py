"""Declarative SQLAlchemy base.

Domain models are introduced in Stage 1. This module only provides
the shared metadata Alembic will bind to.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for future AstraOS domain models."""
