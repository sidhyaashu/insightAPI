"""LlmUsage — granular per-call LLM token and cost ledger."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class LlmUsage(Base):
    """
    One row per LLM API call made during a crawl.

    This gives per-crawl and per-user cost roll-ups, cache-hit rates, and
    model breakdown for billing visibility — at much finer granularity than
    the aggregate ``cost_usd`` / ``total_tokens`` stored on ``CrawlSession``.
    """
    __tablename__ = "llm_usage"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    crawl_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False,
        comment="FK to crawl_sessions.id (soft reference, no FK constraint for perf)"
    )
    user_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tier: Mapped[str] = mapped_column(
        String(16), nullable=False, default="fast",
        comment="ModelTier: fast | smart | vision"
    )
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cached: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True if response was served from Redis cache (no LLM API call made)"
    )
    node_name: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="Agent node that made the call, e.g. PlannerNode, AnalyzerNode"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @property
    def model(self) -> str:
        return self.model_name

    @property
    def input_tokens(self) -> int:
        return self.prompt_tokens

    @property
    def output_tokens(self) -> int:
        return self.completion_tokens

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "crawl_id": self.crawl_id,
            "user_id": self.user_id,
            "node_name": self.node_name,
            "model": self.model_name,
            "model_name": self.model_name,
            "tier": self.tier,
            "input_tokens": self.prompt_tokens,
            "output_tokens": self.completion_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "cached": self.cached,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
