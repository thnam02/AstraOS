"""FastAPI application entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import engine, wait_for_database
from app.routes import api_v1_router
from app.routes.health import router as health_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Connect to PostgreSQL on startup when not running tests."""
    if settings.app_env != "test":
        await wait_for_database()
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    """Build the AstraOS API application."""
    application = FastAPI(
        title="AstraOS API",
        description="Merchant-side decision engine for agentic commerce.",
        version="0.0.1",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router)
    application.include_router(api_v1_router, prefix="/api/v1")
    return application


app = create_app()
