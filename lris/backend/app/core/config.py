"""Application-wide configuration.

Settings are loaded from environment variables (and a local `.env` file in
development), with sane defaults for local development only. Production
deployments must set `DATABASE_URL` and `ENVIRONMENT=production` explicitly;
no production secret ever ships as a default here.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[3]  # repo root


class Settings(BaseSettings):
    """Central application settings.

    Attributes:
        environment: Deployment environment, controls DB dialect defaults
            and log verbosity.
        database_url: SQLAlchemy connection string. Defaults to a local
            SQLite file in development.
        log_level: Root logging level.
        data_dir: Root directory for versioned pipeline datasets.
        api_v1_prefix: URL prefix for versioned API routes.
        cors_origins: Allowed origins for the frontend dev server.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "production", "test"] = "development"

    database_url: str = Field(
        default=f"sqlite:///{BASE_DIR / 'data' / 'dev.db'}",
        description="SQLAlchemy connection string.",
    )

    log_level: str = "INFO"

    data_dir: Path = BASE_DIR / "data"

    api_v1_prefix: str = "/api/v1"

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Scraper defaults
    scraper_request_timeout_seconds: float = 15.0
    scraper_min_delay_seconds: float = 1.0
    scraper_max_delay_seconds: float = 3.0
    scraper_max_retries: int = 3


@lru_cache
def get_settings() -> Settings:
    """Return a cached `Settings` instance.

    Cached so repeated `Depends(get_settings)` calls across the app don't
    re-parse the environment on every request.
    """
    return Settings()
