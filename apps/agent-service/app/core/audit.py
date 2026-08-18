"""
Audit Logging service for capturing tenant security and lifecycle events.
"""
from __future__ import annotations

import logging
from typing import Optional, Any, Dict
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("insightapi.audit")


class AuditLogger:
    """Helper service for recording tenant action audit events."""

    @staticmethod
    def extract_ip(request: Optional[Request]) -> str:
        """Extract client IP address from proxy headers or direct client connection."""
        if not request:
            return "system"
        
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # First IP in X-Forwarded-For is client
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        if request.client and request.client.host:
            return request.client.host
        
        return "unknown"

    @classmethod
    async def log_event(
        cls,
        db: Optional[AsyncSession],
        user_id: str,
        action: str,
        target_id: Optional[str] = None,
        request: Optional[Request] = None,
        ip: Optional[str] = None,
        project_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a compliance audit event safely.
        Never raises exceptions that would break primary API requests.
        """
        if not db:
            logger.debug(f"[Audit] (In-memory/No DB) {user_id} -> {action} ({target_id})")
            return

        client_ip = ip or cls.extract_ip(request)

        try:
            from app.repositories.audit_log_repo import AuditLogRepository
            repo = AuditLogRepository(db)
            await repo.create_log(
                user_id=user_id,
                action=action,
                target_id=target_id,
                ip=client_ip,
                project_id=project_id or "default",
                metadata=metadata or {},
            )
            logger.info(f"[Audit] {user_id} performed `{action}` on `{target_id or 'none'}` from {client_ip}")
        except Exception as e:
            logger.warning(f"[Audit] Failed to persist audit log for action `{action}`: {e}")
