"""
Auth Profiles Router — Manage stored target API credentials and automated test flows.
"""
from __future__ import annotations

import logging
import httpx
from typing import Optional, Dict, Any, List, Tuple
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.audit import AuditLogger
from app.repositories.auth_profile_repo import AuthProfileRepository
from app.models.auth_profile import AuthProfile
from app.core.domain_verifier import normalize_domain

logger = logging.getLogger(__name__)

router = APIRouter()


async def _verify_http_credentials(login_url: str, auth_type: str, creds: Dict[str, Any]) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Lightweight HTTP credentials tester for API keys, Bearer tokens, Basic Auth, and login forms.
    """
    headers = {"User-Agent": "InsightAPI-Verifier/2.0"}
    diagnostics: Dict[str, Any] = {"auth_type": auth_type, "target_url": login_url}

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            token = creds.get("token") or creds.get("bearer_token") or creds.get("api_key")
            username = creds.get("username") or creds.get("email")
            password = creds.get("password")

            if auth_type in ("bearer", "token") or token:
                headers["Authorization"] = f"Bearer {token}" if not str(token).lower().startswith("bearer ") else token
                resp = await client.get(login_url, headers=headers)
            elif auth_type == "basic" and username and password:
                resp = await client.get(login_url, headers=headers, auth=(username, password))
            elif auth_type == "api_key":
                header_name = creds.get("header_name", "X-API-Key")
                headers[header_name] = token or password or ""
                resp = await client.get(login_url, headers=headers)
            else:
                # Default / form login probe
                resp = await client.post(login_url, headers=headers, data=creds)

            diagnostics["status_code"] = resp.status_code
            diagnostics["response_headers"] = dict(resp.headers)

            if resp.status_code < 400:
                return True, None, diagnostics
            else:
                return False, f"Server responded with status code {resp.status_code}", diagnostics
    except httpx.TimeoutException:
        return False, "Connection timed out while verifying credentials.", diagnostics
    except Exception as e:
        logger.warning(f"Auth verification error for {login_url}: {e}")
        return False, str(e), diagnostics


class CreateAuthProfileRequest(BaseModel):
    name: str = Field(..., description="Human-friendly profile name (e.g. 'Staging Admin User')")
    target_domain: Optional[str] = Field(default=None, description="Apex domain or hostname (defaults to login_url domain)")
    login_url: str = Field(..., description="Target application login page or API URL")
    auth_type: str = Field(default="bearer", description="Authentication type: 'bearer', 'api_key', 'basic', 'form'")
    credentials: Dict[str, Any] = Field(..., description="Credentials dictionary (token, username, password, api_key, etc.)")
    project_id: Optional[str] = Field(default="default", description="Optional project partition ID")


class UpdateAuthProfileRequest(BaseModel):
    name: Optional[str] = None
    target_domain: Optional[str] = None
    login_url: Optional[str] = None
    auth_type: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    project_id: Optional[str] = None


class TestAuthProfileRequest(BaseModel):
    login_url: str
    auth_type: str = "bearer"
    credentials: Dict[str, Any]


@router.post("", status_code=201)
async def create_auth_profile(
    body: CreateAuthProfileRequest,
    http_request: Request = None,
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """Create and persist a new encrypted AuthProfile with audit logging."""
    clean_domain = normalize_domain(body.target_domain or body.login_url)
    if not clean_domain:
        raise HTTPException(status_code=400, detail="Invalid target domain or login URL.")

    repo = AuthProfileRepository(db)
    profile = await repo.create_profile(
        user_id=x_user_id,
        name=body.name,
        target_domain=clean_domain,
        login_url=body.login_url,
        auth_type=body.auth_type,
        credentials=body.credentials,
        project_id=body.project_id or "default",
    )

    await AuditLogger.log_event(
        db=db,
        user_id=x_user_id,
        action="auth_profile.create",
        target_id=profile.id,
        request=http_request,
        project_id=body.project_id or "default",
        metadata={"domain": clean_domain, "auth_type": body.auth_type, "name": body.name},
    )

    return profile.to_dict(mask_secrets=True)


@router.get("")
async def list_auth_profiles(
    project_id: Optional[str] = Query(default=None),
    domain: Optional[str] = Query(default=None),
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """List all auth profiles owned by user, returning masked credentials."""
    repo = AuthProfileRepository(db)
    profiles = await repo.list_profiles(user_id=x_user_id, project_id=project_id, target_domain=domain)
    return [p.to_dict(mask_secrets=True) for p in profiles]


@router.get("/{profile_id}")
async def get_auth_profile(
    profile_id: str,
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single auth profile with masked secrets and tenant verification."""
    repo = AuthProfileRepository(db)
    profile = await repo.get_profile(profile_id=profile_id, user_id=x_user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Auth profile not found.")
    return profile.to_dict(mask_secrets=True)


@router.patch("/{profile_id}")
async def update_auth_profile(
    profile_id: str,
    body: UpdateAuthProfileRequest,
    http_request: Request = None,
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """Update existing auth profile with audit logging."""
    repo = AuthProfileRepository(db)
    profile = await repo.update_profile(
        profile_id=profile_id,
        user_id=x_user_id,
        name=body.name,
        target_domain=body.target_domain,
        login_url=body.login_url,
        auth_type=body.auth_type,
        credentials=body.credentials,
        project_id=body.project_id,
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Auth profile not found.")

    await AuditLogger.log_event(
        db=db,
        user_id=x_user_id,
        action="auth_profile.update",
        target_id=profile_id,
        request=http_request,
        metadata={"domain": body.target_domain, "auth_type": body.auth_type},
    )

    return profile.to_dict(mask_secrets=True)


@router.delete("/{profile_id}")
async def delete_auth_profile(
    profile_id: str,
    http_request: Request = None,
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """Delete an auth profile with audit logging."""
    repo = AuthProfileRepository(db)
    deleted = await repo.delete_profile(profile_id=profile_id, user_id=x_user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Auth profile not found.")

    await AuditLogger.log_event(
        db=db,
        user_id=x_user_id,
        action="auth_profile.delete",
        target_id=profile_id,
        request=http_request,
    )

    return {"message": "Auth profile deleted successfully."}


@router.post("/{profile_id}/test")
async def test_auth_profile(
    profile_id: str,
    http_request: Request = None,
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """Execute live credential verification for an existing AuthProfile."""
    repo = AuthProfileRepository(db)
    profile = await repo.get_profile(profile_id=profile_id, user_id=x_user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Auth profile not found.")

    creds = profile.get_decrypted_credentials()
    success, error_msg, diagnostics = await _verify_http_credentials(profile.login_url, profile.auth_type, creds)
    status_str = "success" if success else "failed"
    await repo.update_test_status(profile_id=profile.id, user_id=x_user_id, status=status_str, error=error_msg)

    await AuditLogger.log_event(
        db=db,
        user_id=x_user_id,
        action="auth_profile.test",
        target_id=profile_id,
        request=http_request,
        metadata={"status": status_str, "success": success},
    )

    return {
        "success": success,
        "profile_id": profile.id,
        "status": status_str,
        "error": error_msg,
        "diagnostics": diagnostics or {},
    }


@router.post("/test-transient")
async def test_transient_auth_profile(
    body: TestAuthProfileRequest,
    x_user_id: str = Header(..., alias="x-user-id"),
):
    """Test API credentials before saving to database."""
    success, error_msg, diagnostics = await _verify_http_credentials(body.login_url, body.auth_type, body.credentials)
    return {
        "success": success,
        "status": "success" if success else "failed",
        "error": error_msg,
        "diagnostics": diagnostics or {},
    }
