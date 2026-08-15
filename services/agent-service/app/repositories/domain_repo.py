"""
Domain Repository — Persistence operations for verified domains and ToS audit logs.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain_verification import VerifiedDomain, TosAcceptance
from app.core.domain_verifier import generate_verification_token, normalize_domain

logger = logging.getLogger(__name__)


class DomainRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_domain(self, user_id: str, domain: str) -> VerifiedDomain:
        """Retrieve existing domain record or issue new verification token."""
        clean_domain = normalize_domain(domain)
        stmt = select(VerifiedDomain).where(
            VerifiedDomain.user_id == user_id,
            VerifiedDomain.domain == clean_domain,
        )
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()

        if not record:
            token = generate_verification_token()
            record = VerifiedDomain(
                user_id=user_id,
                domain=clean_domain,
                verification_token=token,
                is_verified=False,
            )
            self.session.add(record)
            await self.session.commit()
            await self.session.refresh(record)

        return record

    async def get_domain(self, user_id: str, domain: str) -> VerifiedDomain | None:
        """Get domain verification record for user."""
        clean_domain = normalize_domain(domain)
        stmt = select(VerifiedDomain).where(
            VerifiedDomain.user_id == user_id,
            VerifiedDomain.domain == clean_domain,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def is_domain_verified(self, user_id: str, domain: str) -> bool:
        """
        Check if domain (or its parent apex domain) is verified for user.
        Example: if user verified 'example.com', 'api.example.com' is also considered verified.
        """
        clean_domain = normalize_domain(domain)
        if not clean_domain:
            return False

        # Generate candidate domains (exact hostname and apex domains)
        parts = clean_domain.split(".")
        candidates = [clean_domain]
        if len(parts) > 2:
            # e.g., 'sub.api.example.com' -> ['sub.api.example.com', 'api.example.com', 'example.com']
            for i in range(1, len(parts) - 1):
                candidates.append(".".join(parts[i:]))

        stmt = select(VerifiedDomain).where(
            VerifiedDomain.user_id == user_id,
            VerifiedDomain.domain.in_(candidates),
            VerifiedDomain.is_verified == True,
        )
        res = await self.session.execute(stmt)
        verified_match = res.scalar_one_or_none()
        return verified_match is not None

    async def is_domain_opted_in_for_active_testing(self, user_id: str, domain: str) -> bool:
        """
        Check if domain is verified AND has active_testing_opt_in explicitly set to True.
        """
        clean_domain = normalize_domain(domain)
        if not clean_domain:
            return False

        parts = clean_domain.split(".")
        candidates = [clean_domain]
        if len(parts) > 2:
            for i in range(1, len(parts) - 1):
                candidates.append(".".join(parts[i:]))

        stmt = select(VerifiedDomain).where(
            VerifiedDomain.user_id == user_id,
            VerifiedDomain.domain.in_(candidates),
            VerifiedDomain.is_verified == True,
            VerifiedDomain.active_testing_opt_in == True,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def set_active_testing_opt_in(self, user_id: str, domain: str, opt_in: bool = True) -> VerifiedDomain | None:
        """Update active_testing_opt_in flag for a domain."""
        clean_domain = normalize_domain(domain)
        stmt = select(VerifiedDomain).where(
            VerifiedDomain.user_id == user_id,
            VerifiedDomain.domain == clean_domain,
        )
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()
        if record:
            record.active_testing_opt_in = opt_in
            record.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(record)
        return record

    async def mark_domain_verified(self, domain_id: str, method: str) -> VerifiedDomain | None:
        """Mark a domain record as successfully verified."""
        stmt = select(VerifiedDomain).where(VerifiedDomain.id == domain_id)
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()
        if record:
            record.is_verified = True
            record.verification_method = method
            record.verified_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(record)
        return record

    async def list_user_domains(self, user_id: str) -> list[VerifiedDomain]:
        """List all verified and pending domains for a user."""
        stmt = select(VerifiedDomain).where(
            VerifiedDomain.user_id == user_id
        ).order_by(VerifiedDomain.created_at.desc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def delete_domain(self, user_id: str, domain: str) -> bool:
        """Delete domain verification record."""
        clean_domain = normalize_domain(domain)
        stmt = delete(VerifiedDomain).where(
            VerifiedDomain.user_id == user_id,
            VerifiedDomain.domain == clean_domain,
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount > 0

    async def record_tos_acceptance(
        self,
        user_id: str,
        domain: str,
        target_url: str,
        user_ip: str,
        tos_version: str = "v1.0",
    ) -> TosAcceptance:
        """Persist a legal ToS acceptance audit log record."""
        clean_domain = normalize_domain(domain)
        acceptance = TosAcceptance(
            user_id=user_id,
            domain=clean_domain,
            target_url=target_url,
            user_ip=user_ip or "unknown",
            tos_version=tos_version,
            accepted_at=datetime.now(timezone.utc),
        )
        self.session.add(acceptance)
        await self.session.commit()
        await self.session.refresh(acceptance)
        logger.info(f"Recorded ToS acceptance for user {user_id}, target {target_url} (IP: {user_ip})")
        return acceptance
