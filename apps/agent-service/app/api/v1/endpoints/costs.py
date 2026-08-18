"""
costs.py — LLM Cost & Token Usage API endpoints.

GET /api/v1/costs              — per-user aggregate summary (optional date window)
GET /api/v1/costs/by-crawl/{id} — per-crawl call-level detail + aggregate
GET /api/v1/costs/breakdown    — cost breakdown by model for the user
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.llm_usage_repo import LlmUsageRepository
from app.repositories.crawl_repo import CrawlRepository

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def get_cost_summary(
    x_user_id: str = Header(..., alias="x-user-id"),
    x_user_tier: Optional[str] = Header(default="FREE", alias="x-user-tier"),
    crawl_id: Optional[str] = Query(default=None, description="Filter by specific crawl session ID"),
    from_date: Optional[str] = Query(default=None, description="ISO-8601 start date filter (e.g. 2026-01-01)"),
    to_date: Optional[str] = Query(default=None, description="ISO-8601 end date filter"),
    db: AsyncSession = Depends(get_db),
):
    """
    Return aggregated LLM token and cost metrics for the authenticated user.

    Scoped by ``x-user-id`` header — no cross-tenant access possible.
    Optionally filter by crawl_id or ISO date range.
    """
    from_dt: Optional[datetime] = None
    to_dt: Optional[datetime] = None

    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid from_date format: '{from_date}'. Use ISO-8601.")
    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid to_date format: '{to_date}'. Use ISO-8601.")

    repo = LlmUsageRepository(db)
    summary = await repo.get_cost_summary(
        user_id=x_user_id,
        crawl_id=crawl_id,
        from_dt=from_dt,
        to_dt=to_dt,
    )
    return {
        "user_id": x_user_id,
        "filters": {
            "crawl_id": crawl_id,
            "from_date": from_date,
            "to_date": to_date,
        },
        **summary,
    }


@router.get("/by-crawl/{crawl_id}")
async def get_crawl_cost_detail(
    crawl_id: str,
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """
    Return per-call LLM usage records for a specific crawl, plus an aggregate
    summary. Tenant-scoped: returns 404 if crawl belongs to another user.
    """
    # Tenant isolation check
    crawl_repo = CrawlRepository(db)
    session = await crawl_repo.get_by_id(crawl_id)
    if not session or session.user_id != x_user_id:
        raise HTTPException(status_code=404, detail="Crawl session not found.")

    usage_repo = LlmUsageRepository(db)
    calls = await usage_repo.get_by_crawl(crawl_id)
    summary = await usage_repo.get_cost_summary(user_id=x_user_id, crawl_id=crawl_id)

    return {
        "crawl_id": crawl_id,
        "target_url": session.target_url,
        "summary": summary,
        "calls": [c.to_dict() for c in calls],
    }


@router.get("/breakdown")
async def get_cost_breakdown_by_model(
    x_user_id: str = Header(..., alias="x-user-id"),
    crawl_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Return cost and token totals grouped by model name / tier.
    Useful for understanding which model tiers drive the most spend.
    """
    repo = LlmUsageRepository(db)
    breakdown = await repo.get_breakdown_by_model(user_id=x_user_id, crawl_id=crawl_id)
    return {
        "user_id": x_user_id,
        "crawl_id": crawl_id,
        "breakdown_by_model": breakdown,
    }
