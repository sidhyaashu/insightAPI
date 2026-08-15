"""Gateway — JWT auth middleware: validates token and injects x-user-id, x-user-tier, and x-user-role headers."""
from __future__ import annotations

import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from app.core.config import settings
from app.core.constants import (
    PUBLIC_PATHS, HEADER_USER_ID, HEADER_USER_TIER, HEADER_USER_ROLE, HEADER_USER_ALLOW_OVERAGE,
    is_admin_email
)
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.get_redis_url(), decode_responses=True)
    return _redis


async def auth_middleware(request: Request, call_next):
    """
    Validates the Bearer JWT from the Authorization header or ?token= query param.
    On success: injects X-User-Id, X-User-Tier, and X-User-Role headers for downstream services.
    Public routes bypass this check.
    """
    path = request.url.path

    # Allow public paths without auth
    if (
        path in PUBLIC_PATHS
        or path.startswith("/docs")
        or path.startswith("/openapi.json")
        or path.startswith("/api/v1/auth/")
        or path.startswith("/api/auth/")
    ):
        return await call_next(request)

    # Extract token from HttpOnly cookie `access_token`, Authorization header, or query param
    token = request.cookies.get("access_token")

    if not token:
        if request.headers.get("upgrade", "").lower() == "websocket":
            token = request.query_params.get("token")
        else:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()

    if not token:
        return JSONResponse(status_code=401, content={"detail": "Missing authentication token."})

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        return JSONResponse(status_code=401, content={"detail": f"Invalid token: {e}"})

    user_id: str = payload.get("sub", "")
    email: str = payload.get("email", "")
    tier: str = payload.get("tier", "FREE")
    role: str = payload.get("role", "user")
    allow_overage: str = "false"

    if not user_id:
        return JSONResponse(status_code=401, content={"detail": "Token missing sub claim."})

    if is_admin_email(email) or is_admin_email(user_id):
        tier = "ADMIN"
        role = "admin"

    # Try Redis cache for tier & overage updates
    try:
        redis = await get_redis()
        cached = await redis.hgetall(f"user:session:{user_id}")
        if cached and "tier" in cached and not is_admin_email(email) and not is_admin_email(user_id):
            tier = cached["tier"]
        if cached and "allow_overage" in cached:
            allow_overage = cached["allow_overage"]
    except Exception:
        pass

    # Inject headers into request scope
    request.state.user_id = user_id
    request.state.user_tier = tier
    request.state.user_role = role
    request.state.allow_overage = allow_overage

    headers = dict(request.headers)
    headers[HEADER_USER_ID] = user_id
    headers[HEADER_USER_TIER] = tier
    headers[HEADER_USER_ROLE] = role
    headers[HEADER_USER_ALLOW_OVERAGE] = allow_overage

    scope = request.scope
    scope["headers"] = [
        (k.encode(), v.encode()) for k, v in headers.items()
    ]

    return await call_next(request)
