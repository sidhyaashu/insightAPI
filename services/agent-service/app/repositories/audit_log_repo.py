"""
Repository for persisting and querying enterprise audit log records.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_log(
        self,
        user_id: str,
        action: str,
        target_id: Optional[str] = None,
        ip: Optional[str] = None,
        project_id: str = "default",
        metadata: Optional[dict] = None,
    ) -> AuditLog:
        """Persist a single audit log event."""
        log_entry = AuditLog(
            user_id=user_id,
            project_id=project_id or "default",
            action=action,
            target_id=target_id,
            ip=ip,
            metadata_json=metadata or {},
        )
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        return log_entry

    async def list_logs(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        target_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[AuditLog], int]:
        """List paginated audit logs scoped to a tenant with optional filtering."""
        conditions = [AuditLog.user_id == user_id]

        if project_id:
            conditions.append(AuditLog.project_id == project_id)
        if action:
            conditions.append(AuditLog.action == action)
        if target_id:
            conditions.append(AuditLog.target_id == target_id)
        if start_date:
            conditions.append(AuditLog.timestamp >= start_date)
        if end_date:
            conditions.append(AuditLog.timestamp <= end_date)

        # Count total
        count_query = select(func.count(AuditLog.id)).where(and_(*conditions))
        total_res = await self.db.execute(count_query)
        total = total_res.scalar_one() or 0

        # Query page
        query = (
            select(AuditLog)
            .where(and_(*conditions))
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total
