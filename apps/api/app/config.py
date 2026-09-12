"""Application configuration loaded from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the AstraOS API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    postgres_db: str = "astraos"
    postgres_user: str = "astraos"
    postgres_password: str = "astraos"
    postgres_host: str = "db"
    postgres_port: int = 5432

    database_url: str = ""

    frontend_url: str = "http://localhost:3000"
    astraos_seed: int = 2026

    intent_parser_mode: str = "rule_based"
    llm_api_key: str = ""
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    offer_ttl_seconds: int = 300

    @property
    def sqlalchemy_database_uri(self) -> str:
        """Return a SQLAlchemy URL using the psycopg driver."""
        url = self.database_url.strip() or (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def cors_origins(self) -> list[str]:
        """Origins permitted for local frontend development."""
        origins = {
            self.frontend_url,
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        }
        return sorted(origins)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
