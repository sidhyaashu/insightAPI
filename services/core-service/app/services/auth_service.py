"""Core Service — AuthService: Business logic for email/password registration, login, verification, and rate limiting."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from app.core.security import hash_password, verify_password, generate_random_token
from app.repositories.user_repo import UserRepository
from app.repositories.session_repo import SessionRepository
from app.services.token_service import TokenService
from app.services.email_service import EmailService
from app.core.redis import get_redis_client
from app.core.constants import (
    RATE_LIMIT_LOGIN_ATTEMPTS, RATE_LIMIT_LOGIN_WINDOW_SECONDS,
    RATE_LIMIT_VERIFY_RESEND_MAX, RATE_LIMIT_VERIFY_WINDOW_SECONDS,
    RATE_LIMIT_FORGOT_PW_MAX, RATE_LIMIT_FORGOT_PW_WINDOW_SECONDS,
    PASSWORD_RESET_TOKEN_TTL_HOURS
)

logger = logging.getLogger("core.auth_service")


class AuthService:
    def __init__(self, user_repo: UserRepository, session_repo: SessionRepository):
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.token_service = TokenService(session_repo)

    async def register_email_user(self, email: str, password: str, name: str | None = None) -> dict:
        """Register a new user with email and password."""
        email_clean = email.strip().lower()
        existing = await self.user_repo.get_by_email(email_clean)
        if existing:
            raise ValueError("An account with this email address already exists.")

        hashed_pw = hash_password(password)
        verification_token = generate_random_token()

        user = await self.user_repo.create_email_user(
            email=email_clean,
            hashed_password=hashed_pw,
            name=name,
            verification_token=verification_token,
        )

        # Dispatch verification email if not admin (admin is auto-verified)
        if not user.is_verified:
            await EmailService.send_verification_email(user.email, verification_token)

        tokens = await self.token_service.issue_token_pair(user.id, user.tier)
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "tier": user.tier,
                "role": user.role,
                "is_verified": user.is_verified,
            },
        }

    async def login_email_user(self, email: str, password: str) -> dict:
        """Authenticate user with email & password, enforcing failed login rate limits."""
        email_clean = email.strip().lower()
        redis = await get_redis_client()

        # Brute force protection check
        fail_key = f"ratelimit:login_fails:{email_clean}"
        fails = await redis.get(fail_key)
        if fails and int(fails) >= RATE_LIMIT_LOGIN_ATTEMPTS:
            raise ValueError("Too many failed login attempts. Please try again in 15 minutes.")

        user = await self.user_repo.get_by_email(email_clean)
        if not user or not user.hashed_password:
            # Increment failed attempts counter
            pipe = redis.pipeline()
            pipe.incr(fail_key)
            pipe.expire(fail_key, RATE_LIMIT_LOGIN_WINDOW_SECONDS)
            await pipe.execute()
            raise ValueError("Invalid email or password.")

        if not verify_password(password, user.hashed_password):
            pipe = redis.pipeline()
            pipe.incr(fail_key)
            pipe.expire(fail_key, RATE_LIMIT_LOGIN_WINDOW_SECONDS)
            await pipe.execute()
            raise ValueError("Invalid email or password.")

        # Success — reset failed login counter
        await redis.delete(fail_key)

        # Special check: grant ADMIN status if sidhyaasutosh@gmail.com
        user = await self.user_repo.check_and_grant_admin(user)

        tokens = await self.token_service.issue_token_pair(user.id, user.tier)
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "tier": user.tier,
                "role": user.role,
                "is_verified": user.is_verified,
            },
        }

    async def verify_email(self, token: str) -> bool:
        """Confirm email verification token."""
        user = await self.user_repo.verify_email_by_token(token)
        return bool(user)

    async def resend_verification_email(self, email: str) -> None:
        """Resend email verification link with Redis rate limiting (3/hour)."""
        email_clean = email.strip().lower()
        redis = await get_redis_client()
        rate_key = f"ratelimit:resend_verify:{email_clean}"

        count = await redis.get(rate_key)
        if count and int(count) >= RATE_LIMIT_VERIFY_RESEND_MAX:
            raise ValueError("Too many verification email requests. Please try again in 1 hour.")

        user = await self.user_repo.get_by_email(email_clean)
        if not user or user.is_verified:
            return   # Silent return for security

        token = generate_random_token()
        await self.user_repo.set_verification_token(user.id, token)

        # Increment rate limit key
        pipe = redis.pipeline()
        pipe.incr(rate_key)
        pipe.expire(rate_key, RATE_LIMIT_VERIFY_WINDOW_SECONDS)
        await pipe.execute()

        await EmailService.send_verification_email(user.email, token)

    async def request_password_reset(self, email: str) -> None:
        """Initiate password reset flow with Redis rate limiting (3/hour)."""
        email_clean = email.strip().lower()
        redis = await get_redis_client()
        rate_key = f"ratelimit:forgot_pw:{email_clean}"

        count = await redis.get(rate_key)
        if count and int(count) >= RATE_LIMIT_FORGOT_PW_MAX:
            raise ValueError("Too many password reset requests. Please try again in 1 hour.")

        user = await self.user_repo.get_by_email(email_clean)
        if not user or not user.hashed_password:
            return   # Silent return so attacker cannot discover registered emails

        token = generate_random_token()
        await self.user_repo.set_password_reset_token(user.id, token)

        pipe = redis.pipeline()
        pipe.incr(rate_key)
        pipe.expire(rate_key, RATE_LIMIT_FORGOT_PW_WINDOW_SECONDS)
        await pipe.execute()

        await EmailService.send_password_reset_email(user.email, token)

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset user password using valid, unexpired reset token."""
        user = await self.user_repo.get_by_password_reset_token(token)
        if not user or not user.password_reset_sent_at:
            raise ValueError("Invalid or expired password reset token.")

        # Check token expiration (1 hour TTL)
        now = datetime.now(timezone.utc)
        if now - user.password_reset_sent_at > timedelta(hours=PASSWORD_RESET_TOKEN_TTL_HOURS):
            raise ValueError("Password reset token has expired. Please request a new one.")

        new_hashed = hash_password(new_password)
        updated_user = await self.user_repo.reset_password_by_token(token, new_hashed)
        return bool(updated_user)
