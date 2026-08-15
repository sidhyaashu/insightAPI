"""Repository for LlmUsage DB operations."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.llm_usage import LlmUsage


class LlmUsageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(
        self,
        crawl_id: str,
        user_id: str,
        model_name: str,
        tier: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        cached: bool = False,
        node_name: Optional[str] = None,
    ) -> LlmUsage:
        """Insert a single LLM call record."""
        row = LlmUsage(
            crawl_id=crawl_id,
            user_id=user_id,
            model_name=model_name,
            tier=tier,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost_usd,
            cached=cached,
            node_name=node_name,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def get_by_crawl(self, crawl_id: str) -> list[LlmUsage]:
        result = await self.db.execute(
            select(LlmUsage)
            .where(LlmUsage.crawl_id == crawl_id)
            .order_by(LlmUsage.created_at)
        )
        return list(result.scalars().all())

    async def get_cost_summary(
        self,
        user_id: str,
        crawl_id: Optional[str] = None,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> dict:
        """
        Aggregate cost and token metrics for a user (optionally filtered by
        crawl or time window).  Returns a dict ready to serialise as JSON.
        """
        q = select(
            func.count(LlmUsage.id).label("total_calls"),
            func.sum(LlmUsage.prompt_tokens).label("prompt_tokens"),
            func.sum(LlmUsage.completion_tokens).label("completion_tokens"),
            func.sum(LlmUsage.total_tokens).label("total_tokens"),
            func.sum(LlmUsage.cost_usd).label("total_cost_usd"),
            func.sum(
                func.cast(LlmUsage.cached, type_=func.count(LlmUsage.id).__class__)
            ).label("cache_hits"),
        ).where(LlmUsage.user_id == user_id)

        if crawl_id:
            q = q.where(LlmUsage.crawl_id == crawl_id)
        if from_dt:
            q = q.where(LlmUsage.created_at >= from_dt)
        if to_dt:
            q = q.where(LlmUsage.created_at <= to_dt)

        result = await self.db.execute(q)
        row = result.one_or_none()
        if not row or row.total_calls == 0:
            return {
                "total_calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "cache_hits": 0,
                "cache_hit_rate_pct": 0.0,
            }

        total_calls = int(row.total_calls or 0)
        cache_hits = int(row.cache_hits or 0)
        return {
            "total_calls": total_calls,
            "prompt_tokens": int(row.prompt_tokens or 0),
            "completion_tokens": int(row.completion_tokens or 0),
            "total_tokens": int(row.total_tokens or 0),
            "total_cost_usd": round(float(row.total_cost_usd or 0.0), 6),
            "cache_hits": cache_hits,
            "cache_hit_rate_pct": round(cache_hits / total_calls * 100, 1) if total_calls else 0.0,
        }

    async def get_breakdown_by_model(
        self,
        user_id: str,
        crawl_id: Optional[str] = None,
    ) -> list[dict]:
        """Per-model cost and token breakdown."""
        q = (
            select(
                LlmUsage.model_name,
                LlmUsage.tier,
                func.count(LlmUsage.id).label("calls"),
                func.sum(LlmUsage.total_tokens).label("tokens"),
                func.sum(LlmUsage.cost_usd).label("cost_usd"),
            )
            .where(LlmUsage.user_id == user_id)
            .group_by(LlmUsage.model_name, LlmUsage.tier)
            .order_by(func.sum(LlmUsage.cost_usd).desc())
        )
        if crawl_id:
            q = q.where(LlmUsage.crawl_id == crawl_id)

        result = await self.db.execute(q)
        return [
            {
                "model_name": row.model_name,
                "tier": row.tier,
                "calls": int(row.calls),
                "total_tokens": int(row.tokens or 0),
                "cost_usd": round(float(row.cost_usd or 0.0), 6),
            }
            for row in result.all()
        ]
