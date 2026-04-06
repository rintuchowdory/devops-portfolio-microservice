from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "DevOps Mesh API"
    VERSION: str = "1.0.0"
    ENV: str = "development"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security
    SECRET_KEY: str = "dev-secret-change-in-production"
    API_KEY_HEADER: str = "X-API-Key"

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:4321",  # Astro dev
        "http://localhost:8080",
        "*",
    ]

    # Metrics refresh interval (seconds)
    METRICS_TTL: int = 5

    # Log settings
    LOG_LEVEL: str = "INFO"
    LOG_MAX_LINES: int = 500

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
