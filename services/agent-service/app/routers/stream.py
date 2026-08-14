"""WebSocket endpoint for real-time crawl log streaming."""
from __future__ import annotations

import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/crawls/{session_id}/stream")
async def stream_crawl_events(
    websocket: WebSocket,
    session_id: str,
    token: str | None = Query(default=None, description="Access token for authentication (validated by gateway)"),
):
    """
    WebSocket endpoint that streams crawl log events for a given session.

    Events are published to Redis PubSub channel `crawl:{session_id}:events`
    by the background crawl task, and forwarded here to the browser.

    Message format:
        {"type": "log", "message": "...", "page": 3, "endpoints_found": 12}
        {"type": "complete", "captured_count": 47}
        {"type": "error", "message": "..."}
    """
    from app.core.redis import get_redis_client

    await websocket.accept()
    logger.info(f"WS crawl stream connected: session={session_id}")

    redis = await get_redis_client()
    pubsub = redis.pubsub()
    channel = f"crawl:{session_id}:events"

    try:
        await pubsub.subscribe(channel)
        await websocket.send_json({"type": "connected", "session_id": session_id})

        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
                await websocket.send_json(data)

                # Stop streaming when crawl completes or errors
                if data.get("type") in ("complete", "error"):
                    break
            except (json.JSONDecodeError, RuntimeError):
                break

    except WebSocketDisconnect:
        logger.info(f"WS crawl stream disconnected: session={session_id}")
    except Exception as e:
        logger.error(f"WS crawl stream error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except RuntimeError:
            pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        try:
            await websocket.close()
        except RuntimeError:
            pass
