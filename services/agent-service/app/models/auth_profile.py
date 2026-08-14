"""
SQLAlchemy ORM model for stored Auth Profiles.
Credentials are encrypted at rest with Fernet.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.encryption import decrypt_credentials, mask_credentials


class AuthProfile(Base):
    __tablename__ = "auth_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), default="default", nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    target_domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    login_url: Mapped[str] = mapped_column(Text, nullable=False)
    auth_type: Mapped[str] = mapped_column(String(32), default="form", nullable=False)  # form, oauth_google, oauth_github, saml
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)

    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_status: Mapped[str | None] = mapped_column(String(32), nullable=True)  # success, failed
    last_test_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def get_decrypted_credentials(self) -> dict:
        """Returns the cleartext credentials dictionary for runtime execution."""
        return decrypt_credentials(self.encrypted_credentials)

    def to_dict(self, mask_secrets: bool = True) -> dict:
        """Serializes profile to dictionary. By default masks passwords/secrets."""
        creds = self.get_decrypted_credentials()
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "name": self.name,
            "target_domain": self.target_domain,
            "login_url": self.login_url,
            "auth_type": self.auth_type,
            "credentials": mask_credentials(creds) if mask_secrets else creds,
            "last_tested_at": self.last_tested_at.isoformat() if self.last_tested_at else None,
            "last_test_status": self.last_test_status,
            "last_test_error": self.last_test_error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
