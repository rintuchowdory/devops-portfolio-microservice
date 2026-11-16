"""Application settings, loaded from environment variables or a .env file."""

from __future__ import annotations

import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Without this, pydantic-settings tries json.loads() on list fields before
        # any validator runs, so ALLOWED_ORIGINS=a,b would crash at import time.
        enable_decoding=False,
    )

    APP_NAME: str = "DevOps Mesh API"
    VERSION: str = "1.1.0"
    ENV: str = "development"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:4321",  # Astro dev server
        "http://localhost:8080",
        "https://rintuchowdory.github.io",
    ]

    # Metrics refresh interval (seconds) used by the dashboard summary payload
    METRICS_TTL: int = 5

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_MAX_LINES: int = 500

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accept JSON arrays as well as comma separated strings.

        Render and Docker users usually set `ALLOWED_ORIGINS=https://a.dev,https://b.dev`,
        which pydantic-settings would otherwise reject because it expects JSON.
        """
        if isinstance(value, str) and not value.strip().startswith("["):
            parts = [item.strip() for item in value.split(",") if item.strip()]
            return parts or ["*"]
        if isinstance(value, str):
            return json.loads(value)
        return value


settings = Settings()
