"""Core Service — API Key CRUD endpoints for Python SDK & CLI authentication."""
import secrets
import hashlib
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db
from app.models.apikey import APIKey
from app.models.user import User

router = APIRouter()


class CreateAPIKeyRequest(BaseModel):
    name: str = "SDK / CLI Access Key"


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    created_at: str
    raw_key: str | None = None  # Returned only once upon generation


async def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required X-User-ID authentication header.",
        )
    return x_user_id


@router.post("/users/me/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    req: CreateAPIKeyRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new SHA-256 hashed API key for SDK/CLI use."""
    token = secrets.token_hex(20)
    raw_key = f"insightapi_live_sk_{token}"
    prefix = raw_key[:16]
    hashed_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    key_record = APIKey(
        user_id=user_id,
        name=req.name,
        key_prefix=prefix,
        hashed_key=hashed_key,
    )
    db.add(key_record)
    await db.commit()
    await db.refresh(key_record)

    return APIKeyResponse(
        id=key_record.id,
        name=key_record.name,
        key_prefix=key_record.key_prefix,
        created_at=key_record.created_at.isoformat(),
        raw_key=raw_key,
    )


@router.get("/users/me/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all active API keys for the current user."""
    stmt = select(APIKey).where(APIKey.user_id == user_id).order_by(APIKey.created_at.desc())
    result = await db.execute(stmt)
    keys = result.scalars().all()

    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            created_at=k.created_at.isoformat(),
            raw_key=None,
        )
        for k in keys
    ]


@router.delete("/users/me/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key by ID."""
    stmt = delete(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id)
    await db.execute(stmt)
    await db.commit()
    return None
