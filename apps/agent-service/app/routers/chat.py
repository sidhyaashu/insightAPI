"""WebSocket & REST endpoints for AI chatbot with DB-first session lifecycle."""
from __future__ import annotations

import json
import logging
import uuid
import base64
from datetime import datetime, timezone
from fastapi import (
    APIRouter, WebSocket, WebSocketDisconnect,
    Query, Depends, Header, HTTPException, status,
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.redis import get_redis_client
from app.repositories.chat_repo import ChatRepository
from app.services.chat_service import stream_chat_response

logger = logging.getLogger(__name__)
router = APIRouter()


# ── JWT helpers ────────────────────────────────────────────────────────────────

def decode_jwt_token(token: str) -> dict:
    """Safely decode JWT payload with jose, pyjwt, or standard base64 fallback."""
    if not token:
        return {}

    try:
        from jose import jwt
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except Exception:
        pass

    try:
        import jwt as pyjwt
        return pyjwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except Exception:
        pass

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


def _resolve_user(
    token: str | None,
    x_user_id: str | None,
    x_user_tier: str | None,
) -> tuple[str, str]:
    """Return (user_id, user_tier) from JWT token or header fallbacks.

    Admin email elevation: if the JWT contains an email (or 'sub' that looks
    like an email) matching settings.ADMIN_EMAILS, the tier is forced to ADMIN
    regardless of what the token claims.
    """
    user_id = x_user_id or ""
    user_tier = (x_user_tier or "FREE").upper()

    if token:
        payload = decode_jwt_token(token)
        user_id = payload.get("sub", user_id)
        user_tier = payload.get("tier", user_tier).upper()

        # Admin email elevation — check both 'email' claim and 'sub' (some
        # OAuth providers embed the email address directly in 'sub').
        jwt_email = payload.get("email") or (
            payload.get("sub", "") if "@" in (payload.get("sub") or "") else None
        )
        if settings.is_admin_email(jwt_email):
            user_tier = "ADMIN"
            logger.info(f"Admin email elevation applied for: {jwt_email}")

    return user_id, user_tier


# ── Quota helpers ──────────────────────────────────────────────────────────────

async def get_user_chat_quota(user_id: str, tier: str) -> dict:
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
    return {
        "user_id": user_id,
        "tier": tier_upper,
        "limit": limit,
        "used": used,
        "remaining": remaining,
        "is_exceeded": used >= limit,
        "reset_period": "daily",
    }


async def increment_user_chat_quota(user_id: str) -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = settings.get_redis_key(f"chat:daily:{user_id}:{today}")
    try:
        redis = await get_redis_client()
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 86400 * 2)
        res = await pipe.execute()
        return int(res[0])
    except Exception as e:
        logger.warning(f"Failed to increment chat quota in Redis: {e}")
        return 1


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    title: str = "New Conversation"


class UpdateSessionRequest(BaseModel):
    title: str


class ChatSessionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    is_archived: bool
    created_at: str
    updated_at: str
    message_count: int = 0


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: str


class SessionWithMessagesResponse(BaseModel):
    session: ChatSessionResponse
    messages: list[ChatMessageResponse]


# ── REST: Quota ────────────────────────────────────────────────────────────────

@router.get("/quota")
@router.get("/chat/quota")
async def get_chat_quota_endpoint(
    token: str | None = Query(default=None),
    x_user_id: str | None = Header(default=None),
    x_user_tier: str | None = Header(default=None),
):
    """Return the current user's message quota based on their subscription tier."""
    user_id, user_tier = _resolve_user(token, x_user_id, x_user_tier)

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


# ── REST: Chat Sessions CRUD ───────────────────────────────────────────────────

