"""
Audit Log ORM model for enterprise compliance, security tracking, and tenant action audit trails.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)
    action: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "action": self.action,
            "target_id": self.target_id,
            "ip": self.ip,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata_json or {},
        }
