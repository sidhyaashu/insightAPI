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
from app.models.crawl_snapshot import CrawlSnapshot  # noqa: F401 — registers crawl_snapshots table

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure agent service database schema is created on startup."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(" Agent Service: Database schema initialized successfully.")
    except Exception as e:
        logger.error(f" Agent Service: Database initialization error: {e}")
    yield


app = FastAPI(
    title=f"{settings.PROJECT_NAME} — Agent Service",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    lifespan=lifespan,
)

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


@app.get("/health")
@app.get(f"{settings.API_V1_STR}/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "agent-service",
        "version": "2.0.0",
        "project": settings.PROJECT_NAME,
        "playwright_engine": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
