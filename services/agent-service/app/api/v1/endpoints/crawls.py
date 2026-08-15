import asyncio
import uuid
import logging
import json
import ipaddress
from urllib.parse import urlparse
from typing import Optional, Dict, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Header, Depends, Request, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.sdk import AgentEngine
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.repositories.crawl_repo import CrawlRepository
from app.repositories.domain_repo import DomainRepository
from app.core.domain_verifier import normalize_domain

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory fallback session store (for lightweight SDK/CLI runs without DB)
CRAWL_SESSIONS: Dict[str, Dict[str, Any]] = {}


class CrawlRequest(BaseModel):
    target_url: Optional[str] = Field(default=None, alias="url")
    url: Optional[str] = None
    max_pages: Optional[int] = 10
    headless: Optional[bool] = True
    goal: Optional[str] = Field(
        default=None,
        description="Optional natural-language crawl objective to guide LLM exploration."
    )
    parallel: Optional[bool] = Field(
        default=False,
        description="When True, decomposes application into sections and launches parallel crawler sub-agents."
    )
    max_agents: Optional[int] = Field(
        default=1,
        description="Number of parallel sub-agent workers (default: 1, max safety limit: 5)."
    )
    session_state: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional Playwright storage_state dict (cookies + localStorage)."
    )
    require_review: bool = Field(
        default=False,
        description="When True, crawl transitions to pending_review after analysis. Exporters run only after POST /crawls/{id}/approve."
    )
    tos_accepted: bool = Field(
        default=False,
        description="When True, certifies authorization to crawl target domain and accepts Terms of Service."
    )
    auth_profile_id: Optional[str] = Field(
        default=None,
        description="Optional AuthProfile ID for automated authenticated login before crawl."
    )

    def get_url(self) -> str:
        res = self.target_url or self.url
        if not res:
            raise ValueError("Target URL is required.")
        return res


class CrawlResponse(BaseModel):
    session_id: str
    status: str
    target_url: str


BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
]


def validate_target_url_ssrf(url: str):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are allowed."
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid target URL.")

    if hostname.lower() in {"localhost", "127.0.0.1", "::1", "169.254.169.254"}:
        raise HTTPException(
            status_code=400,
            detail=f"SSRF Protection: Access to private target '{hostname}' is forbidden."
        )

    try:
        ip = ipaddress.ip_address(hostname)
        for net in BLOCKED_IP_NETWORKS:
            if ip in net:
                raise HTTPException(
                    status_code=400,
                    detail=f"SSRF Protection: Target IP '{ip}' is in restricted private network range."
                )
    except ValueError:
        pass


async def publish_ws_event(session_id: str, event: dict):
    """Publish a log or status event to Redis PubSub for WebSocket streaming."""
    try:
        redis = await get_redis_client()
        channel = f"crawl:{session_id}:events"
        await redis.publish(channel, json.dumps(event))
    except Exception as e:
        logger.warning(f"Failed to publish WS event for {session_id}: {e}")


async def _report_metered_usage(user_id: str, session_id: str, url: str):
    """Dispatch pay-per-crawl metered usage to core-service payments endpoint."""
    try:
        import httpx
        from app.core.config import settings
        core_url = getattr(settings, "CORE_SERVICE_URL", "http://localhost:8000")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{core_url}/api/v1/payments/usage-records",
                json={
                    "user_id": user_id,
                    "crawl_id": session_id,
                    "quantity": 1,
                    "description": f"Pay-per-crawl execution for {url}",
                },
                headers={"x-user-id": user_id},
            )
            logger.info(f"Reported metered crawl usage for user {user_id}, session {session_id}: status={resp.status_code}")
    except Exception as usage_err:
        logger.warning(f"Failed to report metered crawl usage for {session_id} (non-fatal): {usage_err}")


