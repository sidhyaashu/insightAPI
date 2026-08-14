"""WebSocket & REST endpoint for AI chatbot with subscription tier quota enforcement."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import base64

from app.core.database import get_db
from app.core.config import settings
from app.core.redis import get_redis_client
from app.repositories.chat_repo import ChatRepository
from app.services.chat_service import stream_chat_response

logger = logging.getLogger(__name__)
router = APIRouter()


def decode_jwt_token(token: str) -> dict:
    """Safely decode JWT payload with jose, pyjwt, or standard base64 fallback."""
    if not token:
        return {}

    # 1. Try python-jose
    try:
        from jose import jwt
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except Exception:
        pass

    # 2. Try pyjwt
    try:
        import jwt as pyjwt
        return pyjwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except Exception:
        pass

    # 3. Base64 URL-safe JSON decode fallback (validated upstream by API gateway)
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            payload_b64 = parts[1]
            padding = len(payload_b64) % 4
            if padding:
                payload_b64 += "=" * (4 - padding)
            payload_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
            return json.loads(payload_json)
    except Exception as e:
        logger.debug(f"JWT decode error: {e}")

    return {}


async def get_user_chat_quota(user_id: str, tier: str) -> dict:
    """Return user's daily chat message quota status."""
    tier_upper = (tier or "FREE").upper()
    limit = settings.get_tier_chat_limit(tier_upper)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = settings.get_redis_key(f"chat:daily:{user_id}:{today}")

    used = 0
    try:
        redis = await get_redis_client()
        val = await redis.get(key)
        used = int(val) if val else 0
    except Exception as e:
        logger.warning(f"Failed to read chat quota from Redis: {e}")

    remaining = max(0, limit - used)
    is_exceeded = used >= limit

    return {
        "user_id": user_id,
        "tier": tier_upper,
        "limit": limit,
        "used": used,
        "remaining": remaining,
        "is_exceeded": is_exceeded,
        "reset_period": "daily",
    }


async def increment_user_chat_quota(user_id: str) -> int:
    """Increment user's daily message count."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = settings.get_redis_key(f"chat:daily:{user_id}:{today}")
    try:
        redis = await get_redis_client()
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 86400 * 2)  # 2 days TTL
        res = await pipe.execute()
        return int(res[0])
    except Exception as e:
        logger.warning(f"Failed to increment chat quota in Redis: {e}")
        return 1


@router.get("/quota")
@router.get("/chat/quota")
async def get_chat_quota_endpoint(
    token: str | None = Query(default=None),
    x_user_id: str | None = Header(default=None),
    x_user_tier: str | None = Header(default=None),
):
    """Return the current user's message quota based on their subscription tier."""
    user_id = x_user_id or ""
    user_tier = x_user_tier or "FREE"

    if token:
        payload = decode_jwt_token(token)
        user_id = payload.get("sub", user_id)
        user_tier = payload.get("tier", user_tier)

    if not user_id:
        return {
            "user_id": "anonymous",
            "tier": "FREE",
            "limit": settings.TIER_CHAT_LIMIT_FREE,
            "used": 0,
            "remaining": settings.TIER_CHAT_LIMIT_FREE,
            "is_exceeded": False,
            "reset_period": "daily",
        }

    return await get_user_chat_quota(user_id, user_tier)


@router.websocket("/chat/{chat_session_id}")
async def chat_websocket(
    websocket: WebSocket,
    chat_session_id: str,
    token: str = Query(..., description="Access token (validated by gateway before proxying)"),
    x_user_id: str = Query(default="", alias="uid", description="Injected by gateway"),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for the AI chatbot with real-time tier quota enforcement.

    Protocol:
      Client → Server: {"message": "Hello!"}
      Server → Client: {"type": "token", "content": "..."} (streaming)
      Server → Client: {"type": "done", "session_id": "...", "quota": {...}} (when complete)
      Server → Client: {"type": "quota_exceeded", "message": "...", "quota": {...}} (if limit reached)
      Server → Client: {"type": "error", "message": "..."} (on failure)
    """
    user_tier = "FREE"
    if token:
        payload = decode_jwt_token(token)
        x_user_id = payload.get("sub", x_user_id)
        user_tier = payload.get("tier", "FREE").upper()

    await websocket.accept()
    logger.info(f"Chatbot WS connected: user={x_user_id} tier={user_tier} session={chat_session_id}")

    chat_repo = ChatRepository(db)

    try:
        quota = await get_user_chat_quota(x_user_id, user_tier)
        await websocket.send_json({
            "type": "connected",
            "session_id": chat_session_id,
            "quota": quota,
        })

        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
                user_message = payload.get("message", "").strip()
                crawl_context = payload.get("crawl_context")
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON payload."})
                continue

            if not user_message:
                continue

            # Check subscription tier quota before processing
            quota = await get_user_chat_quota(x_user_id, user_tier)
            if quota["is_exceeded"]:
                await websocket.send_json({
                    "type": "quota_exceeded",
                    "message": (
                        f"You have reached your daily quota of {quota['limit']} messages on the {user_tier} plan. "
                        f"Upgrade to PRO or ENTERPRISE for higher or unlimited limits."
                    ),
                    "quota": quota,
                })
                continue

            # Persist user message
            await chat_repo.save_message(
                session_id=chat_session_id,
                user_id=x_user_id,
                role="user",
                content=user_message,
            )

            # Load history for context
            history_msgs = await chat_repo.get_history(chat_session_id, limit=40)
            history = [{"role": m.role, "content": m.content} for m in history_msgs[:-1]]

            # Stream LLM tokens back
            full_response = []
            async for token_text in stream_chat_response(history, user_message, crawl_context):
                await websocket.send_json({"type": "token", "content": token_text})
                full_response.append(token_text)

            # Persist assistant response
            assistant_content = "".join(full_response)
            await chat_repo.save_message(
                session_id=chat_session_id,
                user_id=x_user_id,
                role="assistant",
                content=assistant_content,
            )

            # Increment quota count and broadcast updated quota
            new_used = await increment_user_chat_quota(x_user_id)
            updated_quota = {
                **quota,
                "used": new_used,
                "remaining": max(0, quota["limit"] - new_used),
                "is_exceeded": new_used >= quota["limit"],
            }

            await websocket.send_json({
                "type": "done",
                "session_id": chat_session_id,
                "quota": updated_quota,
            })

    except WebSocketDisconnect:
        logger.info(f"Chatbot WS disconnected: user={x_user_id} session={chat_session_id}")
    except Exception as e:
        logger.error(f"Chatbot WS error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except RuntimeError:
            pass
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass
