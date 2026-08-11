"""Core Service — FastAPI application entry point with standardized app/api/v1 architecture."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from datetime import datetime, timezone

app = FastAPI(
    title=f"{settings.APP_NAME} — Core Service",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [settings.APP_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API v1 Router (Standard Versioned Prefix: /api/v1) ──────────────────────
app.include_router(api_router, prefix=settings.API_V1_STR)

# ── Unversioned Router (Backward Compatibility for /auth/*, /users/*) ───────
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