async def run_background_crawl(
    session_id: str,
    url: str,
    max_pages: int,
    headless: bool,
    user_id: str,
    user_tier: str,
    session_state: Optional[Dict[str, Any]] = None,
    auth_profile_id: Optional[str] = None,
    goal: Optional[str] = None,
    parallel: bool = False,
    max_agents: int = 1,
    require_review: bool = False,
    is_overage: bool = False,
):
    """Background task running AgentEngine exploration and publishing WS events."""
    await publish_ws_event(session_id, {"type": "log", "message": f"Starting crawl engine for {url}..."})

    # ── Automated AuthProfile Login Resolution ─────────────────────────────
    if auth_profile_id and session_state is None:
        try:
            from app.core.database import AsyncSessionLocal
            from app.repositories.auth_profile_repo import AuthProfileRepository
            from app.engine.auth.executor import AutoLoginExecutor

            await publish_ws_event(
                session_id,
                {"type": "log", "message": "Executing automated login flow with stored AuthProfile..."},
            )
            async with AsyncSessionLocal() as auth_db:
                auth_repo = AuthProfileRepository(auth_db)
                profile = await auth_repo.get_profile(profile_id=auth_profile_id, user_id=user_id)
                if profile:
                    session_state = await AutoLoginExecutor.execute_login(profile, headless=headless)
                    cookies_count = len(session_state.get("cookies", []))
                    await publish_ws_event(
                        session_id,
                        {
                            "type": "log",
                            "message": f"✓ Automated login succeeded for '{profile.name}'. Captured {cookies_count} session cookies.",
                        },
                    )
                else:
                    logger.warning(f"Auth profile {auth_profile_id} not found for user {user_id}. Proceeding unauthenticated.")
        except Exception as auth_err:
            logger.error(f"Automated login failed for profile {auth_profile_id}: {auth_err}")
            await publish_ws_event(
                session_id,
                {
                    "type": "log",
                    "message": f"⚠️ Automated login flow failed: {auth_err}. Attempting unauthenticated fallback...",
                },
            )

    try:
        engine = AgentEngine(headless=headless, enable_security_testing=True)
        result = await engine.crawl(
            url,
            max_pages=max_pages,
            session_state=session_state,
            goal=goal,
            parallel=parallel,
            max_agents=max_agents,
            crawl_id=session_id,
            user_id=user_id,
            enable_security_testing=True,
        )

        captured_count = len(result.captured_endpoints)

        # ── Metered Usage-based Billing ────────────────────────────────────
        if is_overage or (user_tier or "").upper() == "PAYG":
            await _report_metered_usage(user_id=user_id, session_id=session_id, url=url)

        if require_review:
            # ── Review gate: skip exporters, enter pending_review ──────────
            if session_id in CRAWL_SESSIONS:
                CRAWL_SESSIONS[session_id].update({
                    "status": "pending_review",
                    "captured_count": captured_count,
                    "action_traces": result.action_traces,
                })
            try:
                from app.core.database import AsyncSessionLocal
                async with AsyncSessionLocal() as db:
                    repo = CrawlRepository(db)
                    await repo.set_pending_review(
                        session_id=session_id,
                        captured_count=captured_count,
                        action_traces=result.action_traces,
                    )
            except Exception as db_err:
                logger.warning(f"DB pending_review update failed for crawl {session_id}: {db_err}")

            # ── Persist snapshots for review listing + drift detection ─────
            try:
                from app.core.database import AsyncSessionLocal
                from app.repositories.snapshot_repo import SnapshotRepository
                async with AsyncSessionLocal() as db:
                    snap_repo = SnapshotRepository(db)
                    inserted = await snap_repo.bulk_upsert_snapshots(
                        crawl_id=session_id,
                        project_id=user_id,
                        captured_endpoints=result.captured_endpoints,
                    )
                    logger.info(f"Crawl {session_id}: persisted {inserted} endpoint snapshots (pending_review).")
            except Exception as snap_err:
                logger.warning(f"Snapshot persistence failed for crawl {session_id} (non-fatal): {snap_err}")

            await publish_ws_event(session_id, {"type": "pending_review", "captured_count": captured_count})
            return  # Exporters run at approval time, not here

        # ── Standard path: run exporters immediately ───────────────────────
        openapi_spec = result.to_openapi()
        postman_col = result.to_postman()
        markdown_docs = result.to_markdown()

        # Update memory store
        if session_id in CRAWL_SESSIONS:
            CRAWL_SESSIONS[session_id].update({
                "status": "completed",
                "captured_count": captured_count,
                "openapi_spec": openapi_spec,
                "postman_collection": postman_col,
                "markdown_docs": markdown_docs,
                "action_traces": result.action_traces,
                "llm_metrics": result.llm_metrics,
            })

        # Update Postgres DB
        try:
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                repo = CrawlRepository(db)
                await repo.update_status(
                    session_id=session_id,
                    status="completed",
                    captured_count=captured_count,
                    openapi_spec=openapi_spec,
                    postman_collection=postman_col,
                    markdown_docs=markdown_docs,
                    action_traces=result.action_traces,
                    llm_metrics=result.llm_metrics,
                )
        except Exception as db_err:
            logger.warning(f"DB update failed for crawl {session_id}: {db_err}")

        # ── Persist endpoint snapshots for drift detection ──────────────────
        try:
            from app.core.database import AsyncSessionLocal
            from app.repositories.snapshot_repo import SnapshotRepository
            async with AsyncSessionLocal() as db:
                snap_repo = SnapshotRepository(db)
                inserted = await snap_repo.bulk_upsert_snapshots(
                    crawl_id=session_id,
                    project_id=user_id,
                    captured_endpoints=result.captured_endpoints,
                )
                logger.info(f"Crawl {session_id}: persisted {inserted} endpoint snapshots for drift tracking.")
        except Exception as snap_err:
            logger.warning(f"Snapshot persistence failed for crawl {session_id} (non-fatal): {snap_err}")

        await publish_ws_event(session_id, {"type": "complete", "captured_count": captured_count})

    except Exception as e:
        logger.error(f"Crawl session {session_id} failed: {e}")
        if session_id in CRAWL_SESSIONS:
            CRAWL_SESSIONS[session_id].update({
                "status": "failed",
                "error_message": str(e),
            })
        try:
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                repo = CrawlRepository(db)
                await repo.update_status(
                    session_id=session_id,
                    status="failed",
                    error_message=str(e),
                )
        except Exception as db_err:
            logger.warning(f"DB failed update failed for crawl {session_id}: {db_err}")

        await publish_ws_event(session_id, {"type": "error", "message": str(e)})


