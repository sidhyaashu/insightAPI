"""Repository for CrawlSnapshot DB operations in agent-service.

Provides helpers to:
- Bulk-persist per-endpoint snapshots after a crawl completes.
- Load all snapshots for a crawl (for drift comparison).
- Locate the most recent prior crawl for a project (auto-detect base).
"""
from __future__ import annotations

import re
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.crawl_snapshot import CrawlSnapshot

logger = logging.getLogger(__name__)


def _build_endpoint_key(ep: dict[str, Any]) -> str:
    """Derive a stable composite key from a captured endpoint dict.

    Format: ``{METHOD}:{normalized_path}:{status_code}``
    Mirrors the keying used by the OpenAPI exporter so keys are consistent.
    """
    full_route: str = ep.get("template_route", "/")
    parsed = urlparse(full_route)
    raw_path = parsed.path if parsed.path else "/"
    path = re.sub(r"\s*\([^)]*\)", "", raw_path).strip()
    method = ep.get("method", "GET").upper()
    status = str(ep.get("status", 200))
    # Append GraphQL operation name when present so ops are distinct
    graphql_op = ep.get("graphql_operation_name")
    if graphql_op:
        clean_op = re.sub(r"[^a-zA-Z0-9_]", "_", graphql_op)
        path = f"{path.rstrip('/')}/{clean_op}"
    return f"{method}:{path}:{status}"


class SnapshotRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Write ────────────────────────────────────────────────────────────────

    async def bulk_upsert_snapshots(
        self,
        crawl_id: str,
        project_id: str,
        captured_endpoints: list[dict[str, Any]],
    ) -> int:
        """Persist one snapshot row per endpoint for *crawl_id*.

        Uses PostgreSQL ``INSERT … ON CONFLICT DO NOTHING`` so repeated calls
        (e.g. retries) are idempotent.  Returns the number of rows inserted.
        """
        if not captured_endpoints:
            return 0

        rows: list[dict] = []
        seen_keys: set[str] = set()
        for ep in captured_endpoints:
            key = _build_endpoint_key(ep)
            if key in seen_keys:
                continue  # de-duplicate within the same crawl
            seen_keys.add(key)
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "crawl_id": crawl_id,
                    "project_id": project_id,
                    "endpoint_key": key,
                    "schema_json": ep.get("schema") or {},
                    "status_code": int(ep.get("status", 200)),
                    "created_at": datetime.now(timezone.utc),
                }
            )

        if not rows:
            return 0

        stmt = pg_insert(CrawlSnapshot).values(rows).on_conflict_do_nothing(
            index_elements=["crawl_id", "endpoint_key"]
        )
        await self.db.execute(stmt)
        await self.db.commit()
        return len(rows)

    # ── Read ─────────────────────────────────────────────────────────────────

    async def get_snapshots_for_crawl(self, crawl_id: str) -> list[CrawlSnapshot]:
        """Return all snapshot rows for a given crawl."""
        result = await self.db.execute(
            select(CrawlSnapshot).where(CrawlSnapshot.crawl_id == crawl_id)
        )
        return list(result.scalars().all())

    async def get_latest_crawl_id_for_project(
        self,
        project_id: str,
        exclude_crawl_id: str | None = None,
    ) -> str | None:
        """Return the crawl_id of the most recent completed snapshot set for *project_id*.

        Used by the drift endpoint to auto-detect the base crawl when ``?base=``
        is not supplied by the caller.
        """
        q = (
            select(CrawlSnapshot.crawl_id, CrawlSnapshot.created_at)
            .where(CrawlSnapshot.project_id == project_id)
        )
        if exclude_crawl_id:
            q = q.where(CrawlSnapshot.crawl_id != exclude_crawl_id)
        q = q.order_by(CrawlSnapshot.created_at.desc()).limit(1)
        result = await self.db.execute(q)
        row = result.first()
        return row[0] if row else None

    # ── Delete ───────────────────────────────────────────────────────────────

    async def delete_snapshots_for_crawl(self, crawl_id: str) -> None:
        """Remove all snapshot rows for a crawl (e.g. when crawl is deleted)."""
        await self.db.execute(
            delete(CrawlSnapshot).where(CrawlSnapshot.crawl_id == crawl_id)
        )
        await self.db.commit()
