"""
Domains router — Domain verification and ownership challenge management.
"""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.domain_repo import DomainRepository
from app.core.domain_verifier import DomainVerifier, normalize_domain

logger = logging.getLogger(__name__)

router = APIRouter()


class VerifyDomainRequest(BaseModel):
    domain: str = Field(..., description="The hostname or target URL to verify ownership for.")


class CheckDomainRequest(BaseModel):
    method: Optional[str] = Field(default="auto", description="Verification method: 'auto', 'dns', or 'well_known'")


def _format_domain_response(record) -> dict:
    clean_domain = record.domain
    token = record.verification_token
    return {
        "id": record.id,
        "domain": clean_domain,
        "verification_token": token,
        "verification_method": record.verification_method,
        "is_verified": record.is_verified,
        "verified_at": record.verified_at.isoformat() if record.verified_at else None,
        "created_at": record.created_at.isoformat(),
        "instructions": {
            "dns": {
                "record_type": "TXT",
                "host": f"_insightapi-challenge.{clean_domain}",
                "value": token,
                "description": f"Add a DNS TXT record with host '_insightapi-challenge.{clean_domain}' and value '{token}'",
            },
            "well_known": {
                "file_path": "/.well-known/insightapi-verification.txt",
                "target_url": f"https://{clean_domain}/.well-known/insightapi-verification.txt",
                "content": token,
                "description": f"Serve a plain text file containing '{token}' at https://{clean_domain}/.well-known/insightapi-verification.txt",
            },
        },
    }


@router.post("/verify")
async def initiate_domain_verification(
    request: VerifyDomainRequest,
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """
    Issue a new or retrieve an existing domain verification token.
    Provides DNS TXT and well-known file instructions.
    """
    clean_domain = normalize_domain(request.domain)
    if not clean_domain:
        raise HTTPException(status_code=400, detail="Invalid domain name supplied.")

    repo = DomainRepository(db)
    record = await repo.get_or_create_domain(user_id=x_user_id, domain=clean_domain)
    return _format_domain_response(record)


@router.post("/{domain}/check")
async def check_domain_verification(
    domain: str,
    body: Optional[CheckDomainRequest] = None,
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """
    Validate DNS TXT record or well-known HTTP file for a registered domain.
    Marks domain as verified upon detection.
    """
    clean_domain = normalize_domain(domain)
    repo = DomainRepository(db)
    record = await repo.get_domain(user_id=x_user_id, domain=clean_domain)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Domain '{clean_domain}' has not been registered for verification. Call POST /verify first.",
        )

    if record.is_verified:
        return {
            "verified": True,
            "domain": clean_domain,
            "verification_method": record.verification_method,
            "message": "Domain is already verified.",
        }

    method = (body.method if body else "auto") or "auto"
    verifier = DomainVerifier(timeout=10.0)
    is_valid, verified_method = await verifier.verify(
        domain=clean_domain,
        token=record.verification_token,
        method=method,
    )

    if is_valid and verified_method:
        updated_record = await repo.mark_domain_verified(record.id, verified_method)
        return {
            "verified": True,
            "domain": clean_domain,
            "verification_method": verified_method,
            "message": f"Domain ownership verified successfully via {verified_method}.",
            "domain_record": _format_domain_response(updated_record),
        }

    return {
        "verified": False,
        "domain": clean_domain,
        "detail": (
            "Verification challenge not found. Please ensure the DNS TXT record "
            f"'_insightapi-challenge.{clean_domain}' or well-known file at "
            f"'https://{clean_domain}/.well-known/insightapi-verification.txt' is accessible."
        ),
    }


@router.get("")
async def list_verified_domains(
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """List all registered and verified domains for authenticated user."""
    repo = DomainRepository(db)
    domains = await repo.list_user_domains(user_id=x_user_id)
    return [_format_domain_response(d) for d in domains]


@router.get("/status")
async def check_domain_status(
    domain: str = Query(..., description="Domain or URL to check verification status for"),
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """Check if a given domain or URL is verified for the authenticated user."""
    clean_domain = normalize_domain(domain)
    repo = DomainRepository(db)
    is_verified = await repo.is_domain_verified(user_id=x_user_id, domain=clean_domain)
    return {
        "domain": clean_domain,
        "is_verified": is_verified,
    }


@router.delete("/{domain}")
async def delete_domain(
    domain: str,
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """Remove domain verification record."""
    clean_domain = normalize_domain(domain)
    repo = DomainRepository(db)
    deleted = await repo.delete_domain(user_id=x_user_id, domain=clean_domain)
    if not deleted:
        raise HTTPException(status_code=404, detail="Domain not found.")
    return {"message": f"Domain '{clean_domain}' removed successfully."}