@router.get("")
async def list_crawl_sessions(
    x_user_id: str = Header(..., alias="x-user-id"),
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List crawl sessions for the authenticated user."""
    try:
        repo = CrawlRepository(db)
        db_sessions = await repo.get_by_user(user_id=x_user_id, limit=limit, offset=offset)
        return [s.to_dict() for s in db_sessions]
    except Exception as e:
        logger.warning(f"DB query failed, falling back to memory store: {e}")

    # Fallback to memory store
    user_sessions = [
        s for s in CRAWL_SESSIONS.values()
        if s.get("user_id") == x_user_id
    ]
    return user_sessions[offset : offset + limit]


from app.core.constants import TIER_QUOTAS, TIER_MAX_PAGES, TIER_MAX_AGENTS

@router.post("/start", response_model=CrawlResponse)
async def start_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    http_request: Request = None,
    x_user_id: str = Header(..., alias="x-user-id"),
    x_user_tier: Optional[str] = Header(default="FREE", alias="x-user-tier"),
    x_user_allow_overage: Optional[str] = Header(default="false", alias="x-user-allow-overage"),
    x_forwarded_for: Optional[str] = Header(default=None, alias="x-forwarded-for"),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an autonomous AI crawl session with domain verification, ToS gating, and tier quotas."""
    try:
        url_str = request.get_url().strip()
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

    if not url_str.startswith("http://") and not url_str.startswith("https://"):
        url_str = f"https://{url_str}"

    validate_target_url_ssrf(url_str)

    # ── Domain Ownership Verification & ToS Gating ───────────────────────────
    clean_domain = normalize_domain(url_str)
    domain_repo = DomainRepository(db)
    is_domain_verified = await domain_repo.is_domain_verified(x_user_id, clean_domain)

    if not is_domain_verified:
        if not request.tos_accepted:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Domain '{clean_domain}' is not verified for your account. "
                    "You must verify domain ownership via DNS/well-known challenge "
                    "or explicitly accept the Terms of Service & Authorized Crawling agreement."
                ),
            )
        # Log legal ToS acceptance audit record
        client_ip = "unknown"
        if x_forwarded_for and not hasattr(x_forwarded_for, "default"):
            client_ip = x_forwarded_for
        elif http_request:
            client_ip = (
                http_request.headers.get("x-forwarded-for")
                or (http_request.client.host if http_request.client else "unknown")
            )
        try:
            await domain_repo.record_tos_acceptance(
                user_id=x_user_id,
                domain=clean_domain,
                target_url=url_str,
                user_ip=client_ip,
                tos_version="v1.0",
            )
        except Exception as tos_err:
            logger.warning(f"Could not persist ToS acceptance audit record: {tos_err}")

    raw_tier = x_user_tier.default if hasattr(x_user_tier, "default") else (x_user_tier or "FREE")
    tier = str(raw_tier or "FREE").upper()
    quota_limit = TIER_QUOTAS.get(tier, 1)

    raw_overage = x_user_allow_overage.default if hasattr(x_user_allow_overage, "default") else (x_user_allow_overage or "false")
    allow_overage = str(raw_overage).lower() in ("true", "1") or tier == "PAYG"
    is_overage_run = False

    # Daily Quota Check (ADMIN and ENTERPRISE have 999999 quota)
    repo = CrawlRepository(db)
    if tier != "ADMIN" and tier != "ENTERPRISE":
        current_count, is_exceeded = await repo.check_daily_quota(x_user_id, quota_limit)
        if is_exceeded:
            if allow_overage:
                is_overage_run = True
                logger.info(
                    f"User {x_user_id} exceeded daily quota ({quota_limit}) on {tier} tier. "
                    "Allowing overage run billed via pay-per-crawl."
                )
            else:
                raise HTTPException(
                    status_code=429,
                    detail=f"Daily crawl limit reached ({quota_limit}/day on {tier} tier). Enable Pay-per-crawl overage in Billing settings to continue crawling."
                )

    # Max pages enforcement based on tier
    allowed_max_pages = TIER_MAX_PAGES.get(tier, 10)
    requested_pages = request.max_pages or 10
    max_pages = min(requested_pages, allowed_max_pages) if tier != "ADMIN" else requested_pages

    # Max agents enforcement based on tier
    allowed_max_agents = TIER_MAX_AGENTS.get(tier, 1)
    requested_agents = request.max_agents or 1
    max_agents = min(requested_agents, allowed_max_agents) if tier != "ADMIN" else requested_agents

    # Optional AuthProfile validation
    if request.auth_profile_id:
        from app.repositories.auth_profile_repo import AuthProfileRepository
        auth_repo = AuthProfileRepository(db)
        profile = await auth_repo.get_profile(profile_id=request.auth_profile_id, user_id=x_user_id)
        if not profile:
            raise HTTPException(
                status_code=400,
                detail=f"AuthProfile '{request.auth_profile_id}' was not found for your account.",
            )

    # Persist session to DB
    session_id = str(uuid.uuid4())
    try:
        db_session = await repo.create(
            user_id=x_user_id,
            user_tier=x_user_tier,
            target_url=url_str,
            max_pages=max_pages,
            goal=request.goal,
        )
        session_id = db_session.id
        await repo.increment_daily_quota(x_user_id)
    except Exception as db_err:
        logger.warning(f"Could not persist crawl session to DB: {db_err}")

    # Also store in memory
    CRAWL_SESSIONS[session_id] = {
        "session_id": session_id,
        "user_id": x_user_id,
        "status": "running",
        "target_url": url_str,
        "captured_count": 0,
        "captured_endpoints": [],
    }

    # Record enterprise compliance audit log
    from app.core.audit import AuditLogger
    await AuditLogger.log_event(
        db=db,
        user_id=x_user_id,
        action="crawl.create",
        target_id=session_id,
        request=http_request,
        metadata={
            "target_url": url_str,
            "max_pages": max_pages,
            "goal": request.goal,
            "auth_profile_id": request.auth_profile_id,
            "require_review": request.require_review,
        },
    )

    crawl_payload = {
        "session_id": session_id,
        "url": url_str,
        "max_pages": max_pages,
        "headless": request.headless if request.headless is not None else True,
        "user_id": x_user_id,
        "user_tier": x_user_tier,
        "session_state": request.session_state,
        "auth_profile_id": request.auth_profile_id,
        "goal": request.goal,
        "parallel": request.parallel or False,
        "max_agents": request.max_agents or 1,
        "require_review": request.require_review,
        "is_overage": is_overage_run,
    }

    # Dispatch to Celery worker (decoupled from web process) or fallback to local background task
    dispatched_to_queue = False
    try:
        from app.tasks.crawl_tasks import run_crawl_task
        run_crawl_task.delay(session_id=session_id, payload=crawl_payload)
        dispatched_to_queue = True
        logger.info(f"Crawl [{session_id}] dispatched to Celery worker queue.")
    except Exception as celery_err:
        logger.warning(
            f"Celery dispatch failed for [{session_id}] ({celery_err}). "
            "Using BackgroundTasks fallback — crawl tied to web process lifecycle."
        )

    if not dispatched_to_queue:
        background_tasks.add_task(run_background_crawl, **crawl_payload)

    return CrawlResponse(
        session_id=session_id,
        status="running",
        target_url=url_str,
    )


