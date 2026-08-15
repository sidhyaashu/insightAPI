"""
Security Patterns API — Human review queue for destructive security tests.

Endpoints
---------
GET  /security-patterns/pending-review
    Returns all pending approval requests for the authenticated user.
    Surfaces reasoning_trace so reviewers can read the LLM's justification.

POST /security-patterns/{approval_id}/approve-run
    Grants single-use approval for one destructive test execution.
    Single-use: next run on a different target requires a new approval.
    Returns {"approved": true, "approval_id": "...", "policy": "single-use"}.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.models.security_test_pattern import SecurityTestPattern
from app.repositories.security_repo import SecurityPatternRepository

logger = get_logger("api.security_patterns")

router = APIRouter()


# ── GET /security-patterns/pending-review ────────────────────────────────────

@router.get(
    "/pending-review",
    summary="List pending destructive test approval requests",
    response_description="Pending SecurityApproval records for this user with pattern context",
)
async def list_pending_approvals(
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all `status=pending` SecurityApproval rows for the authenticated user.

    Each item includes:
    - approval_id, pattern_id, endpoint_route, method, target_domain
    - test_strategy_snapshot — the exact test case awaiting authorization
    - reasoning_trace — the LLM's justification (from linked pattern)
    - pattern_meta — occurrences, distinct_target_count, confidence, is_destructive

    The reviewer reads this queue, evaluates the reasoning, then calls
    POST /security-patterns/{approval_id}/approve-run to authorize one execution.
    """
    repo = SecurityPatternRepository(db)
    approvals = await repo.get_pending_approvals(x_user_id)

    if not approvals:
        return {"pending_approvals": [], "total": 0}

    # Enrich each approval with pattern metadata for the reviewer
    pattern_ids = list({a.pattern_id for a in approvals if a.pattern_id != "unknown"})
    patterns_by_id: dict = {}
    if pattern_ids:
        pattern_rows = await db.execute(
            select(SecurityTestPattern).where(SecurityTestPattern.id.in_(pattern_ids))
        )
        patterns_by_id = {p.id: p for p in pattern_rows.scalars().all()}

    items = []
    for approval in approvals:
        item = approval.to_dict()
        pattern = patterns_by_id.get(approval.pattern_id)
        if pattern:
            # reasoning_trace surfaced here — reviewer context only
            item["reasoning_trace"] = pattern.reasoning_trace
            item["pattern_meta"] = {
                "vuln_class": pattern.vuln_class,
                "occurrences": pattern.occurrences,
                "distinct_target_count": pattern.distinct_target_count,
                "confidence": pattern.confidence,
                "status": pattern.status,
                "is_destructive": pattern.is_destructive,
            }
        items.append(item)

    logger.info(f"Pending approvals | user={x_user_id} | count={len(items)}")
    return {"pending_approvals": items, "total": len(items)}


# ── POST /security-patterns/{approval_id}/approve-run ────────────────────────

@router.post(
    "/{approval_id}/approve-run",
    summary="Grant single-use approval for a destructive security test",
)
async def approve_run(
    approval_id: str,
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """
    Grants **single-use** authorization for one destructive test execution.

    Rules:
    - Sets SecurityApproval.status = approved and records reviewed_by/reviewed_at.
    - Authorizes exactly ONE execution. Any subsequent run — same pattern, different
      target — requires a new approval row and a new POST to this endpoint.
    - Returns HTTP 409 if the approval is already approved/executed/rejected.
    - Returns HTTP 404 if the approval_id doesn't belong to this user.

    No reject action is provided. Non-approval is implicit — the test will not
    execute until this record is approved.
    """
    repo = SecurityPatternRepository(db)

    # Ownership check — approval must belong to this user
    approval = await repo.get_approval_by_id(approval_id, x_user_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request '{approval_id}' not found or does not belong to your account.",
        )

    try:
        updated = await repo.approve_run(
            approval_id=approval_id, reviewed_by=x_user_id
        )
    except ValueError as exc:
        # Already approved / executed / rejected
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Approval update failed unexpectedly.",
        )

    logger.info(
        f"Destructive test approved | approval={approval_id} | user={x_user_id}"
    )

    return {
        "approved": True,
        "approval_id": approval_id,
        "pattern_id": updated.pattern_id,
        "endpoint_route": updated.endpoint_route,
        "method": updated.method,
        "target_domain": updated.target_domain,
        "reviewed_at": updated.reviewed_at.isoformat() if updated.reviewed_at else None,
        "policy": "single-use",
        "note": (
            "This approval authorizes exactly one execution. "
            "The next destructive test run on any target requires a new approval request."
        ),
    }


# ── POST /security-patterns/{approval_id}/reject ────────────────────────────

@router.post(
    "/{approval_id}/reject",
    summary="Reject a pending destructive test approval request",
)
async def reject_approval(
    approval_id: str,
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    repo = SecurityPatternRepository(db)
    approval = await repo.get_approval_by_id(approval_id, x_user_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request '{approval_id}' not found.",
        )
    try:
        updated = await repo.reject_approval(approval_id=approval_id, reviewed_by=x_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return {"rejected": True, "approval_id": approval_id, "status": "rejected"}


# ── GET /security-patterns/findings ──────────────────────────────────────────

@router.get(
    "/findings",
    summary="List confirmed security vulnerabilities",
)
async def list_security_findings(
    crawl_id: Optional[str] = None,
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    repo = SecurityPatternRepository(db)
    findings = await repo.list_findings(user_id=x_user_id, crawl_id=crawl_id)
    return {"findings": [f.to_dict() for f in findings], "total": len(findings)}


# ── GET /security-patterns/patterns ──────────────────────────────────────────

@router.get(
    "/patterns",
    summary="List learned and in-review security test patterns",
)
async def list_security_test_patterns(
    status: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    repo = SecurityPatternRepository(db)
    patterns = await repo.list_patterns(status_filter=status, limit=limit)
    return {"patterns": [p.to_dict() for p in patterns], "total": len(patterns)}

