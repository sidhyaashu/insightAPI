"""Core Service — Users router: profile and internal user lookup."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Header
from app.core.database import get_db
from app.repositories.user_repo import UserRepository
import contextlib

router = APIRouter(prefix="/users", tags=["Users"])


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
            "created_at": user.created_at.isoformat(),
        }
