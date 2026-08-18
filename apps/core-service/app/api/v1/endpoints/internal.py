"""Core Service — Internal router for inter-service communication (not exposed publicly)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from app.core.config import settings
from app.core.database import get_db
from app.repositories.user_repo import UserRepository
from app.repositories.session_repo import SessionRepository
import contextlib

router = APIRouter(prefix="/internal", tags=["Internal"])

TIER_LEVELS = {"FREE": 0, "STARTER": 1, "PRO": 2, "ENTERPRISE": 3}


def _verify_gateway(
    x_gateway_secret: str = Header(...),
    x_user_id: str | None = Header(default=None),
    target_user_id: str | None = None,
):
    if not settings.GATEWAY_SECRET or x_gateway_secret != settings.GATEWAY_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized internal request.")
    # Defense-in-depth: if an end-user header is forwarded, ensure it matches target_user_id
    if x_user_id and target_user_id and x_user_id != target_user_id:
        raise HTTPException(status_code=403, detail="Cross-user internal session query forbidden.")


@router.get("/users/{user_id}/session")
async def get_user_session(
    user_id: str,
    x_gateway_secret: str = Header(...),
    x_user_id: str | None = Header(default=None),
):
    """
    Called by gateway to retrieve cached user tier for x-user-id injection.
    Returns {"tier": "PRO"} or 404.
    """
    _verify_gateway(x_gateway_secret=x_gateway_secret, x_user_id=x_user_id, target_user_id=user_id)
    repo = SessionRepository()
    session = await repo.get_user_session(user_id)
    if not session:
        # Fallback: look up directly in DB
        async with contextlib.asynccontextmanager(get_db)() as db:
            user_repo = UserRepository(db)
            user = await user_repo.get_by_id(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found.")
            # Re-cache
            await repo.cache_user_session(user_id, user.tier)
            return {"tier": user.tier}
    return session


@router.patch("/users/{user_id}/tier")
async def update_user_tier(user_id: str, tier: str, x_gateway_secret: str = Header(...)):
    """Called by payment webhook to update user tier after Stripe subscription change."""
    _verify_gateway(x_gateway_secret)
    if tier not in TIER_LEVELS:
        raise HTTPException(status_code=400, detail=f"Unknown tier: {tier}")
    async with contextlib.asynccontextmanager(get_db)() as db:
        user_repo = UserRepository(db)
        await user_repo.update_tier(user_id, tier)
        # Invalidate Redis cache so gateway picks up new tier immediately
        repo = SessionRepository()
        await repo.cache_user_session(user_id, tier)
    return {"message": f"User {user_id} tier updated to {tier}."}
