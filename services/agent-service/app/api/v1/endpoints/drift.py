"""API Drift Detection — REST endpoints

GET  /api/v1/projects/{project_id}/drift
     ?base={crawl_id}&compare={crawl_id}
     — Returns a structured DriftReport comparing two crawl snapshots.
       ``base`` is optional; omit it to auto-detect the most recent prior crawl.

POST /api/v1/projects/{project_id}/drift/webhook
     — Fires an outbound HTTP POST to a configured CI webhook URL when
       breaking_changes exist.  Includes 3-attempt retry with exponential backoff.

Both endpoints are gated behind the PRO tier (FREE and STARTER receive 403).
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.drift import compare_snapshots, DriftReport
from app.repositories.snapshot_repo import SnapshotRepository

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Tiers allowed to use drift detection ─────────────────────────────────────
_DRIFT_ALLOWED_TIERS = {"PRO", "ENTERPRISE", "ADMIN"}

# ── SSRF blocked networks (same set as crawls.py) ────────────────────────────
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
]


def _require_pro_tier(tier: str) -> None:
    """Raise 403 if *tier* is below PRO."""
    if (tier or "FREE").upper() not in _DRIFT_ALLOWED_TIERS:
        raise HTTPException(
            status_code=403,
            detail=(
                "API Drift Detection requires a PRO plan or higher. "
                "Upgrade at /billing to unlock this feature."
            ),
        )


def _validate_webhook_url_ssrf(url: str) -> None:
    """Block webhook URLs that resolve to internal/private network ranges."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported webhook URL scheme '{parsed.scheme}'. Only http and https are allowed.",
        )
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid webhook URL: no hostname.")
    if hostname.lower() in {"localhost", "127.0.0.1", "::1", "169.254.169.254"}:
        raise HTTPException(
            status_code=400,
            detail=f"SSRF Protection: webhook target '{hostname}' is forbidden.",
        )
    try:
        ip = ipaddress.ip_address(hostname)
        for net in _BLOCKED_NETWORKS:
            if ip in net:
                raise HTTPException(
                    status_code=400,
                    detail=f"SSRF Protection: webhook IP '{ip}' is in a restricted private network.",
                )
    except ValueError:
        pass  # hostname is a domain — DNS resolution happens at fire time


