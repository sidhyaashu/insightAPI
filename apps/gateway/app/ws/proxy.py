"""Backward compatibility re-export of gateway WebSocket proxy router."""
from app.api.v1.endpoints.ws import router, ws_proxy

__all__ = ["router", "ws_proxy"]
