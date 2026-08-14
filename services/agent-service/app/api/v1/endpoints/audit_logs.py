"""
Enterprise Audit Logs API endpoint.
Restricted to ENTERPRISE and ADMIN tiers for compliance monitoring and security audit trails.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.audit_log_repo import AuditLogRepository

router = APIRouter()


def _clean_header(val: Any, default: str = "") -> str:
    if hasattr(val, "default"):
        return str(val.default or default)
    return str(val if val is not None else default)


@router.get("")
async def get_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action type e.g. crawl.create"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    target_id: Optional[str] = Query(None, description="Filter by target entity ID"),
    start_date: Optional[datetime] = Query(None, description="Filter logs on or after this ISO timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter logs on or before this ISO timestamp"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    x_user_id: str = Header("default-user", alias="X-User-Id"),
    x_user_tier: str = Header("FREE", alias="X-User-Tier"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve paginated audit logs for the authenticated tenant.
    Requires ENTERPRISE tier or ADMIN role.
    """
    user_id = _clean_header(x_user_id, "default-user")
    tier = _clean_header(x_user_tier, "FREE").upper()
    if tier not in ("ENTERPRISE", "ADMIN"):
        raise HTTPException(
            status_code=403,
            detail="Access to compliance audit logs requires ENTERPRISE tier. Please upgrade your subscription.",
        )

    repo = AuditLogRepository(db)
    items, total = await repo.list_logs(
        user_id=user_id,
        project_id=project_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        target_id=target_id,
        limit=limit,
        offset=offset,
    )

    return {
        "items": [item.to_dict() for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }

