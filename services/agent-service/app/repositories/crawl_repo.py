"""Repository for CrawlSession DB operations in agent-service."""
from __future__ import annotations

from datetime import datetime, timezone, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.models.crawl_session import CrawlSession
from app.core.redis import get_redis_client


class CrawlRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: str, user_tier: str, target_url: str, max_pages: int, goal: str | None) -> CrawlSession:
        session = CrawlSession(
            user_id=user_id,
            user_tier=user_tier,
            target_url=target_url,
            max_pages=max_pages,
            goal=goal,
            status="running",
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_by_id(self, session_id: str) -> CrawlSession | None:
        result = await self.db.execute(select(CrawlSession).where(CrawlSession.id == session_id))
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: str, limit: int = 20, offset: int = 0) -> list[CrawlSession]:
        result = await self.db.execute(
            select(CrawlSession)
            .where(CrawlSession.user_id == user_id)
            .order_by(CrawlSession.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        session_id: str,
        status: str,
        captured_count: int = 0,
        openapi_spec: dict | None = None,
        postman_collection: dict | None = None,
        markdown_docs: str | None = None,
        action_traces: list | None = None,
        error_message: str | None = None,
    ) -> None:
        values: dict = {
            "status": status,
            "captured_count": captured_count,
            "updated_at": datetime.now(timezone.utc),
        }
        if openapi_spec is not None:
            values["openapi_spec"] = openapi_spec
        if postman_collection is not None:
            values["postman_collection"] = postman_collection
        if markdown_docs is not None:
            values["markdown_docs"] = markdown_docs
        if action_traces is not None:
            values["action_traces"] = action_traces
        if error_message is not None:
            values["error_message"] = error_message

        await self.db.execute(
            update(CrawlSession).where(CrawlSession.id == session_id).values(**values)
        )
        await self.db.commit()

    async def check_daily_quota(self, user_id: str, free_limit: int) -> tuple[int, bool]:
        """
        Check Redis counter for today's crawl count.
        Returns (current_count, quota_exceeded).
        """
        today = date.today().isoformat()
        key = f"quota:crawl:{user_id}:{today}"
        redis = await get_redis_client()
        count = await redis.get(key)
        current = int(count) if count else 0
        return current, current >= free_limit

    async def increment_daily_quota(self, user_id: str) -> None:
        """Increment and set 25h TTL on the daily crawl quota counter."""
        today = date.today().isoformat()
        key = f"quota:crawl:{user_id}:{today}"
        redis = await get_redis_client()
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 90000)   # 25 hours TTL
        await pipe.execute()

    # ── Review / Approval Gate ────────────────────────────────────────────────

    async def set_pending_review(
        self, session_id: str, captured_count: int, action_traces: list | None = None
    ) -> None:
        """Transition crawl to pending_review after analysis completes.

        Called when ``require_review=True`` on the crawl request.
        Exporters do NOT run at this point; they run on approval.
        """
        values: dict = {
            "status": "pending_review",
            "captured_count": captured_count,
            "updated_at": datetime.now(timezone.utc),
        }
        if action_traces is not None:
            values["action_traces"] = action_traces

        await self.db.execute(
            update(CrawlSession).where(CrawlSession.id == session_id).values(**values)
        )
        await self.db.commit()

    async def save_reviewed_endpoints(
        self, session_id: str, reviewed_endpoints: dict
    ) -> None:
        """Persist the full reviewed_endpoints dict (keyed by endpoint_key).

        Structure: ``{ endpoint_key: { "reviewed_schema": dict, "is_excluded": bool } }``

        Called by ``PATCH /crawls/{id}/endpoints/{key}`` to merge-patch a single
        endpoint's overrides into the blob.
        """
        await self.db.execute(
            update(CrawlSession)
            .where(CrawlSession.id == session_id)
            .values(
                reviewed_endpoints=reviewed_endpoints,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await self.db.commit()

    async def approve_crawl(
        self,
        session_id: str,
        openapi_spec: dict,
        postman_collection: dict,
        markdown_docs: str,
        captured_count: int,
    ) -> None:
        """Finalize review: persist exports and transition to completed.

        Called by ``POST /crawls/{id}/approve``.
        """
        await self.db.execute(
            update(CrawlSession)
            .where(CrawlSession.id == session_id)
            .values(
                status="completed",
                captured_count=captured_count,
                openapi_spec=openapi_spec,
                postman_collection=postman_collection,
                markdown_docs=markdown_docs,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await self.db.commit()

