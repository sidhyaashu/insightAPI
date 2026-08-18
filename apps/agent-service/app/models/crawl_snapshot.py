"""Agent-Service SQLAlchemy ORM model for per-crawl endpoint snapshots.

Each completed crawl writes one ``CrawlSnapshot`` row per captured endpoint,
enabling drift comparison between any two crawls via ``app.core.drift``.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class CrawlSnapshot(Base):
    __tablename__ = "crawl_snapshots"

    # ── Primary key ──────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Owning crawl / project ───────────────────────────────────────────────
    crawl_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # ── Endpoint key: "{method}:{template_route}:{status_code}" ─────────────
    endpoint_key: Mapped[str] = mapped_column(String(512), nullable=False)

    # ── Normalized schema persisted from the OpenAPI exporter ────────────────
    schema_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── HTTP status code observed for this endpoint ──────────────────────────
    status_code: Mapped[int] = mapped_column(Integer, default=200, nullable=False)

    # ── Metadata ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        # One snapshot row per (crawl, endpoint) — idempotent upserts are safe
        UniqueConstraint("crawl_id", "endpoint_key", name="uq_snapshot_crawl_endpoint"),
        # Accelerate per-project latest-crawl auto-detect lookups
        Index("ix_snapshot_project_crawl", "project_id", "crawl_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "crawl_id": self.crawl_id,
            "project_id": self.project_id,
            "endpoint_key": self.endpoint_key,
            "schema_json": self.schema_json,
            "status_code": self.status_code,
            "created_at": self.created_at.isoformat(),
        }
