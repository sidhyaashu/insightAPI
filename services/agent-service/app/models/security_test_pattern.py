"""SecurityTestPattern — adaptive, memory-driven security test pattern store (V2).

V2 promotion rules (stricter than UI patterns to prevent false-negative hiding):

  HARD RULES (enforced in code, no override path):
  - is_destructive=True patterns NEVER reach status=learned, no matter how many
    confirmations. Every destructive test always requires human approval.
  - Auto-cache-replay requires ALL of:
      status=learned AND is_destructive=False
      AND occurrences >= OCCURRENCES_THRESHOLD (20)
      AND distinct_target_count >= DISTINCT_TARGET_THRESHOLD (15)
      AND confidence >= CONFIDENCE_THRESHOLD (0.80)

  The distinction from UI-pattern thresholds (N=3) is intentional and load-bearing:
  a wrong security pattern silently hides real vulnerabilities on every future target.
  Trust must be earned with cross-domain evidence, not just repeat runs on one site.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Text, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class SecurityTestPattern(Base):
    """
    Cross-target generalizable endpoint security test pattern.

    Lifecycle
    ---------
    new observation      → status=needs_review, occurrences=1, distinct_target_count=1
    20+ confirmations    → eligible for promotion IF distinct_target_count>=15 AND NOT is_destructive
    promoted             → status=learned (only non-destructive, cross-domain confirmed)
    conflicting outcome  → demoted to needs_review, outcome=inconclusive
    superseded           → status=deprecated (manual admin action)

    Fields
    ------
    endpoint_signature      : SHA-256 hex of (method + param_types_sorted +
                              param_name_shapes_sorted + auth_required + response_schema_shape).
                              Deliberately excludes literal URL/domain.
    vuln_class              : idor|injection|auth_bypass|mass_assignment|
                              rate_limit_bypass|ssrf_via_param|other
    test_strategy           : JSON test case spec with mandatory "is_destructive" key.
    is_destructive          : True if the test can write/modify/delete target state or
                              trigger side-effects (emails, payments, etc.).
                              HARD RULE: is_destructive=True → never auto-promote, never
                              auto-execute. Always requires human SecurityApproval.
    outcome                 : vulnerable|not_vulnerable|inconclusive
    confidence              : Float in [0, 0.99]. Rises with distinct-target confirmations.
    occurrences             : Total run count across all targets (including repeat runs
                              on the same domain — counts raw execution volume).
    distinct_target_count   : Number of DIFFERENT domains this pattern has been confirmed
                              against. Repeat runs on the same domain do NOT increment this.
                              Promotion requires distinct_target_count >= 15.
    seen_domains            : JSON array of domain strings already counted. Used to deduplicate
                              distinct_target_count increments without a join table.
    reasoning_trace         : LLM chain-of-thought. Stored for audit, surfaced in the
                              human review queue. NEVER re-sent to LLM on cache hit.
    status                  : needs_review|learned|deprecated
    last_human_reviewed_at  : When a human last reviewed/approved a test using this pattern.
    """

    __tablename__ = "security_test_patterns"

    # ── Promotion thresholds (V2 — far stricter than UI-pattern N=3) ──────────
    # Both must be met simultaneously. is_destructive=True bypasses all of these.
    OCCURRENCES_THRESHOLD: int = 20
    DISTINCT_TARGET_THRESHOLD: int = 15
    CONFIDENCE_THRESHOLD: float = 0.80

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    endpoint_signature: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False,
        comment="SHA-256 of (method+param_types+param_names+auth+schema_shape)"
    )
    vuln_class: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="idor|injection|auth_bypass|mass_assignment|rate_limit_bypass|ssrf_via_param|other"
    )
    test_strategy: Mapped[dict] = mapped_column(
        JSON, nullable=False,
        comment="Test case spec — must include 'is_destructive' key"
    )
    is_destructive: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True=can write/modify/delete target state. Hard-blocks auto-promotion and auto-execution."
    )
    outcome: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="vulnerable|not_vulnerable|inconclusive"
    )
    confidence: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False,
        comment="Rises with distinct-target confirmation. Capped at 0.99."
    )
    occurrences: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False,
        comment="Total executions across all targets (including repeat runs on same domain)"
    )
    distinct_target_count: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False,
        comment="Number of DIFFERENT domains this pattern confirmed against. Promotion requires >=15."
    )
    seen_domains: Mapped[list | None] = mapped_column(
        JSON, nullable=True,
        comment="JSON array of domain strings already counted for distinct_target_count deduplication."
    )
    reasoning_trace: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="LLM chain-of-thought. Surfaced in review queue. Never re-sent on cache hit."
    )
    status: Mapped[str] = mapped_column(
        String(32), default="needs_review", nullable=False,
        comment="needs_review|learned|deprecated"
    )
    last_human_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When a human last reviewed/approved a run using this pattern."
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def is_cache_eligible(self) -> bool:
        """
        True iff this pattern qualifies for LLM-free cache replay.
        ALL conditions must be simultaneously satisfied — no partial credit.
        """
        return (
            self.status == "learned"
            and not self.is_destructive
            and self.occurrences >= self.OCCURRENCES_THRESHOLD
            and self.distinct_target_count >= self.DISTINCT_TARGET_THRESHOLD
            and self.confidence >= self.CONFIDENCE_THRESHOLD
        )

    def to_dict(self, include_reasoning: bool = False) -> dict:
        d = {
            "id": self.id,
            "endpoint_signature": self.endpoint_signature,
            "vuln_class": self.vuln_class,
            "test_strategy": self.test_strategy,
            "is_destructive": self.is_destructive,
            "outcome": self.outcome,
            "confidence": self.confidence,
            "occurrences": self.occurrences,
            "distinct_target_count": self.distinct_target_count,
            "status": self.status,
            "last_human_reviewed_at": (
                self.last_human_reviewed_at.isoformat()
                if self.last_human_reviewed_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        # reasoning_trace is only included in human-review context, not public API
        if include_reasoning:
            d["reasoning_trace"] = self.reasoning_trace
        return d
