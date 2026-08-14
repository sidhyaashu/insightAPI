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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database schema is created on startup."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(" Core Service: Database schema initialized successfully.")
    except Exception as e:
        logger.error(f" Core Service: Database initialization error: {e}")
    yield


app = FastAPI(
    title=f"{settings.APP_NAME} — Core Service",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs" if settings.DEBUG else None,
    lifespan=lifespan,
)

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
