"""SecurityApproval — single-use human approval record for destructive security tests.

Every request to execute a destructive test creates one row here with
status=pending. A human must POST to /security-patterns/{id}/approve-run before
SandboxExecutor will run it. Approving one row authorizes exactly ONE execution.
The next destructive run, even for the same pattern on a different target,
requires a fresh approval row.

This is not a standing authorization. It is a one-time gate.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class SecurityApproval(Base):
    """
    Single-use approval record for destructive security test execution.

    Status transitions:
      pending → approved  (human calls POST /approve-run)
      pending → rejected  (future: human dismisses; currently implicit via expiry or non-action)
      approved → executed (SandboxExecutor consumes the approval)

    A row is created by SecurityReasonerNode whenever it encounters a test_strategy
    with is_destructive=True. The node queues the request and moves on without
    executing. The crawl report surfaces pending approvals so the user can act.
    """

    __tablename__ = "security_approvals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    pattern_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False,
        comment="FK to security_test_patterns.id (soft reference)"
    )
    crawl_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    endpoint_route: Mapped[str | None] = mapped_column(Text, nullable=True)
    method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    target_domain: Mapped[str | None] = mapped_column(String(256), nullable=True)
    test_strategy_snapshot: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Snapshot of test_strategy at time of request, for reviewer context"
    )
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False,
        comment="pending|approved|rejected|executed"
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        String(36), nullable=True,
        comment="user_id of the reviewer who approved/rejected"
    )
    execution_result: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Filled by SandboxExecutor after execution completes"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pattern_id": self.pattern_id,
            "crawl_id": self.crawl_id,
            "user_id": self.user_id,
            "endpoint_route": self.endpoint_route,
            "method": self.method,
            "target_domain": self.target_domain,
            "test_strategy_snapshot": self.test_strategy_snapshot,
            "status": self.status,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewed_by": self.reviewed_by,
        }
