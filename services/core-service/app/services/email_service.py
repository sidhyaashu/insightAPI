"""Core Service — Email Service: Dispatches email verification and password reset links."""
from __future__ import annotations

import logging
from app.core.config import settings

logger = logging.getLogger("core.email")


class EmailService:
    @staticmethod
    async def send_verification_email(to_email: str, token: str) -> None:
        """
        Send an email verification link to the user.
        In development, logs the link clearly to standard output.
        """
        verify_url = f"{settings.APP_URL}/verify-email?token={token}"
        
        logger.info(f"============================================================")
        logger.info(f"[EMAIL DISPATCH] Verification email sent to: {to_email}")
        logger.info(f"[VERIFY LINK] {verify_url}")
        logger.info(f"============================================================")

    @staticmethod
    async def send_password_reset_email(to_email: str, token: str) -> None:
        """
        Send a password reset link to the user.
        In development, logs the link clearly to standard output.
        """
        reset_url = f"{settings.APP_URL}/reset-password?token={token}"
        
        logger.info(f"============================================================")
        logger.info(f"[EMAIL DISPATCH] Password reset email sent to: {to_email}")
        logger.info(f"[RESET LINK] {reset_url}")
        logger.info(f"============================================================")