@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
@router.post("/chat/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    body: CreateSessionRequest,
    token: str | None = Query(default=None),
    x_user_id: str | None = Header(default=None),
    x_user_tier: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Create a new DB-persisted chat session. Returns the session with a server-generated UUID."""
    user_id, _ = _resolve_user(token, x_user_id, x_user_tier)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    chat_repo = ChatRepository(db)
    session = await chat_repo.create_session(user_id=user_id, title=body.title)
    return {**session.to_dict(), "message_count": 0}


@router.get("/sessions", response_model=list[ChatSessionResponse])
@router.get("/chat/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    token: str | None = Query(default=None),
    x_user_id: str | None = Header(default=None),
    x_user_tier: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """List all active chat sessions for the authenticated user."""
    user_id, _ = _resolve_user(token, x_user_id, x_user_tier)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    chat_repo = ChatRepository(db)
    sessions = await chat_repo.list_sessions(user_id, limit=limit, offset=offset)

    result = []
    for s in sessions:
        count = await chat_repo.get_message_count(s.id)
        result.append({**s.to_dict(), "message_count": count})
    return result


@router.get("/sessions/{session_id}", response_model=SessionWithMessagesResponse)
@router.get("/chat/sessions/{session_id}", response_model=SessionWithMessagesResponse)
async def get_session(
    session_id: str,
    token: str | None = Query(default=None),
    x_user_id: str | None = Header(default=None),
    x_user_tier: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single session with its full message history (for page reload / history resume)."""
    user_id, _ = _resolve_user(token, x_user_id, x_user_tier)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    chat_repo = ChatRepository(db)
    session = await chat_repo.get_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    messages = await chat_repo.get_history(session_id, limit=200)
    msg_count = len(messages)

    return {
        "session": {**session.to_dict(), "message_count": msg_count},
        "messages": [
            {
                "id": m.id,
                "session_id": m.session_id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
@router.patch("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: str,
    body: UpdateSessionRequest,
    token: str | None = Query(default=None),
    x_user_id: str | None = Header(default=None),
    x_user_tier: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Update session title."""
    user_id, _ = _resolve_user(token, x_user_id, x_user_tier)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    chat_repo = ChatRepository(db)
    updated = await chat_repo.update_session_title(session_id, user_id, body.title.strip() or "Untitled")
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    session = await chat_repo.get_session(session_id, user_id)
    count = await chat_repo.get_message_count(session_id)
    return {**session.to_dict(), "message_count": count}


@router.delete("/sessions/{session_id}", status_code=204)
@router.delete("/chat/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    token: str | None = Query(default=None),
    x_user_id: str | None = Header(default=None),
    x_user_tier: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete (archive) a session. Returns 204 No Content."""
    user_id, _ = _resolve_user(token, x_user_id, x_user_tier)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    chat_repo = ChatRepository(db)
    archived = await chat_repo.archive_session(session_id, user_id)
    if not archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")


# ── WebSocket: Chat stream ─────────────────────────────────────────────────────

@router.websocket("/chat/{chat_session_id}")
async def chat_websocket(
    websocket: WebSocket,
    chat_session_id: str,
    token: str | None = Query(default=None, description="Access token"),
    x_user_id: str = Query(default="", alias="uid", description="Injected by gateway"),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for AI chatbot with real-time tier quota enforcement.

    Protocol:
      Client → Server: {"message": "Hello!", "model": "gpt-4o-mini"}
      Server → Client: {"type": "connected", "session_id": "...", "quota": {...}}
      Server → Client: {"type": "token", "content": "..."}         (streaming tokens)
      Server → Client: {"type": "done", "session_id": "...", "quota": {...}}
      Server → Client: {"type": "quota_exceeded", "message": "...", "quota": {...}}
      Server → Client: {"type": "error", "message": "..."}
    """
    auth_token = (
        token
        or websocket.cookies.get("access_token")
        or websocket.headers.get("x-access-token")
    )
    user_tier = "FREE"
    if auth_token:
        payload = decode_jwt_token(auth_token)
        x_user_id = payload.get("sub", x_user_id)
        user_tier = payload.get("tier", "FREE").upper()

        # Admin email elevation — same logic as _resolve_user()
        jwt_email = payload.get("email") or (
            payload.get("sub", "") if "@" in (payload.get("sub") or "") else None
        )
        if settings.is_admin_email(jwt_email):
            user_tier = "ADMIN"
            logger.info(f"[WS] Admin email elevation applied for: {jwt_email}")

    await websocket.accept()
    logger.info(f"Chatbot WS connected: user={x_user_id} tier={user_tier} session={chat_session_id}")

    chat_repo = ChatRepository(db)

    # Verify session ownership (DB-first sessions only; legacy IDs are tolerated but not validated)
    # A session that starts with "chat-" is a legacy localStorage-generated ID — allow it through.
    is_legacy_id = chat_session_id.startswith("chat-")
    if not is_legacy_id and x_user_id:
        db_session = await chat_repo.get_session(chat_session_id, x_user_id)
        if not db_session:
            # Session doesn't belong to this user or doesn't exist
            await websocket.send_json({
                "type": "error",
                "message": "Session not found or access denied.",
            })
            await websocket.close(code=4403)
            return

    try:
        quota = await get_user_chat_quota(x_user_id, user_tier)
        await websocket.send_json({
            "type": "connected",
            "session_id": chat_session_id,
            "quota": quota,
        })

        is_first_message = (await chat_repo.get_message_count(chat_session_id)) == 0

        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
                user_message = payload.get("message", "").strip()
                crawl_context = payload.get("crawl_context")
                requested_model = payload.get("model")
                auth_profile_id = payload.get("auth_profile_id")
                approved_actions = payload.get("approved_actions", [])
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON payload."})
                continue

            if not user_message:
                continue

            # Check quota
            quota = await get_user_chat_quota(x_user_id, user_tier)
            if quota["is_exceeded"]:
                await websocket.send_json({
                    "type": "quota_exceeded",
                    "message": (
                        f"You have reached your daily quota of {quota['limit']} messages "
                        f"on the {user_tier} plan. Upgrade for higher or unlimited limits."
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

            # Auto-set session title from first message (DB sessions only)
            if is_first_message and not is_legacy_id and x_user_id:
                auto_title = user_message[:60].strip()
                if len(user_message) > 60:
                    auto_title += "..."
                await chat_repo.update_session_title(chat_session_id, x_user_id, auto_title)
                await websocket.send_json({
                    "type": "title",
                    "session_id": chat_session_id,
                    "title": auto_title,
                })
                is_first_message = False

            # Touch session updated_at so sidebar list stays sorted
            if not is_legacy_id:
                await chat_repo.touch_session(chat_session_id)

            # Load history for context
            history_msgs = await chat_repo.get_history(chat_session_id, limit=40)
            history = [{"role": m.role, "content": m.content} for m in history_msgs[:-1]]

            # Resolve Auth Profile credentials if present
            auth_headers = {}
            if x_user_id and db:
                from app.tools.auth_vault import resolve_auth_headers
                auth_headers = await resolve_auth_headers(
                    user_id=x_user_id,
                    domain_or_url=user_message,
                    auth_profile_id=auth_profile_id,
                    db=db,
                )

            # Stream Agentic events (tool_start, tool_result, approval_required, token)
            from app.services.chat_service import stream_agentic_chat
            full_response: list[str] = []
            async for event in stream_agentic_chat(
                history=history,
                user_message=user_message,
                crawl_context=crawl_context,
                model=requested_model,
                auth_headers=auth_headers,
                approved_actions=approved_actions,
                session_id=chat_session_id,
            ):
                await websocket.send_json(event)
                if event.get("type") == "token":
                    full_response.append(event.get("content", ""))

            # Persist assistant response
            assistant_content = "".join(full_response)
            await chat_repo.save_message(
                session_id=chat_session_id,
                user_id=x_user_id,
                role="assistant",
                content=assistant_content,
            )

            # Increment quota and broadcast updated values
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
