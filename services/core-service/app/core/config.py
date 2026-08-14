"""Core Service — pydantic-settings configuration reading from root .env."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class CoreSettings(BaseSettings):
    # App
    APP_NAME: str = "InsightAPI AI"
    APP_ENV: str = "development"
    APP_URL: str = "http://localhost"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database (shared Postgres — from root .env)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "insightapi"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    CORE_SERVICE_REDIS_PREFIX: str = "insightapi:core:"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-root-env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OAuth — GitHub
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    # OAuth — Google
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # OAuth shared
    OAUTH_REDIRECT_URI: str = "http://localhost:3000/callback"

    # SMTP Email Delivery Credentials
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_TLS: bool = True

    # Stripe (Payment — inside core-service)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_ENTERPRISE: str = ""
    STRIPE_PRICE_METERED_CRAWL: str = ""

    # Internal
    GATEWAY_SECRET: str = "change-me-in-root-env"

    model_config = SettingsConfigDict(
        # Root .env is 4 levels up: services/core-service/app/core/config.py -> root
        env_file=(
            "../../../../.env",
            "../../../.env",
            "../../.env",
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def get_redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    def get_redis_key(self, suffix: str) -> str:
        """Return key namespaced with service-specific Redis prefix."""
        return f"{self.CORE_SERVICE_REDIS_PREFIX}{suffix.lstrip(':')}"


settings = CoreSettings()
