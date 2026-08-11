"""WebSocket endpoint for AI chatbot (merged into agent-service)."""
from __future__ import annotations

import json
import logging
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.chat_repo import ChatRepository
from app.services.chat_service import stream_chat_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/chat/{chat_session_id}")
async def chat_websocket(
    websocket: WebSocket,
    chat_session_id: str,
    token: str = Query(..., description="Access token (validated by gateway before proxying)"),
    x_user_id: str = Query(default="", alias="uid", description="Injected by gateway"),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for the AI chatbot.

    The API Gateway validates the JWT and proxies the connection here,
    injecting x_user_id as a query param (uid).

    Protocol:
      Client → Server: {"message": "What endpoints did my last crawl find?"}
      Server → Client: {"type": "token", "content": "Based on..."} (streaming)
      Server → Client: {"type": "done", "session_id": "..."} (when complete)
      Server → Client: {"type": "error", "message": "..."} (on failure)
    """
    await websocket.accept()
    logger.info(f"Chatbot WS connected: user={x_user_id} session={chat_session_id}")

    chat_repo = ChatRepository(db)

    try:
        await websocket.send_json({"type": "connected", "session_id": chat_session_id})

        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
                user_message = payload.get("message", "").strip()
                crawl_context = payload.get("crawl_context")   # optional from client
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON payload."})
                continue

            if not user_message:
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
            history = [{"role": m.role, "content": m.content} for m in history_msgs[:-1]]  # exclude just-added

            # Stream LLM tokens back
            full_response = []
            async for token in stream_chat_response(history, user_message, crawl_context):
                await websocket.send_json({"type": "token", "content": token})
                full_response.append(token)

            # Persist assistant response
            assistant_content = "".join(full_response)
            await chat_repo.save_message(
                session_id=chat_session_id,
                user_id=x_user_id,
                role="assistant",
                content=assistant_content,
            )

            await websocket.send_json({"type": "done", "session_id": chat_session_id})

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
