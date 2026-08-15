import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.router import api_router
from datetime import datetime, timezone

# Ensure all SQLAlchemy models are registered on Base.metadata
from app.models.user import User
from app.models.subscription import Subscription

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database schema is initialized safely on startup."""
    if settings.DEBUG or getattr(settings, "APP_ENV", "development") in ("development", "test", "local"):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info(" Core Service: Database schema initialized successfully (dev mode).")
        except Exception as e:
            logger.error(f" Core Service: Database initialization error: {e}")
    else:
        logger.info(" Core Service: Running in production mode. Database managed via Alembic migrations.")
    yield


app = FastAPI(
    title=f"{settings.APP_NAME} — Core Service",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs" if settings.DEBUG else None,
    lifespan=lifespan,
)

async def correlation_id_middleware(request: Request, call_next) -> Response:
    corr_id = (
        request.headers.get("X-Correlation-ID")
        or request.headers.get("X-Request-ID")
        or str(uuid.uuid4())
    )
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = corr_id
    return response

app.add_middleware(BaseHTTPMiddleware, dispatch=correlation_id_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [settings.APP_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers (/api/v1, /api, and root) ────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(api_router, prefix="/api")
app.include_router(api_router)


@app.get("/health")
@app.get(f"{settings.API_V1_STR}/health")
async def health():
    return {
        "status": "healthy",
        "service": "core-service",
        "version": "2.0.0",
        "api_v1": settings.API_V1_STR,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
