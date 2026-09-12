"""Health-check response schema."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Public liveness payload for GET /health."""

    status: str = Field(examples=["ok"])
    service: str = Field(examples=["astraos-api"])
