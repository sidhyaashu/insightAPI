"""Agent-Service SQLAlchemy ORM model for persisted crawl sessions."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class CrawlSession(Base):
    __tablename__ = "crawl_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    user_tier: Mapped[str] = mapped_column(String(32), default="FREE", nullable=False)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    max_pages: Mapped[int] = mapped_column(Integer, default=10)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Export outputs stored as JSON blobs
    openapi_spec: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    postman_collection: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    markdown_docs: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Human-reviewed endpoint overrides (schema corrections + exclusion flags)
    # Populated by PATCH /crawls/{id}/endpoints/{key}; consumed at approve time.
    reviewed_endpoints: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Replayable ordered sequence of executed actions & triggered network calls
    action_traces: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # LLM Token & Cost Tracking
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(default=0.0, nullable=False)
    llm_metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

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
            "session_id": self.id,
            "user_id": self.user_id,
            "target_url": self.target_url,
            "status": self.status,
            "max_pages": self.max_pages,
            "goal": self.goal,
            "captured_count": self.captured_count,
            "action_traces": self.action_traces or [],
            "openapi_spec": self.openapi_spec,
            "postman_collection": self.postman_collection,
            "markdown_docs": self.markdown_docs,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "llm_metrics": self.llm_metrics_json or {},
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else datetime.now(timezone.utc).isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else datetime.now(timezone.utc).isoformat(),
        }

