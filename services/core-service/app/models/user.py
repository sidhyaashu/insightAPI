"""Core Service — User ORM model with email auth, verification, and admin role fields."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.core.constants import TIER_FREE, ROLE_USER, LOGIN_METHOD_EMAIL


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Auth Credentials & Provider
    email: Mapped[str] = mapped_column(String(256), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(256), nullable=True)  # None for OAuth-only users
    login_method: Mapped[str] = mapped_column(String(32), default=LOGIN_METHOD_EMAIL, nullable=False) # "email" | "github" | "google"
    oauth_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    oauth_sub: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)

    # Verification & Security Lifecycle
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_token: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    verification_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_reset_token: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    password_reset_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Profile & Access
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tier: Mapped[str] = mapped_column(String(32), default=TIER_FREE, nullable=False)   # FREE | STARTER | PRO | ENTERPRISE | ADMIN
    role: Mapped[str] = mapped_column(String(32), default=ROLE_USER, nullable=False)   # user | admin

    # Stripe customer ID
    stripe_customer_id: Mapped[str | None] = mapped_column(String(256), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
