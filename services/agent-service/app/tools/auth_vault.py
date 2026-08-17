"""Auth profile vault and secure credential injector."""
from __future__ import annotations

import base64
import logging
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def resolve_auth_headers(
    user_id: str,
    domain_or_url: str,
    auth_profile_id: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> Dict[str, str]:
    """
    Resolve and build request authentication headers for a given user and target domain.
    If auth_profile_id is provided, loads that specific profile. Otherwise matches by domain.
    """
    if not user_id or not db:
        return {}

    try:
        from app.models.auth_profile import AuthProfile

        query = select(AuthProfile).where(AuthProfile.user_id == user_id)
        if auth_profile_id:
            query = query.where(AuthProfile.id == auth_profile_id)
        else:
            # Extract domain from domain_or_url
            import urllib.parse
            parsed = urllib.parse.urlparse(domain_or_url)
            hostname = (parsed.hostname or domain_or_url).lower()
            query = query.where(AuthProfile.target_domain.ilike(f"%{hostname}%"))

        result = await db.execute(query)
        profile = result.scalars().first()
        if not profile:
            return {}

        headers: Dict[str, str] = {}
        creds = profile.credentials or {}
        auth_type = (profile.auth_type or "bearer").lower()

        if auth_type in ("bearer", "token", "jwt"):
            token = creds.get("token") or creds.get("bearer_token") or creds.get("jwt") or creds.get("access_token")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif auth_type in ("api_key", "apikey"):
            header_name = creds.get("header_name") or "X-API-Key"
            api_key = creds.get("api_key") or creds.get("key") or creds.get("token")
            if api_key:
                headers[header_name] = api_key

        elif auth_type in ("basic", "basic_auth"):
            username = creds.get("username") or ""
            password = creds.get("password") or ""
            if username or password:
                encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"

        elif auth_type in ("cookie", "session", "form"):
            cookie_val = creds.get("cookie") or creds.get("session_token")
            if cookie_val:
                headers["Cookie"] = cookie_val

        return headers

    except Exception as e:
        logger.warning(f"Error resolving auth headers for {domain_or_url}: {e}")
        return {}
