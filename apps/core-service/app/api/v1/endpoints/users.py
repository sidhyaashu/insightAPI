"""Core Service — Users router: profile and internal user lookup."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Header
from app.core.database import get_db
from app.repositories.user_repo import UserRepository
import contextlib

from pydantic import BaseModel
from typing import Optional
from app.repositories.session_repo import SessionRepository

router = APIRouter(prefix="/users", tags=["Users"])


class UserPreferencesUpdate(BaseModel):
    allow_overage: Optional[bool] = None


@router.get("/me")
async def get_current_user(x_user_id: str = Header(...)):
    """Return the profile of the authenticated user (x-user-id injected by gateway)."""
    async with contextlib.asynccontextmanager(get_db)() as db:
        repo = UserRepository(db)
        user = await repo.get_by_id(x_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "tier": user.tier,
            "oauth_provider": user.oauth_provider,
            "allow_overage": user.allow_overage,
            "created_at": user.created_at.isoformat(),
        }


@router.patch("/me/preferences")
async def update_user_preferences(
    body: UserPreferencesUpdate,
    x_user_id: str = Header(...),
):
    """Update user billing and execution preferences (e.g. allow pay-per-crawl overage)."""
    async with contextlib.asynccontextmanager(get_db)() as db:
        repo = UserRepository(db)
        user = await repo.get_by_id(x_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        if body.allow_overage is not None:
            user = await repo.update_overage_preference(x_user_id, body.allow_overage)
            # Re-cache in Redis for gateway and agents
            session_repo = SessionRepository()
            await session_repo.cache_user_session(
                user_id=x_user_id,
                tier=user.tier,
                allow_overage=user.allow_overage,
            )

        return {
            "id": user.id,
            "tier": user.tier,
            "allow_overage": user.allow_overage,
            "message": "Preferences updated successfully.",
        }

