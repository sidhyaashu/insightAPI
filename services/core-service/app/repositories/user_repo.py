"""Core Service — UserRepository: DB queries for user lifecycle and admin assignment."""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.user import User
from app.core.constants import (
    ADMIN_EMAIL, TIER_ADMIN, TIER_FREE, ROLE_ADMIN, ROLE_USER,
    LOGIN_METHOD_EMAIL, LOGIN_METHOD_GITHUB, LOGIN_METHOD_GOOGLE
)


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email.ilike(email.strip())))
        return result.scalar_one_or_none()

    async def get_by_verification_token(self, token: str) -> User | None:
        result = await self.db.execute(select(User).where(User.verification_token == token))
        return result.scalar_one_or_none()

    async def get_by_password_reset_token(self, token: str) -> User | None:
        result = await self.db.execute(select(User).where(User.password_reset_token == token))
        return result.scalar_one_or_none()

    async def check_and_grant_admin(self, user: User) -> User:
        """
        Special Admin Check: If user email matches sidhyaasutosh@gmail.com,
        automatically grant ADMIN tier, admin role, and verified status.
        """
        if user.email.strip().lower() == ADMIN_EMAIL.lower():
            user.tier = TIER_ADMIN
            user.role = ROLE_ADMIN
            user.is_verified = True
            await self.db.commit()
            await self.db.refresh(user)
        return user

    async def create_email_user(
        self,
        email: str,
        hashed_password: str,
        name: str | None = None,
        verification_token: str | None = None,
    ) -> User:
        """Create a new user using email & password registration."""
        is_admin_email = email.strip().lower() == ADMIN_EMAIL.lower()
        
        user = User(
            email=email.strip().lower(),
            hashed_password=hashed_password,
            login_method=LOGIN_METHOD_EMAIL,
            name=name,
            tier=TIER_ADMIN if is_admin_email else TIER_FREE,
            role=ROLE_ADMIN if is_admin_email else ROLE_USER,
            is_verified=True if is_admin_email else False,
            verification_token=verification_token,
            verification_sent_at=datetime.now(timezone.utc) if verification_token else None,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def verify_email_by_token(self, token: str) -> User | None:
        """Confirm email verification token and activate user."""
        user = await self.get_by_verification_token(token)
        if not user:
            return None

        user.is_verified = True
        user.verification_token = None
        user.verification_sent_at = None
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def set_verification_token(self, user_id: str, token: str) -> None:
        """Save new email verification token for resend request."""
        user = await self.get_by_id(user_id)
        if user:
            user.verification_token = token
            user.verification_sent_at = datetime.now(timezone.utc)
            await self.db.commit()

    async def set_password_reset_token(self, user_id: str, token: str) -> None:
        """Save password reset token with timestamp."""
        user = await self.get_by_id(user_id)
        if user:
            user.password_reset_token = token
            user.password_reset_sent_at = datetime.now(timezone.utc)
            await self.db.commit()

    async def reset_password_by_token(self, token: str, new_hashed_password: str) -> User | None:
        """Verify password reset token and update hashed password."""
        user = await self.get_by_password_reset_token(token)
        if not user:
            return None

        user.hashed_password = new_hashed_password
        user.password_reset_token = None
        user.password_reset_sent_at = None
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_oauth_sub(self, provider: str, sub: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.oauth_provider == provider, User.oauth_sub == sub)
        )
        return result.scalar_one_or_none()

    async def upsert_oauth_user(
        self,
        provider: str,
        sub: str,
        email: str,
        name: str | None = None,
        avatar_url: str | None = None,
    ) -> User:
        """
        Create or update a user from OAuth profile data.
        Implements Identity Account Unification: if user created an account via Email/Password 
        with the same email, link the OAuth provider to that existing account.
        """
        normalized_email = email.strip().lower()
        
        # 1. First search by explicit (provider, sub)
        user = await self.get_by_oauth_sub(provider, sub)

        # 2. If not found by sub, search by email to unify existing account
        if not user:
            user = await self.get_by_email(normalized_email)

        is_admin_email = normalized_email == ADMIN_EMAIL.lower()

        if user:
            # Unify / Link OAuth provider to existing user record
            user.oauth_provider = provider
            user.oauth_sub = sub
            if name and not user.name:
                user.name = name
            if avatar_url:
                user.avatar_url = avatar_url
            user.is_verified = True  # OAuth provider verifies email
            if is_admin_email:
                user.tier = TIER_ADMIN
                user.role = ROLE_ADMIN
        else:
            # Create brand new user record
            user = User(
                oauth_provider=provider,
                oauth_sub=sub,
                login_method=provider,
                email=normalized_email,
                name=name,
                avatar_url=avatar_url,
                is_verified=True,
                tier=TIER_ADMIN if is_admin_email else TIER_FREE,
                role=ROLE_ADMIN if is_admin_email else ROLE_USER,
            )
            self.db.add(user)

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_tier(self, user_id: str, tier: str) -> None:
        user = await self.get_by_id(user_id)
        if user:
            user.tier = tier
            await self.db.commit()

    async def update_stripe_customer_id(self, user_id: str, customer_id: str) -> None:
        user = await self.get_by_id(user_id)
        if user:
            user.stripe_customer_id = customer_id
            await self.db.commit()

    async def update_overage_preference(self, user_id: str, allow_overage: bool) -> User | None:
        user = await self.get_by_id(user_id)
        if user:
            user.allow_overage = allow_overage
            await self.db.commit()
            await self.db.refresh(user)
        return user

