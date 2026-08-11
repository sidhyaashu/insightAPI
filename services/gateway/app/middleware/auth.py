"""Gateway — JWT auth middleware: validates token and injects x-user-id, x-user-tier, and x-user-role headers."""
from __future__ import annotations

import logging
from fastapi import Request, HTTPException
from jose import jwt, JWTError
from app.core.config import settings
from app.core.constants import (
    PUBLIC_PATHS, HEADER_USER_ID, HEADER_USER_TIER, HEADER_USER_ROLE
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
    if path in PUBLIC_PATHS or path.startswith("/docs"):
        return await call_next(request)

    # WebSocket auth via query param `?token=`
    token = None
    if request.headers.get("upgrade", "").lower() == "websocket":
        token = request.query_params.get("token")
    else:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token.")

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    user_id: str = payload.get("sub", "")
    tier: str = payload.get("tier", "FREE")
    role: str = payload.get("role", "user")

    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub claim.")

    # Try Redis cache for tier updates
    try:
        redis = await get_redis()
        cached = await redis.hgetall(f"user:session:{user_id}")
        if cached and "tier" in cached:
            tier = cached["tier"]
    except Exception:
        pass

    # Inject headers into request scope
    request.state.user_id = user_id
    request.state.user_tier = tier
    request.state.user_role = role

    headers = dict(request.headers)
    headers[HEADER_USER_ID] = user_id
    headers[HEADER_USER_TIER] = tier
    headers[HEADER_USER_ROLE] = role

    scope = request.scope
    scope["headers"] = [
        (k.encode(), v.encode()) for k, v in headers.items()
    ]

    return await call_next(request)
