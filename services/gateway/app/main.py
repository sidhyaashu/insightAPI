"""Gateway Service — FastAPI entry point with auth middleware and standardized app/api/v1 architecture."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.middleware.auth import auth_middleware
from app.api.v1.router import api_router
from datetime import datetime, timezone

app = FastAPI(
    title="InsightAPI AI — Gateway",
    docs_url="/docs" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import uuid
from starlette.requests import Request
from starlette.responses import Response

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

# JWT auth middleware — validates tokens and injects x-user-id / x-user-tier
app.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)

# Standardized v1 API Router (handles WebSocket and REST proxy)
app.include_router(api_router)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "gateway",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
