import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.router import api_router
from app.routers import stream, chat

# Ensure all SQLAlchemy models are registered on Base.metadata
from app.models.crawl_session import CrawlSession
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession  # noqa: F401 — registers chat_sessions table
from app.models.crawl_snapshot import CrawlSnapshot  # noqa: F401 — registers crawl_snapshots table
from app.models.llm_usage import LlmUsage  # noqa: F401 — registers llm_usage table
from app.models.auth_profile import AuthProfile  # noqa: F401
from app.models.domain_verification import VerifiedDomain, TosAcceptance  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.security_test_pattern import SecurityTestPattern  # noqa: F401 — registers security_test_patterns
from app.models.security_finding import SecurityFinding  # noqa: F401 — registers security_findings
from app.models.security_approval import SecurityApproval  # noqa: F401 — registers security_approvals



from app.core.observability import CorrelationIdMiddleware, metrics
from fastapi.responses import PlainTextResponse

logger = logging.getLogger(__name__)

# ── Sentry SDK (initialise before anything else so it can catch startup errors) ──
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            CeleryIntegration(),
        ],
        # Do not send PII — user IPs are already in audit_logs
        send_default_pii=False,
    )
    logger.info(f"Sentry SDK initialised (env={settings.APP_ENV}, sample_rate={settings.SENTRY_TRACES_SAMPLE_RATE})")
else:
    logger.info("Sentry DSN not configured — error tracking disabled.")



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database schema is verified safely on startup."""
    if settings.DEBUG or settings.APP_ENV in ("development", "test", "local"):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info(" Agent Service: Database schema initialized successfully (dev mode).")
        except Exception as e:
            logger.error(f" Agent Service: Database initialization error: {e}")
    else:
        logger.info(" Agent Service: Running in production mode. Database schema managed via Alembic migrations.")
    yield


app = FastAPI(
    title=f"{settings.PROJECT_NAME} — Agent Service",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    lifespan=lifespan,
)

# Distributed Tracing Correlation ID
app.add_middleware(CorrelationIdMiddleware)

# CORS — restricted in production; gateway handles cross-origin for clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [settings.APP_ENV],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API (v1)
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat")
app.include_router(chat.router, prefix="/api/chat")

# WebSocket routers (accessed via /ws/*)
app.include_router(stream.router, prefix="/ws")
app.include_router(chat.router, prefix="/ws")


from datetime import datetime, timezone


@app.get("/")
async def root():
    return {
        "service": "agent-service",
        "name": settings.PROJECT_NAME,
        "version": "2.0.0",
        "status": "online",
        "docs": "/docs",
        "api_v1": settings.API_V1_STR,
    }


@app.get("/metrics", response_class=PlainTextResponse)
@app.get(f"{settings.API_V1_STR}/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Expose Prometheus-compatible metrics format."""
    return metrics.render_prometheus_text()


@app.get("/health")
@app.get(f"{settings.API_V1_STR}/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "agent-service",
        "version": "2.0.0",
        "project": settings.PROJECT_NAME,
        "playwright_engine": "ready",
    }
