"""Core Service — Token service: issue, refresh, and revoke JWT token pairs."""
from __future__ import annotations

import logging
from jose import JWTError
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.repositories.session_repo import SessionRepository

logger = logging.getLogger(__name__)


class TokenService:
    def __init__(self, session_repo: SessionRepository):
        self.session_repo = session_repo

    async def issue_token_pair(self, user_id: str, tier: str, role: str = "user") -> dict:
        """Issue access + refresh token pair and cache session in Redis."""
        access_token = create_access_token(user_id, tier, role)
        refresh_token, refresh_jti = create_refresh_token(user_id)

        await self.session_repo.store_refresh_token(user_id, refresh_jti)
        await self.session_repo.cache_user_session(user_id, tier)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def rotate_tokens(self, refresh_token: str, user_tier: str, user_role: str = "user") -> dict:
        """
        Validate the incoming refresh token, revoke it, and issue a fresh pair.
        Implements refresh token rotation — each refresh token is single-use.
        """
        try:
            payload = decode_token(refresh_token)
        except JWTError as e:
            raise ValueError(f"Invalid refresh token: {e}")

        if payload.get("type") != "refresh":
            raise ValueError("Token is not a refresh token.")

        user_id = payload["sub"]
        jti = payload["jti"]

        if not await self.session_repo.is_refresh_token_valid(user_id, jti):
            # Token reuse detected — revoke all sessions (possible compromise)
            await self.session_repo.revoke_all_sessions(user_id)
            raise ValueError("Refresh token already used or revoked. All sessions invalidated.")

        # Single-use: revoke old token before issuing new pair
        await self.session_repo.revoke_refresh_token(user_id, jti)
        return await self.issue_token_pair(user_id, user_tier, user_role)

    async def revoke_session(self, refresh_token: str) -> None:
        """Revoke a specific refresh token (logout)."""
        try:
            payload = decode_token(refresh_token)
            user_id = payload["sub"]
            jti = payload["jti"]
            await self.session_repo.revoke_refresh_token(user_id, jti)
        except JWTError:
            pass   # Already invalid — ignore
