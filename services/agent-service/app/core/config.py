import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "InsightAPI AI"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # LLM Provider Selection ("auto", "gemini", "azure", "openai")
    LLM_PROVIDER: str = "auto"

    # Google Gemini Settings
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.7-flash"
    GEMINI_MODEL_FAST: str = "gemini-3.7-flash"
    GEMINI_MODEL_SMART: str = "gemini-3.7-flash"
    GEMINI_MODEL_VISION: str = "gemini-3.7-flash"

    # Azure OpenAI Settings
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_VERSION: str = "2024-12-01-preview"
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o"
    AZURE_OPENAI_API_KEY: Optional[str] = None

    # Standard OpenAI Settings (Fallback)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Database Settings (shared Postgres — values come from root .env)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "insightapi"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Redis Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    AGENT_SERVICE_REDIS_PREFIX: str = "insightapi:agent:"

    # ── Celery Job Queue ─────────────────────────────────────────────────────
    # Defaults to the same Redis instance used by the rest of the service.
    # Override via CELERY_BROKER_URL / CELERY_RESULT_BACKEND in root .env.
    CELERY_BROKER_URL: Optional[str] = None      # falls back to get_redis_url()
    CELERY_RESULT_BACKEND: Optional[str] = None  # falls back to get_redis_url()

    # ── Sentry Error Tracking ────────────────────────────────────────────────
    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1  # 10% of requests traced

    # Chatbot Subscription Tier Daily Message Limits
    TIER_CHAT_LIMIT_FREE: int = 15
    TIER_CHAT_LIMIT_STARTER: int = 50
    TIER_CHAT_LIMIT_PRO: int = 250
    TIER_CHAT_LIMIT_ENTERPRISE: int = 10000
    TIER_CHAT_LIMIT_ADMIN: int = 10000

    def get_tier_chat_limit(self, tier: str) -> int:
        normalized = (tier or "FREE").upper()
        mapping = {
            "FREE": self.TIER_CHAT_LIMIT_FREE,
            "STARTER": self.TIER_CHAT_LIMIT_STARTER,
            "PRO": self.TIER_CHAT_LIMIT_PRO,
            "ENTERPRISE": self.TIER_CHAT_LIMIT_ENTERPRISE,
            "ADMIN": self.TIER_CHAT_LIMIT_ADMIN,
        }
        return mapping.get(normalized, self.TIER_CHAT_LIMIT_FREE)

    # Authentication Profile Encryption Key
    AUTH_PROFILE_SECRET_KEY: str = "insightapi-auth-profile-encryption-key-32chars!"

    # Engine Defaults & Compliance Guardrails
    MAX_CRAWL_PAGES: int = 15
    CRAWL_TIMEOUT_SECONDS: int = 300
    RESPECT_ROBOTS_TXT: bool = True
    MIN_DOMAIN_DELAY_MS: int = 500
    REPORTS_DIR: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "reports")
    )

    # ── SaaS Tier Enforcement ────────────────────────────────────────────────
    FREE_TIER_DAILY_QUERIES: int = 1

    # ── Internal Service Communication ──────────────────────────────────────
    CORE_SERVICE_URL: str = "http://core-service:8001"
    GATEWAY_SECRET: str = "change-me-in-root-env"

    # ── Intelligence Feature Flags ───────────────────────────────────────────
    LLM_PLANNER_ENABLED: bool = True
    LLM_VISION_FALLBACK_ENABLED: bool = True
    LLM_REFLECTION_ENABLED: bool = True
    LLM_SEMANTIC_SUMMARY_ENABLED: bool = True
    LLM_SMART_FORM_ENABLED: bool = True

    # ── Model Router — Tiered Model Selection ─────────────────────────────────
    OPENAI_MODEL_FAST: str = "gpt-4o-mini"
    OPENAI_MODEL_SMART: str = "gpt-4o"
    OPENAI_MODEL_VISION: str = "gpt-4o-mini"

    # Azure model overrides per tier (if using Azure OpenAI)
    AZURE_OPENAI_DEPLOYMENT_FAST: str = "gpt-4o-mini"
    AZURE_OPENAI_DEPLOYMENT_SMART: str = "gpt-4o"
    AZURE_OPENAI_DEPLOYMENT_VISION: str = "gpt-4o-mini"

    # ── LLM Cost Management ──────────────────────────────────────────────────
    LLM_TOKEN_BUDGET_PER_CRAWL: int = 50000
    LLM_PLANNER_MAX_CALLS: int = 20
    LLM_REFLECTION_INTERVAL: int = 5
    VISION_FALLBACK_THRESHOLD: int = 3

    # ── Third-Party Integration Settings ─────────────────────────────────────
    STEALTH_MODE_ENABLED: bool = True
    HUMANIZE_INTERACTIONS: bool = True
    PROXY_URL: Optional[str] = None
    CHROME_EXTENSION_PATHS: list[str] = []
    FUZZING_ENABLED: bool = True

    # ── Security Testing (Phase 4) ────────────────────────────────────────────
    # Global kill-switch — must be True for SecurityReasonerNode to activate.
    # Set to True in production only for tenants that have explicitly opted in.
    SECURITY_TESTING_ENABLED: bool = False

    model_config = SettingsConfigDict(
        # Root .env is 4 levels up from this file's location:
        # services/agent-service/app/core/config.py -> root
        env_file=(
            "../../../../.env",   # when running from service root in Docker
            "../../../.env",      # when running locally from services/agent-service/
            "../../.env",         # fallback
            ".env",               # fallback local
        ),
        env_file_encoding="utf-8",
        extra="ignore"
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
        return f"{self.AGENT_SERVICE_REDIS_PREFIX}{suffix.lstrip(':')}"


settings = Settings()