def _clean_header(val: Any, default: str = "") -> str:
    if hasattr(val, "default"):
        return str(val.default or default)
    return str(val if val is not None else default)


@router.get("/{session_id}")
@router.get("/{session_id}/status")
async def get_crawl_status(
    session_id: str,
    x_user_id: str = Header("default-user", alias="X-User-Id"),
    x_user_tier: str = Header("FREE", alias="X-User-Tier"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve current status and metadata of a crawl session with tenant isolation."""
    user_id = _clean_header(x_user_id, "default-user")
    tier = _clean_header(x_user_tier, "FREE").upper()
    try:
        repo = CrawlRepository(db)
        db_session = await repo.get_by_id(session_id)
        if db_session:
            # Enforce row-level tenant boundary
            if db_session.user_id != user_id and tier != "ADMIN":
                raise HTTPException(status_code=404, detail="Crawl session not found.")
            return db_session.to_dict()
    except HTTPException:
        raise
    except Exception:
        pass

    if session_id not in CRAWL_SESSIONS:
        raise HTTPException(status_code=404, detail="Crawl session not found.")
    
    session = CRAWL_SESSIONS[session_id]
    if session.get("user_id") and session["user_id"] != user_id and tier != "ADMIN":
        raise HTTPException(status_code=404, detail="Crawl session not found.")

    return session


@router.delete("/{session_id}")
async def delete_crawl_session(
    session_id: str,
    http_request: Request = None,
    x_user_id: str = Header("default-user", alias="X-User-Id"),
    x_user_tier: str = Header("FREE", alias="X-User-Tier"),
    db: AsyncSession = Depends(get_db),
):
    """Delete a crawl session with tenant verification and audit logging."""
    user_id = _clean_header(x_user_id, "default-user")
    tier = _clean_header(x_user_tier, "FREE").upper()
    found = False

    # Check DB
    try:
        repo = CrawlRepository(db)
        db_session = await repo.get_by_id(session_id)
        if db_session:
            if db_session.user_id != user_id and tier != "ADMIN":
                raise HTTPException(status_code=404, detail="Crawl session not found.")
            found = True
            await db.delete(db_session)
            await db.commit()
    except HTTPException:
        raise
    except Exception:
        pass

    # Check Memory Store
    if session_id in CRAWL_SESSIONS:
        session = CRAWL_SESSIONS[session_id]
        if session.get("user_id") and session["user_id"] != user_id and tier != "ADMIN":
            raise HTTPException(status_code=404, detail="Crawl session not found.")
        found = True
        del CRAWL_SESSIONS[session_id]

    if not found:
        raise HTTPException(status_code=404, detail="Crawl session not found.")

    # Record audit log
    from app.core.audit import AuditLogger
    await AuditLogger.log_event(
        db=db,
        user_id=user_id,
        action="crawl.delete",
        target_id=session_id,
        request=http_request,
    )

    return {"message": f"Session {session_id} deleted successfully."}


@router.get("/{session_id}/generate-tests")
async def generate_playwright_tests(
    session_id: str,
    format: str = Query("python", enum=["python", "typescript"]),
    as_zip: bool = Query(False),
    http_request: Request = None,
    x_user_id: str = Header("default-user", alias="X-User-Id"),
    x_user_tier: str = Header("FREE", alias="X-User-Tier"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate runnable Playwright regression test script or full CI/CD test suite zip
    from recorded crawl action traces and network observations with tenant verification.
    """
    from app.generators.playwright_test_gen import PlaywrightTestGenerator
    from app.core.audit import AuditLogger
    from fastapi.responses import Response

    user_id = _clean_header(x_user_id, "default-user")
    tier = _clean_header(x_user_tier, "FREE").upper()
    target_url = "https://example.com"
    action_traces = []
    found = False

    # 1. Try DB
    try:
        repo = CrawlRepository(db)
        db_session = await repo.get_by_id(session_id)
        if db_session:
            if db_session.user_id != user_id and tier != "ADMIN":
                raise HTTPException(status_code=404, detail="Crawl session not found.")
            found = True
            target_url = db_session.target_url
            action_traces = db_session.action_traces or []
    except HTTPException:
        raise
    except Exception:
        pass

    # 2. Try in-memory store if DB missed
    if not found and session_id in CRAWL_SESSIONS:
        session = CRAWL_SESSIONS[session_id]
        if session.get("user_id") and session["user_id"] != user_id and tier != "ADMIN":
            raise HTTPException(status_code=404, detail="Crawl session not found.")
        found = True
        target_url = session.get("target_url", target_url)
        action_traces = session.get("action_traces", [])

    if not found:
        raise HTTPException(status_code=404, detail="Crawl session not found.")

    # Record audit log for export download
    await AuditLogger.log_event(
        db=db,
        user_id=user_id,
        action="export.download",
        target_id=session_id,
        request=http_request,
        metadata={"format": f"playwright_{format}", "as_zip": as_zip},
    )


    if as_zip:
        zip_bytes = PlaywrightTestGenerator.generate_test_suite_zip(
            target_url=target_url,
            action_traces=action_traces,
            session_id=session_id,
            format=format,
        )
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=insightapi_test_suite_{session_id}.zip"
            },
        )

    if format.lower() in ("ts", "typescript"):
        code = PlaywrightTestGenerator.generate_typescript_test(
            target_url=target_url,
            action_traces=action_traces,
            session_id=session_id,
        )
        return Response(
            content=code,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=test_regression_{session_id}.spec.ts"
            },
        )
    else:
        code = PlaywrightTestGenerator.generate_python_test(
            target_url=target_url,
            action_traces=action_traces,
            session_id=session_id,
        )
        return Response(
            content=code,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=test_regression_{session_id}.py"
            },
        )


