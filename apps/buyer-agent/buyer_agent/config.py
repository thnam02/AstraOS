"""Buyer Agent configuration. Independent of AstraOS settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PACKAGE_ENV = Path(__file__).resolve().parents[1] / ".env"
_REPO_ENV = Path(__file__).resolve().parents[3] / ".env"


class BuyerAgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_PACKAGE_ENV, _REPO_ENV),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    astraos_agent_base_url: str = "http://localhost:8000"
    buyer_agent_mode: str = "deterministic"
    buyer_agent_model: str = "gpt-4o-mini"
    buyer_agent_max_turns: int = 4
    buyer_agent_timeout: float = 30.0
    buyer_agent_api_key: str = ""
    llm_api_key: str = ""
    openai_api_key: str = ""
    buyer_agent_llm_base_url: str = "https://api.openai.com/v1"
    buyer_agent_id: str = "astraos-buyer-agent"

    @property
    def api_key(self) -> str:
        return (
            self.buyer_agent_api_key
            or self.llm_api_key
            or self.openai_api_key
        ).strip()


def load_settings() -> BuyerAgentSettings:
    return BuyerAgentSettings()
