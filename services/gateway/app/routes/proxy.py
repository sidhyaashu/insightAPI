"""Backward compatibility re-export of gateway REST proxy router."""
from app.api.v1.endpoints.proxy import router, ROUTE_TABLE, reverse_proxy

__all__ = ["router", "ROUTE_TABLE", "reverse_proxy"]
