"""Agent-Service ORM models for VerifiedDomain and TosAcceptance audit logging."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class VerifiedDomain(Base):
    __tablename__ = "verified_domains"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    verification_token: Mapped[str] = mapped_column(String(128), nullable=False)
    verification_method: Mapped[str | None] = mapped_column(String(32), nullable=True)  # "dns_txt" | "well_known"
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "domain": self.domain,
            "verification_token": self.verification_token,
            "verification_method": self.verification_method,
            "is_verified": self.is_verified,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TosAcceptance(Base):
    __tablename__ = "tos_acceptances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    user_ip: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    tos_version: Mapped[str] = mapped_column(String(32), default="v1.0", nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "domain": self.domain,
            "target_url": self.target_url,
            "user_ip": self.user_ip,
            "tos_version": self.tos_version,
            "accepted_at": self.accepted_at.isoformat(),
        }
