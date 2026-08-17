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

    async def cache_user_session(self, user_id: str, tier: str, allow_overage: bool = False) -> None:
        """Cache user tier & overage setting in Redis — read by gateway for fast x-user-id injection."""
        redis = await get_redis_client()
        ttl = int(timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES + 5).total_seconds())
        await redis.hset(
            f"user:session:{user_id}",
            mapping={
                "tier": tier,
                "allow_overage": "true" if allow_overage else "false",
            },
        )
        await redis.expire(f"user:session:{user_id}", ttl)

    async def get_user_session(self, user_id: str) -> dict | None:
        redis = await get_redis_client()
        data = await redis.hgetall(f"user:session:{user_id}")
        return data if data else None

    async def store_oauth_state(self, provider: str, ttl_seconds: int = 600) -> str:
        """Generate and persist a cryptographically random OAuth state token in Redis."""
        import secrets
        state = secrets.token_urlsafe(32)
        redis = await get_redis_client()
        await redis.set(f"oauth:state:{state}", provider, ex=ttl_seconds)
        return state

    async def verify_and_consume_oauth_state(self, state: str, provider: str) -> bool:
        """Verify the state token matches the expected provider and delete it (single-use)."""
        if not state:
            return False
        redis = await get_redis_client()
        key = f"oauth:state:{state}"
        stored = await redis.get(key)
        if not stored:
            return False
        if isinstance(stored, bytes):
            stored = stored.decode("utf-8")
        if stored != provider:
            return False
        await redis.delete(key)
        return True