async def _fire_webhook_with_retry(
    webhook_url: str,
    payload: dict,
    max_attempts: int = 3,
    base_delay: float = 1.0,
) -> bool:
    """POST *payload* to *webhook_url* with up to *max_attempts* retries.

    Uses exponential backoff (1s, 2s, 4s).  Returns True if any attempt succeeds
    (HTTP 2xx from the receiver), False otherwise.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        for attempt in range(1, max_attempts + 1):
            try:
                resp = await client.post(webhook_url, json=payload)
                if resp.is_success:
                    logger.info(f"Webhook delivered on attempt {attempt}: {webhook_url}")
                    return True
                logger.warning(
                    f"Webhook attempt {attempt} returned HTTP {resp.status_code} from {webhook_url}"
                )
            except Exception as exc:
                logger.warning(f"Webhook attempt {attempt} failed ({exc}): {webhook_url}")

            if attempt < max_attempts:
                await asyncio.sleep(base_delay * (2 ** (attempt - 1)))

    logger.error(f"Webhook delivery failed after {max_attempts} attempts: {webhook_url}")
    return False


# ── Request / Response schemas ────────────────────────────────────────────────

class WebhookRequest(BaseModel):
    compare_crawl_id: str
    webhook_url: str
    base_crawl_id: Optional[str] = None  # auto-detected when omitted


class WebhookResponse(BaseModel):
    fired: bool
    breaking_change_count: int
    compare_crawl_id: str
    base_crawl_id: str
    has_breaking_changes: bool


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/{project_id}/drift", response_model=DriftReport)
async def get_drift_report(
    project_id: str,
    compare: str = Query(..., description="The candidate crawl session ID to compare."),
    base: Optional[str] = Query(
        None,
        description="The reference crawl session ID. Omit to auto-detect the most recent prior crawl for this project.",
    ),
    x_user_id: str = Header(..., alias="x-user-id"),
    x_user_tier: str = Header("FREE", alias="x-user-tier"),
    db: AsyncSession = Depends(get_db),
):
    """Compare two crawl snapshots and return a structured drift report.

    - Requires **PRO** tier or above.
    - ``project_id`` must match the authenticated user's ID.
    - If ``base`` is omitted, the most recent prior completed crawl for this
      project is used automatically.
    """
    _require_pro_tier(x_user_tier)

    # Ownership guard — users may only query their own project
    if x_user_id != project_id:
        raise HTTPException(status_code=403, detail="You do not have access to this project.")

    # Auto-detect base crawl when not supplied
    resolved_base = base
    if not resolved_base:
        repo = SnapshotRepository(db)
        resolved_base = await repo.get_latest_crawl_id_for_project(
            project_id=project_id,
            exclude_crawl_id=compare,
        )
        if not resolved_base:
            raise HTTPException(
                status_code=404,
                detail=(
                    "No prior crawl snapshot found for this project. "
                    "Run at least two crawls before requesting a drift report, "
                    "or supply the 'base' query parameter explicitly."
                ),
            )

    if resolved_base == compare:
        raise HTTPException(
            status_code=400,
            detail="'base' and 'compare' must be different crawl IDs.",
        )

    try:
        report = await compare_snapshots(
            base_crawl_id=resolved_base,
            compare_crawl_id=compare,
            db=db,
        )
    except Exception as exc:
        logger.error(f"Drift comparison failed for project {project_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Drift comparison failed: {exc}")

    return report


@router.post("/{project_id}/drift/webhook", response_model=WebhookResponse)
async def trigger_drift_webhook(
    project_id: str,
    body: WebhookRequest,
    http_request: Request = None,
    x_user_id: str = Header(..., alias="x-user-id"),
    x_user_tier: str = Header("FREE", alias="x-user-tier"),
    db: AsyncSession = Depends(get_db),
):
    """Run drift comparison and fire a webhook POST if breaking changes exist.

    - Requires **PRO** tier or above.
    - Webhook is fired only when ``has_breaking_changes=True``.
    - Webhook delivery is retried up to 3 times with exponential backoff.
    - The webhook URL is validated against SSRF attack vectors before use.
    """
    _require_pro_tier(x_user_tier)

    if x_user_id != project_id:
        raise HTTPException(status_code=403, detail="You do not have access to this project.")

    # SSRF guard on user-supplied webhook URL
    _validate_webhook_url_ssrf(body.webhook_url)

    # Resolve base crawl
    resolved_base = body.base_crawl_id
    if not resolved_base:
        repo = SnapshotRepository(db)
        resolved_base = await repo.get_latest_crawl_id_for_project(
            project_id=project_id,
            exclude_crawl_id=body.compare_crawl_id,
        )
        if not resolved_base:
            raise HTTPException(
                status_code=404,
                detail="No prior crawl snapshot found to use as base. Supply 'base_crawl_id' explicitly.",
            )

    try:
        report = await compare_snapshots(
            base_crawl_id=resolved_base,
            compare_crawl_id=body.compare_crawl_id,
            db=db,
        )
    except Exception as exc:
        logger.error(f"Drift comparison failed for webhook {project_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Drift comparison failed: {exc}")

    fired = False
    if report.has_breaking_changes:
        payload = report.model_dump(mode="json")
        payload["source"] = "insightapi-drift-webhook"
        fired = await _fire_webhook_with_retry(body.webhook_url, payload)

    # Record audit log
    from app.core.audit import AuditLogger
    await AuditLogger.log_event(
        db=db,
        user_id=x_user_id,
        action="drift_webhook.trigger",
        target_id=project_id,
        request=http_request,
        metadata={
            "webhook_url": body.webhook_url,
            "fired": fired,
            "has_breaking_changes": report.has_breaking_changes,
            "breaking_count": report.summary.breaking_count,
        },
    )

    return WebhookResponse(
        fired=fired,
        breaking_change_count=report.summary.breaking_count,
        compare_crawl_id=body.compare_crawl_id,
        base_crawl_id=resolved_base,
        has_breaking_changes=report.has_breaking_changes,
    )

