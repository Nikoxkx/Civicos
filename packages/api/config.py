"""
CivicOS API — Configuration.

All settings are loaded from environment variables and validated with Pydantic.
Never hardcode secrets — they must come from the environment or .env file.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables.

    Use `get_settings()` to access — it caches the parsed result.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://civicos:civicos_dev@localhost:5432/civicos"

    # Anthropic
    anthropic_api_key: str = ""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    environment: str = "development"
    log_level: str = "info"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance. Safe to call repeatedly."""
    return Settings()
