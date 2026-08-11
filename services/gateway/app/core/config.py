"""Gateway Service — pydantic-settings configuration reading from root .env."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    APP_ENV: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # JWT (shared secret with core-service — read from root .env)
    JWT_SECRET_KEY: str = "change-me-in-root-env"
    JWT_ALGORITHM: str = "HS256"

    # Redis (for rate limiting counters and user session cache)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    GATEWAY_SERVICE_REDIS_PREFIX: str = "insightapi:gateway:"

    # Downstream service URLs
    CORE_SERVICE_URL: str = "http://core-service:8001"
    AGENT_SERVICE_URL: str = "http://agent-service:8002"

    # Internal secret for service-to-service auth
    GATEWAY_SECRET: str = "change-me-in-root-env"

    model_config = SettingsConfigDict(
        env_file=(
            "../../../../.env",
            "../../../.env",
            "../../.env",
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    def get_redis_key(self, suffix: str) -> str:
        """Return key namespaced with service-specific Redis prefix."""
        return f"{self.GATEWAY_SERVICE_REDIS_PREFIX}{suffix.lstrip(':')}"


settings = GatewaySettings()
