"""
Repository layer for managing stored Auth Profiles in PostgreSQL.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_profile import AuthProfile
from app.core.encryption import encrypt_credentials
from app.core.domain_verifier import normalize_domain

logger = logging.getLogger(__name__)


class AuthProfileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_profile(
        self,
        user_id: str,
        name: str,
        target_domain: str,
        login_url: str,
        auth_type: str,
        credentials: Dict[str, Any],
        project_id: str = "default",
    ) -> AuthProfile:
        """Create and persist a new encrypted AuthProfile."""
        clean_domain = normalize_domain(target_domain or login_url)
        encrypted_token = encrypt_credentials(credentials)

        profile = AuthProfile(
            user_id=user_id,
            project_id=project_id,
            name=name.strip(),
            target_domain=clean_domain,
            login_url=login_url.strip(),
            auth_type=auth_type.lower(),
            encrypted_credentials=encrypted_token,
        )
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        logger.info(f"Created auth profile '{profile.name}' (id={profile.id}) for domain '{clean_domain}'")
        return profile

    async def get_profile(self, profile_id: str, user_id: str) -> Optional[AuthProfile]:
        """Fetch an auth profile by ID owned by user_id."""
        stmt = select(AuthProfile).where(
            AuthProfile.id == profile_id,
            AuthProfile.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_profiles(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        target_domain: Optional[str] = None,
    ) -> List[AuthProfile]:
        """List all auth profiles owned by user_id, optionally filtered by project or domain."""
        stmt = select(AuthProfile).where(AuthProfile.user_id == user_id)
        if project_id:
            stmt = stmt.where(AuthProfile.project_id == project_id)
        if target_domain:
            clean_dom = normalize_domain(target_domain)
            stmt = stmt.where(AuthProfile.target_domain == clean_dom)

        stmt = stmt.order_by(AuthProfile.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_profile(
        self,
        profile_id: str,
        user_id: str,
        name: Optional[str] = None,
        target_domain: Optional[str] = None,
        login_url: Optional[str] = None,
        auth_type: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
    ) -> Optional[AuthProfile]:
        """Update an existing auth profile."""
        profile = await self.get_profile(profile_id, user_id)
        if not profile:
            return None

        if name is not None:
            profile.name = name.strip()
        if target_domain is not None:
            profile.target_domain = normalize_domain(target_domain)
        if login_url is not None:
            profile.login_url = login_url.strip()
        if auth_type is not None:
            profile.auth_type = auth_type.lower()
        if project_id is not None:
            profile.project_id = project_id
        if credentials is not None:
            profile.encrypted_credentials = encrypt_credentials(credentials)

        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def update_test_status(
        self,
        profile_id: str,
        user_id: str,
        status: str,
        error: Optional[str] = None,
    ) -> Optional[AuthProfile]:
        """Record live test execution results."""
        profile = await self.get_profile(profile_id, user_id)
        if not profile:
            return None

        profile.last_tested_at = datetime.now(timezone.utc)
        profile.last_test_status = status
        profile.last_test_error = error
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def delete_profile(self, profile_id: str, user_id: str) -> bool:
        """Delete an auth profile."""
        stmt = delete(AuthProfile).where(
            AuthProfile.id == profile_id,
            AuthProfile.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
