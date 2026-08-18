"""SecurityPatternRepository — V2.

Key enforcement points (all hard-coded, not config-driven):

1. upsert_pattern: is_destructive=True patterns NEVER reach status=learned.
   The check is a guard at the top of the promotion block — it is the first
   check, it cannot be bypassed by thresholds or confidence.

2. Promotion to learned requires ALL of:
   - is_destructive=False
   - occurrences >= SecurityTestPattern.OCCURRENCES_THRESHOLD (20)
   - distinct_target_count >= SecurityTestPattern.DISTINCT_TARGET_THRESHOLD (15)
   Any single condition failing keeps the pattern in needs_review indefinitely.

3. distinct_target_count is incremented only when the target domain is new,
   verified via the seen_domains JSON array. Repeat runs on the same domain
   increment occurrences but NOT distinct_target_count.

4. Approval CRUD: create_approval_request / approve_run / mark_executed enforce
   the single-use semantics — no standing authorizations.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.security_test_pattern import SecurityTestPattern
from app.models.security_finding import SecurityFinding
from app.models.security_approval import SecurityApproval

logger = logging.getLogger("agent.security_repo")


class SecurityPatternRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Pattern lookup ─────────────────────────────────────────────────────────

    async def get_by_signature(self, signature: str) -> Optional[SecurityTestPattern]:
        result = await self.db.execute(
            select(SecurityTestPattern).where(
                SecurityTestPattern.endpoint_signature == signature
            )
        )
        return result.scalar_one_or_none()

    # ── Upsert with V2 strict promotion ──────────────────────────────────────

    async def upsert_pattern(
        self,
        signature: str,
        vuln_class: str,
        test_strategy: dict,
        is_destructive: bool,
        outcome: str,
        target_domain: Optional[str] = None,
        reasoning_trace: Optional[str] = None,
    ) -> SecurityTestPattern:
        """
        Insert a new pattern or update an existing one with strict V2 promotion.

        Confidence formula:
            confidence = round(min(0.99, 0.4 + 0.04 * distinct_target_count), 3)
        This ties confidence directly to cross-domain evidence, not just repetition.
        """
        existing = await self.get_by_signature(signature)

        if existing is None:
            # First observation — always needs_review
            seen = [target_domain] if target_domain else []
            pattern = SecurityTestPattern(
                id=str(uuid.uuid4()),
                endpoint_signature=signature,
                vuln_class=vuln_class,
                test_strategy=test_strategy,
                is_destructive=is_destructive,
                outcome=outcome,
                confidence=0.0,
                occurrences=1,
                distinct_target_count=1 if target_domain else 0,
                seen_domains=seen,
                reasoning_trace=reasoning_trace,
                status="needs_review",
            )
            self.db.add(pattern)
            await self.db.commit()
            await self.db.refresh(pattern)
            logger.info(
                f"🔒 New security pattern | sig={signature[:12]}… "
                f"| class={vuln_class} | destructive={is_destructive} | outcome={outcome}"
            )
            return pattern

        # ── Existing pattern update ────────────────────────────────────────
        if existing.outcome == outcome:
            # Confirmed same outcome — safe to increment
            existing.occurrences += 1

            # Increment distinct_target_count only for a new domain
            seen = list(existing.seen_domains or [])
            if target_domain and target_domain not in seen:
                seen.append(target_domain)
                existing.seen_domains = seen
                existing.distinct_target_count = len(seen)
                logger.info(
                    f"📍 New distinct target for sig={signature[:12]}… "
                    f"| domain={target_domain} | distinct_count={existing.distinct_target_count}"
                )

            # Confidence tied to cross-domain evidence
            existing.confidence = round(
                min(0.99, 0.4 + 0.04 * existing.distinct_target_count), 3
            )
            existing.updated_at = datetime.now(timezone.utc)

            # ── PROMOTION BLOCK — strict V2 rules ──────────────────────────
            if existing.status == "needs_review":
                self._attempt_promotion(existing)

        else:
            # Conflicting outcome — demote if was learned, mark inconclusive
            existing.outcome = "inconclusive"
            if existing.status == "learned":
                existing.status = "needs_review"
                logger.warning(
                    f"⚠️  Pattern demoted (conflicting outcome) | sig={signature[:12]}…"
                )
            existing.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(existing)
        return existing

    @staticmethod
    def _attempt_promotion(pattern: SecurityTestPattern) -> None:
        """
        HARD RULES enforced here:
        1. is_destructive=True → never promote. Full stop. Not a threshold.
        2. occurrences < 20 → not promoted.
        3. distinct_target_count < 15 → not promoted.
        All three must pass simultaneously. No partial credit.
        """
        # Rule 1: Destructive patterns never auto-promote — hard block
        if pattern.is_destructive:
            return  # Not a warning, not a log — just silently enforced

        # Rule 2+3: Both evidence thresholds required
        if pattern.occurrences < SecurityTestPattern.OCCURRENCES_THRESHOLD:
            return
        if pattern.distinct_target_count < SecurityTestPattern.DISTINCT_TARGET_THRESHOLD:
            return

        pattern.status = "learned"
        logger.info(
            f"🎓 Security pattern promoted → learned | sig={pattern.endpoint_signature[:12]}… "
            f"| occurrences={pattern.occurrences} "
            f"| distinct_targets={pattern.distinct_target_count} "
            f"| confidence={pattern.confidence}"
        )

    # ── Finding insertion ─────────────────────────────────────────────────────

    async def insert_finding(
        self,
        crawl_id: str,
        user_id: str,
        pattern_id: str,
        endpoint_signature: str,
        vuln_class: str,
        endpoint_route: Optional[str],
        method: Optional[str],
        evidence: Optional[dict],
        severity: str = "medium",
        ran_via_cache: bool = False,
    ) -> SecurityFinding:
        finding = SecurityFinding(
            id=str(uuid.uuid4()),
            crawl_id=crawl_id,
            user_id=user_id,
            pattern_id=pattern_id,
            endpoint_signature=endpoint_signature,
            vuln_class=vuln_class,
            endpoint_route=endpoint_route,
            method=method,
            evidence=evidence,
            severity=severity,
            ran_via_cache=ran_via_cache,
        )
        self.db.add(finding)
        await self.db.commit()
        await self.db.refresh(finding)
        logger.info(
            f"🚨 Security finding | vuln={vuln_class} | severity={severity} "
            f"| via_cache={ran_via_cache} | crawl={crawl_id}"
        )
        return finding

    async def get_findings_by_crawl(self, crawl_id: str) -> list[SecurityFinding]:
        result = await self.db.execute(
            select(SecurityFinding)
            .where(SecurityFinding.crawl_id == crawl_id)
            .order_by(SecurityFinding.created_at)
        )
        return list(result.scalars().all())

    # ── Approval CRUD — single-use gate ──────────────────────────────────────

    async def create_approval_request(
        self,
        pattern_id: str,
        crawl_id: str,
        user_id: str,
        endpoint_route: Optional[str],
        method: Optional[str],
        target_domain: Optional[str],
        test_strategy_snapshot: Optional[dict],
    ) -> SecurityApproval:
        """
        Queue a destructive test for human approval.
        Creates a fresh row for every execution request — no standing auth.
        """
        approval = SecurityApproval(
            id=str(uuid.uuid4()),
            pattern_id=pattern_id,
            crawl_id=crawl_id,
            user_id=user_id,
            endpoint_route=endpoint_route,
            method=method,
            target_domain=target_domain,
            test_strategy_snapshot=test_strategy_snapshot,
            status="pending",
        )
        self.db.add(approval)
        await self.db.commit()
        await self.db.refresh(approval)
        logger.info(
            f"⏳ Destructive test approval requested | approval={approval.id} "
            f"| pattern={pattern_id} | domain={target_domain}"
        )
        return approval

    async def get_pending_approvals(self, user_id: str) -> list[SecurityApproval]:
        result = await self.db.execute(
            select(SecurityApproval)
            .where(
                SecurityApproval.user_id == user_id,
                SecurityApproval.status == "pending",
            )
            .order_by(SecurityApproval.requested_at.desc())
        )
        return list(result.scalars().all())

    async def get_approval_by_id(
        self, approval_id: str, user_id: str
    ) -> Optional[SecurityApproval]:
        result = await self.db.execute(
            select(SecurityApproval).where(
                SecurityApproval.id == approval_id,
                SecurityApproval.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def approve_run(
        self, approval_id: str, reviewed_by: str
    ) -> Optional[SecurityApproval]:
        """
        Grant single-use approval. Raises ValueError if already consumed.
        """
        result = await self.db.execute(
            select(SecurityApproval).where(SecurityApproval.id == approval_id)
        )
        approval = result.scalar_one_or_none()
        if approval is None:
            return None
        if approval.status != "pending":
            raise ValueError(
                f"Approval {approval_id} is already {approval.status}. "
                "A new request must be submitted for each destructive test execution."
            )
        approval.status = "approved"
        approval.reviewed_by = reviewed_by
        approval.reviewed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(approval)
        logger.info(
            f"✅ Destructive test approved | approval={approval_id} | by={reviewed_by}"
        )
        return approval

    async def get_approved_for_execution(
        self, pattern_id: str, crawl_id: str
    ) -> Optional[SecurityApproval]:
        """
        Find the single-use approved record for this specific crawl + pattern.
        Returns None if no valid approved record exists.
        """
        result = await self.db.execute(
            select(SecurityApproval).where(
                SecurityApproval.pattern_id == pattern_id,
                SecurityApproval.crawl_id == crawl_id,
                SecurityApproval.status == "approved",
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def mark_executed(
        self, approval_id: str, execution_result: dict
    ) -> Optional[SecurityApproval]:
        """Consume the single-use approval after execution."""
        result = await self.db.execute(
            select(SecurityApproval).where(SecurityApproval.id == approval_id)
        )
        approval = result.scalar_one_or_none()
        if approval is None:
            return None
        approval.status = "executed"
        approval.execution_result = execution_result
        await self.db.commit()
        await self.db.refresh(approval)
        return approval

    async def reject_approval(
        self, approval_id: str, reviewed_by: str
    ) -> Optional[SecurityApproval]:
        """Reject and cancel a pending destructive test approval."""
        result = await self.db.execute(
            select(SecurityApproval).where(SecurityApproval.id == approval_id)
        )
        approval = result.scalar_one_or_none()
        if approval is None:
            return None
        if approval.status != "pending":
            raise ValueError(
                f"Approval {approval_id} is already {approval.status}."
            )
        approval.status = "rejected"
        approval.reviewed_by = reviewed_by
        approval.reviewed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(approval)
        return approval

    async def list_findings(
        self, user_id: str, crawl_id: Optional[str] = None
    ) -> list[SecurityFinding]:
        """Query security findings for a user or specific crawl."""
        query = select(SecurityFinding).where(SecurityFinding.user_id == user_id)
        if crawl_id:
            query = query.where(SecurityFinding.crawl_id == crawl_id)
        query = query.order_by(SecurityFinding.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_patterns(
        self, status_filter: Optional[str] = None, limit: int = 100
    ) -> list[SecurityTestPattern]:
        """Query security test patterns with optional status filter."""
        query = select(SecurityTestPattern)
        if status_filter:
            query = query.where(SecurityTestPattern.status == status_filter)
        query = query.order_by(SecurityTestPattern.occurrences.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

