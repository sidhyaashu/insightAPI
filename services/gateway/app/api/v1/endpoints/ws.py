"""Gateway — WebSocket reverse proxy to agent-service."""
from __future__ import annotations

import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import websockets
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/{path:path}")
async def ws_proxy(websocket: WebSocket, path: str):
    """
    Proxy WebSocket connections to agent-service.
    Auth is handled by the auth middleware before the WS upgrade.
    Both /ws/crawls/{id}/stream and /ws/chat/{session} are forwarded.
    """
    await websocket.accept()

    # Build upstream WS URL
    query_string = str(websocket.url.query)
    upstream_url = f"ws://{settings.AGENT_SERVICE_URL.replace('http://', '')}/ws/{path}"
    if query_string:
        upstream_url += f"?{query_string}"

    try:
        async with websockets.connect(upstream_url) as upstream_ws:
            async def client_to_upstream():
                try:
                    while True:
                        data = await websocket.receive_text()
                        await upstream_ws.send(data)
                except (WebSocketDisconnect, Exception):
                    pass

            async def upstream_to_client():
                try:
                    async for message in upstream_ws:
                        await websocket.send_text(message)
                except Exception:
                    pass

            await asyncio.gather(client_to_upstream(), upstream_to_client())

    except Exception as e:
        logger.error(f"WS proxy error for path={path}: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except RuntimeError:
            pass
