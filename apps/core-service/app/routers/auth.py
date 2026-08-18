"""Backward compatibility re-export of auth router."""
from app.api.v1.endpoints.auth import router, RegisterRequest, LoginRequest, ResendVerifyRequest, ForgotPasswordRequest, ResetPasswordRequest

__all__ = ["router", "RegisterRequest", "LoginRequest", "ResendVerifyRequest", "ForgotPasswordRequest", "ResetPasswordRequest"]
