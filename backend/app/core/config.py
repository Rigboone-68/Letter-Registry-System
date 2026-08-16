"""Application configuration.

All configuration is environment-based. No credentials, connection strings,
or secrets are hard-coded anywhere in the codebase. Values are read from the
process environment (optionally seeded from a local `.env` file that is never
committed — see `.env.example` for the expected keys).
"""

from functools import lru_cache
from typing import Annotated, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the LRS backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ----------------------------------------------------
    APP_NAME: str = "Letter Registry System"
    APP_SHORT_NAME: str = "LRS"
    APP_ENV: str = "development"          # development | staging | production
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # --- Security -------------------------------------------------------
    # Supplied by the environment in every deployment. There is deliberately
    # no default value for production use.
    SECRET_KEY: str = Field(default="", description="Signing key, set via environment")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- Database -------------------------------------------------------
    # Example shape (never a real value): postgresql+psycopg2://user:pass@host:5432/db
    DATABASE_URL: str = ""

    # --- CORS -----------------------------------------------------------
    # Comma-separated list in the environment, e.g. "http://localhost:5173".
    # `NoDecode` stops pydantic-settings from JSON-decoding this env value
    # before the validator below runs (its default behavior for list-typed
    # fields, which fails on a plain comma-separated string like the one
    # above and crashes settings loading before the validator gets a turn).
    CORS_ORIGINS: Annotated[List[str], NoDecode] = Field(default=[])

    # --- Document storage ----------------------------------------------
    # Filesystem root for scanned letters. The database stores only metadata
    # and a relative path into this root.
    STORAGE_PATH: str = "../storage/letters"

    # --- Logging --------------------------------------------------------
    LOG_LEVEL: str = "INFO"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value):
        """Accept either a comma-separated string or a real list."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (single source of truth)."""
    return Settings()


settings = get_settings()
