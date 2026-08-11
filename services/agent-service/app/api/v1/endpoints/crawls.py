import asyncio
import uuid
import logging
import json
import ipaddress
from urllib.parse import urlparse
from typing import Optional, Dict, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.sdk import AgentEngine
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.repositories.crawl_repo import CrawlRepository

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


async def run_background_crawl(
    session_id: str,
    url: str,
    max_pages: int,
    headless: bool,
    user_id: str,
    user_tier: str,
    session_state: Optional[Dict[str, Any]] = None,
    goal: Optional[str] = None,
    parallel: bool = False,
    max_agents: int = 1,
):
    """Background task running AgentEngine exploration and publishing WS events."""
    await publish_ws_event(session_id, {"type": "log", "message": f"Starting crawl engine for {url}..."})

    try:
        engine = AgentEngine(headless=headless)
        result = await engine.crawl(
            url,
            max_pages=max_pages,
            session_state=session_state,
            goal=goal,
            parallel=parallel,
            max_agents=max_agents,
        )

        captured_count = len(result.captured_endpoints)
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
                )
        except Exception as db_err:
            logger.warning(f"DB update failed for crawl {session_id}: {db_err}")

        await publish_ws_event(session_id, {"type": "complete", "captured_count": captured_count})

    except Exception as e:
        logger.error(f"Crawl session {session_id} failed: {e}")
        if session_id in CRAWL_SESSIONS:
            CRAWL_SESSIONS[session_id].update({"status": "failed", "error": str(e)})

        try:
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                repo = CrawlRepository(db)
                await repo.update_status(session_id=session_id, status="failed", error_message=str(e))
        except Exception:
            pass

        await publish_ws_event(session_id, {"type": "error", "message": str(e)})


@router.get("")
async def list_crawl_sessions(
    x_user_id: Optional[str] = Header(default=None, alias="x-user-id"),
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List crawl sessions for the authenticated user."""
    if x_user_id:
        try:
            repo = CrawlRepository(db)
            db_sessions = await repo.get_by_user(user_id=x_user_id, limit=limit)
            return [s.to_dict() for s in db_sessions]
        except Exception as e:
            logger.warning(f"DB query failed, falling back to memory store: {e}")

    # Fallback to memory store
    user_sessions = [
        s for s in CRAWL_SESSIONS.values()
        if not x_user_id or s.get("user_id") == x_user_id
    ]
    return user_sessions[:limit]


from app.core.constants import TIER_QUOTAS, TIER_MAX_PAGES, TIER_MAX_AGENTS

@router.post("/start", response_model=CrawlResponse)
async def start_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    x_user_id: Optional[str] = Header(default="anonymous", alias="x-user-id"),
    x_user_tier: Optional[str] = Header(default="FREE", alias="x-user-tier"),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an autonomous AI crawl session with tier-quota enforcement and header injection."""
    try:
        url_str = request.get_url().strip()
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

    if not url_str.startswith("http://") and not url_str.startswith("https://"):
        url_str = f"https://{url_str}"

    validate_target_url_ssrf(url_str)

    tier = (x_user_tier or "FREE").upper()
    quota_limit = TIER_QUOTAS.get(tier, 1)

    # Daily Quota Check (ADMIN and ENTERPRISE have 999999 quota)
    repo = CrawlRepository(db)
    if tier != "ADMIN" and tier != "ENTERPRISE":
        current_count, is_exceeded = await repo.check_daily_quota(x_user_id, quota_limit)
        if is_exceeded:
            raise HTTPException(
                status_code=429,
                detail=f"Daily crawl limit reached ({quota_limit}/day on {tier} tier). Upgrade your plan for more crawls."
            )

    # Max pages enforcement based on tier
    allowed_max_pages = TIER_MAX_PAGES.get(tier, 10)
    requested_pages = request.max_pages or 10
    max_pages = min(requested_pages, allowed_max_pages) if tier != "ADMIN" else requested_pages

    # Max agents enforcement based on tier
    allowed_max_agents = TIER_MAX_AGENTS.get(tier, 1)
    requested_agents = request.max_agents or 1
    max_agents = min(requested_agents, allowed_max_agents) if tier != "ADMIN" else requested_agents

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

    background_tasks.add_task(
        run_background_crawl,
        session_id=session_id,
        url=url_str,
        max_pages=max_pages,
        headless=request.headless if request.headless is not None else True,
        user_id=x_user_id,
        user_tier=x_user_tier,
        session_state=request.session_state,
        goal=request.goal,
        parallel=request.parallel or False,
        max_agents=request.max_agents or 1,
    )

    return CrawlResponse(
        session_id=session_id,
        status="running",
        target_url=url_str,
    )


@router.get("/{session_id}")
@router.get("/{session_id}/status")
async def get_crawl_status(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve current status and metadata of a crawl session."""
    try:
        repo = CrawlRepository(db)
        db_session = await repo.get_by_id(session_id)
        if db_session:
            return db_session.to_dict()
    except Exception:
        pass

    if session_id not in CRAWL_SESSIONS:
        raise HTTPException(status_code=404, detail="Crawl session not found.")
    return CRAWL_SESSIONS[session_id]


@router.delete("/{session_id}")
async def delete_crawl_session(session_id: str):
    """Delete a crawl session from memory."""
    if session_id in CRAWL_SESSIONS:
        del CRAWL_SESSIONS[session_id]
    return {"message": f"Session {session_id} deleted successfully."}
