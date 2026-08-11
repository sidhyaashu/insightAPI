"""Backward compatibility re-export of internal router."""
from app.api.v1.endpoints.internal import router, TIER_LEVELS

__all__ = ["router", "TIER_LEVELS"]
