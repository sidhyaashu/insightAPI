"""SecurityFinding — one row per confirmed vulnerability found during a crawl."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class SecurityFinding(Base):
    """
    A confirmed vulnerability finding linked to the security_test_patterns record
    that produced the detection.

    Fields:
      - id: UUID primary key
      - crawl_id: Crawl session reference
      - user_id: User identifier
      - pattern_id: Reference to security_test_patterns.id
      - endpoint_key: Normalized endpoint route or method+route key
      - finding_type: Vulnerability class (idor, injection, auth_bypass, etc.)
      - severity: info | low | medium | high | critical
      - detail: JSON evidence, request/response payloads, and detection signals
      - discovered_via: "cache" | "llm_reasoning" | "rule_classifier"
      - ran_via_cache: Boolean flag for cost accounting
      - created_at: Timestamp
    """

    __tablename__ = "security_findings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    crawl_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False,
        comment="FK to crawl_sessions.id"
    )
    user_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    pattern_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False,
        comment="FK to security_test_patterns.id"
    )
    endpoint_signature: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False
    )
    vuln_class: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="idor|injection|auth_bypass|mass_assignment|rate_limit_bypass|ssrf_via_param|other"
    )
    endpoint_route: Mapped[str | None] = mapped_column(Text, nullable=True)
    method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    evidence: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Request/response delta that triggered the finding"
    )
    severity: Mapped[str] = mapped_column(
        String(16), default="medium", nullable=False,
        comment="info|low|medium|high|critical"
    )
    ran_via_cache: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True when finding was produced by cached pattern replay (no LLM call made)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Aliases to match standard schema definitions
    @property
    def endpoint_key(self) -> str:
        return f"{self.method or 'GET'} {self.endpoint_route or '/'}"

    @property
    def finding_type(self) -> str:
        return self.vuln_class

    @property
    def detail(self) -> dict:
        return self.evidence or {}

    @property
    def discovered_via(self) -> str:
        return "cache" if self.ran_via_cache else "llm_reasoning"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "crawl_id": self.crawl_id,
            "user_id": self.user_id,
            "pattern_id": self.pattern_id,
            "endpoint_signature": self.endpoint_signature,
            "endpoint_route": self.endpoint_route,
            "endpoint_key": self.endpoint_key,
            "method": self.method,
            "vuln_class": self.vuln_class,
            "finding_type": self.finding_type,
            "severity": self.severity,
            "evidence": self.evidence,
            "detail": self.detail,
            "discovered_via": self.discovered_via,
            "ran_via_cache": self.ran_via_cache,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
