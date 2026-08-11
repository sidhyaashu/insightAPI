"""Backward compatibility re-export of users router."""
from app.api.v1.endpoints.users import router

__all__ = ["router"]
