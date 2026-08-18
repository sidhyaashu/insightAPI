"""Core Service — OAuth service: GitHub & Google token exchange and profile fetch."""
from __future__ import annotations

import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


async def exchange_github_code(code: str) -> dict:
    """Exchange GitHub OAuth code for access token and user profile."""
    async with httpx.AsyncClient() as client:
        # 1. Exchange code for access token
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError(f"GitHub token exchange failed: {token_data}")

        # 2. Fetch user profile
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
        user_resp.raise_for_status()
        user = user_resp.json()

        # 3. Fetch primary email (if not public on profile)
        email = user.get("email")
        if not email:
            email_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            emails = email_resp.json()
            primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
            email = primary["email"] if primary else f"{user['id']}@github.noemail"

    return {
        "provider": "github",
        "sub": str(user["id"]),
        "email": email,
        "name": user.get("name") or user.get("login"),
        "avatar_url": user.get("avatar_url"),
    }


async def exchange_google_code(code: str, redirect_uri: str) -> dict:
    """Exchange Google OAuth code for access token and user profile."""
    async with httpx.AsyncClient() as client:
        # 1. Exchange code for tokens
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError(f"Google token exchange failed: {token_data}")

        # 2. Fetch user profile
        user_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_resp.raise_for_status()
        user = user_resp.json()

    return {
        "provider": "google",
        "sub": user["id"],
        "email": user["email"],
        "name": user.get("name"),
        "avatar_url": user.get("picture"),
    }
