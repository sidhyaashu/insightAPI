"""
coordinator.py — Parallel Multi-Agent Coordinator for InsightAPI AI

Design
------
Orchestrates concurrent browser exploration sessions when parallel crawling is enabled.

Workflow
--------
1. Inspects the target page navigation elements using ModelTier.FAST (gpt-4o-mini).
2. Decomposes the application into N independent section goals (up to max_agents).
3. Spawns concurrent AgentEngine instances using asyncio.gather().
4. Deduplicates and merges all captured endpoints and LLM metrics into a single unified CrawlResult.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger("agent.coordinator")


class CrawlCoordinator:
    """
    Coordinates multi-agent parallel crawling across independent app sections.
    """

    @staticmethod
    async def identify_section_goals(
        url: str,
        initial_elements: List[Dict[str, Any]],
        max_agents: int = 3,
        overall_goal: Optional[str] = None,
    ) -> List[str]:
        """
        Uses an LLM to decompose a target site's navigation controls into
        N focused, non-overlapping section goals for parallel sub-agents.
        """
        if max_agents <= 1 or not initial_elements:
            return [overall_goal or "Explore all API endpoints"]

        # Build element list summary
        nav_elements = []
        for el in initial_elements:
            text = (el.get("text") or el.get("ariaLabel") or "").strip()
            tag = el.get("tag", "")
            role = el.get("role", "")
            if text and (role in ["button", "link", "tab", "menuitem"] or tag in ["a", "button"]):
                nav_elements.append(f"- {text} ({role or tag})")

        prompt = (
            f"Target URL: {url}\n"
            f"Overall Goal: {overall_goal or 'Discover all API endpoints'}\n"
            f"Navigation Controls visible on main page:\n"
            + "\n".join(nav_elements[:30])
            + "\n\n"
            f"Decompose this web application into up to {max_agents} independent, non-overlapping "
            "sub-goals for parallel crawler agents to explore simultaneously.\n"
            "Respond ONLY with a JSON array of strings (the sub-goal descriptions).\n"
            'Example: ["Focus on User Account & Profile Settings", "Focus on Product Catalog & Search", "Focus on Checkout & Cart"]'
        )

        try:
            from app.agents.nodes.llm_client import get_llm, ModelTier
            llm = get_llm(ModelTier.FAST)
            response = await llm.ainvoke(prompt)
            response_text = response.content if hasattr(response, "content") else str(response)

            clean = response_text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            sub_goals = json.loads(clean)
            if isinstance(sub_goals, list) and sub_goals:
                logger.info(f"🔀 Coordinator split crawl into {len(sub_goals)} parallel section goals: {sub_goals}")
                return [str(g) for g in sub_goals[:max_agents]]
        except Exception as e:
            logger.warning(f"Coordinator goal decomposition failed ({type(e).__name__}: {e}). Using single worker.")

        return [overall_goal or "Explore all API endpoints"]

    @classmethod
    async def run_parallel_crawl(
        cls,
        url: str,
        max_pages: int = 15,
        max_agents: int = 2,
        rate_limit_ms: int = 500,
        session_state: Optional[Dict[str, Any]] = None,
        goal: Optional[str] = None,
        headless: bool = True,
    ) -> Any:
        """
        Executes parallel crawl workers across identified section goals and merges results.
        """
        from app.sdk import AgentEngine, CrawlResult

        # Clamp max_agents to PARALLEL_AGENTS_MAX config safety limit unless overridden
        effective_max_agents = max(1, min(max_agents, getattr(settings, "PARALLEL_AGENTS_MAX", 5) or 5))

        logger.info(
            f"🚀 Launching Parallel Crawl | Target: {url} | "
            f"Workers: {effective_max_agents} | Max Pages Total: {max_pages}"
        )

        # 1. Single lightweight initial scan to get DOM elements for goal decomposition
        initial_engine = AgentEngine(headless=headless)
        initial_result = await initial_engine.crawl(
            url, max_pages=1, rate_limit_ms=rate_limit_ms, session_state=session_state, goal=goal
        )

        initial_elements = initial_result.captured_endpoints  # reference endpoints

        # 2. Decompose into section sub-goals
        sub_goals = await cls.identify_section_goals(
            url=url,
            initial_elements=initial_result.captured_endpoints,
            max_agents=effective_max_agents,
            overall_goal=goal,
        )

        pages_per_worker = max(2, max_pages // len(sub_goals))

        # 3. Spawn parallel worker engines
        async def _worker(worker_id: int, sub_goal: str):
            logger.info(f"Worker #{worker_id} starting for sub-goal: '{sub_goal}' (budget: {pages_per_worker} pages)")
            worker_engine = AgentEngine(headless=headless)
            return await worker_engine.crawl(
                url,
                max_pages=pages_per_worker,
                rate_limit_ms=rate_limit_ms,
                session_state=session_state,
                goal=f"SUB-AGENT GOAL: {sub_goal}. Overall goal: {goal or 'Discover all APIs'}",
            )

        worker_tasks = [_worker(i + 1, sg) for i, sg in enumerate(sub_goals)]
        worker_results = await asyncio.gather(*worker_tasks, return_exceptions=True)

        # 4. Merge all captured endpoints and LLM metrics
        all_endpoints: List[Dict[str, Any]] = []
        seen_keys = set()
        total_explored = 0
        total_tokens = 0
        total_llm_calls = 0
        total_cost = 0.0

        # Include initial scan endpoints
        for ep in initial_result.captured_endpoints:
            key = (ep.get("template_route"), ep.get("method"), ep.get("status"))
            if key not in seen_keys:
                seen_keys.add(key)
                all_endpoints.append(ep)

        for res in worker_results:
            if isinstance(res, Exception):
                logger.error(f"Parallel worker failed: {res}")
                continue
            if not isinstance(res, CrawlResult):
                continue

            total_explored += res.explored_count

            # Roll up metrics
            m = res.llm_metrics or {}
            total_tokens += m.get("tokens_used", 0)
            total_llm_calls += m.get("llm_calls_made", 0)
            total_cost += m.get("estimated_cost_usd", 0.0)

            for ep in res.captured_endpoints:
                key = (ep.get("template_route"), ep.get("method"), ep.get("status"))
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_endpoints.append(ep)

        merged_metrics = {
            "tokens_used": total_tokens,
            "llm_calls_made": total_llm_calls,
            "estimated_cost_usd": round(total_cost, 4),
            "parallel_workers": len(sub_goals),
        }

        logger.info(
            f"✅ Parallel Crawl Complete | Merged Endpoints: {len(all_endpoints)} | "
            f"Total Explored Pages: {total_explored} | Total Cost: ${total_cost:.4f}"
        )

        return CrawlResult(
            target_url=url,
            captured_endpoints=all_endpoints,
            explored_count=total_explored or 1,
            elapsed_time_seconds=initial_result.elapsed_time_seconds,
            llm_metrics=merged_metrics,
        )
