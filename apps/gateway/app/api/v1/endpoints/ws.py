"""Gateway — WebSocket reverse proxy to agent-service."""
from __future__ import annotations

import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import websockets
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def build_upstream_ws_url(agent_service_url: str, path: str, query_string: str = "") -> str:
    """Properly construct upstream WebSocket URL handling both http:// and https:// schemes."""
    clean_path = path.lstrip("/")
    if clean_path.startswith("ws/"):
        clean_path = clean_path[3:].lstrip("/")

    scheme = "wss" if agent_service_url.startswith("https://") else "ws"
    host = agent_service_url.split("://", 1)[1] if "://" in agent_service_url else agent_service_url
    upstream_url = f"{scheme}://{host}/ws/{clean_path}"
    if query_string:
        upstream_url += f"?{query_string}"
    return upstream_url


@router.websocket("/ws/{path:path}")
async def ws_proxy(websocket: WebSocket, path: str):
    """
    Proxy WebSocket connections to agent-service.
    Auth is handled by the auth middleware before the WS upgrade.
    Both /ws/crawls/{id}/stream and /ws/chat/{session} are forwarded.
    """
    await websocket.accept()

    query_string = str(websocket.url.query)
    upstream_url = build_upstream_ws_url(settings.AGENT_SERVICE_URL, path, query_string)

    # Forward Cookie and Auth headers to upstream
    headers = {}
    if "cookie" in websocket.headers:
        headers["Cookie"] = websocket.headers["cookie"]

    token = websocket.cookies.get("access_token") or websocket.query_params.get("token")
    connect_kwargs = {}
    if headers:
        import inspect
        sig = inspect.signature(websockets.connect)
        if "additional_headers" in sig.parameters:
            connect_kwargs["additional_headers"] = headers
        else:
            connect_kwargs["extra_headers"] = headers

    try:
        async with websockets.connect(upstream_url, **connect_kwargs) as upstream_ws:
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
