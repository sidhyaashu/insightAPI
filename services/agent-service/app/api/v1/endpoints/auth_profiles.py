"""
Auth Profiles Router — Manage stored target login credentials and automated test flows.
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.audit import AuditLogger
from app.repositories.auth_profile_repo import AuthProfileRepository
from app.engine.auth.executor import AutoLoginExecutor
from app.models.auth_profile import AuthProfile
from app.core.domain_verifier import normalize_domain

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateAuthProfileRequest(BaseModel):
    name: str = Field(..., description="Human-friendly profile name (e.g. 'Staging Admin User')")
    target_domain: Optional[str] = Field(default=None, description="Apex domain or hostname (defaults to login_url domain)")
    login_url: str = Field(..., description="Target application login page URL")
    auth_type: str = Field(default="form", description="Authentication type: 'form', 'oauth_google', 'oauth_github', 'saml'")
    credentials: Dict[str, Any] = Field(..., description="Credentials dictionary (username, password, client_id, etc.)")
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
    auth_type: str = "form"
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
    """Execute live automated login test for an existing AuthProfile."""
    repo = AuthProfileRepository(db)
    profile = await repo.get_profile(profile_id=profile_id, user_id=x_user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Auth profile not found.")

    success, error_msg, diagnostics = await AutoLoginExecutor.test_profile_login(profile, headless=True)
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
    """Test automated login credentials before saving to database."""
    clean_domain = normalize_domain(body.login_url)
    profile = AuthProfile(
        id="transient-test",
        user_id=x_user_id,
        name="Transient Test",
        target_domain=clean_domain,
        login_url=body.login_url,
        auth_type=body.auth_type,
        encrypted_credentials="",
    )
    profile.get_decrypted_credentials = lambda: body.credentials

    success, error_msg, diagnostics = await AutoLoginExecutor.test_profile_login(profile, headless=True)
    return {
        "success": success,
        "status": "success" if success else "failed",
        "error": error_msg,
        "diagnostics": diagnostics or {},
    }

