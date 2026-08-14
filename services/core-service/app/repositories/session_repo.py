"""Core Service — SessionRepository: Redis-backed refresh token store."""
from __future__ import annotations

from datetime import timedelta
from app.core.redis import get_redis_client
from app.core.config import settings


class SessionRepository:
    """
    Stores refresh token JTIs in Redis.
    Key pattern: session:refresh:{user_id}:{jti}  (TTL = REFRESH_TOKEN_EXPIRE_DAYS)
    Also caches user session info for gateway lookup:
    Key pattern: user:session:{user_id} → {"tier": "PRO"}
    """

    async def store_refresh_token(self, user_id: str, jti: str) -> None:
        redis = await get_redis_client()
        ttl = int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds())
        await redis.set(f"session:refresh:{user_id}:{jti}", "1", ex=ttl)

    async def is_refresh_token_valid(self, user_id: str, jti: str) -> bool:
        redis = await get_redis_client()
        return bool(await redis.exists(f"session:refresh:{user_id}:{jti}"))

    async def revoke_refresh_token(self, user_id: str, jti: str) -> None:
        redis = await get_redis_client()
        await redis.delete(f"session:refresh:{user_id}:{jti}")

    async def revoke_all_sessions(self, user_id: str) -> None:
        """Revoke all refresh tokens for a user (e.g. on password reset / account compromise)."""
        redis = await get_redis_client()
        pattern = f"session:refresh:{user_id}:*"
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)

    async def cache_user_session(self, user_id: str, tier: str) -> None:
        """Cache user tier in Redis — read by gateway for fast x-user-id injection."""
        redis = await get_redis_client()
        ttl = int(timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES + 5).total_seconds())
        await redis.hset(f"user:session:{user_id}", mapping={"tier": tier})
        await redis.expire(f"user:session:{user_id}", ttl)

    async def get_user_session(self, user_id: str) -> dict | None:
        redis = await get_redis_client()
        data = await redis.hgetall(f"user:session:{user_id}")
        return data if data else None
