"""
reflection.py — LLM-Powered Self-Critique Node for InsightAPI AI

Design
------
Evaluates progress every ``LLM_REFLECTION_INTERVAL`` (default 5 explored pages).
Uses ModelTier.SMART (gpt-4o / gpt-5.4) for holistic reasoning:
- Assesses whether current exploration direction is yielding new APIs
- Identifies coverage blind spots based on discovered endpoint categories vs target URL
- Updates state["reflection_notes"] to guide subsequent PlannerNode decisions
"""
from __future__ import annotations

import json
import logging
from typing import Dict, Any, Optional

from app.agents.state import CrawlState
from app.core.config import settings

logger = logging.getLogger("agent.reflection")


class ReflectionNode:
    """
    Self-critique node that periodically steps back to evaluate crawl effectiveness.
    """

    @classmethod
    def should_reflect(cls, state: CrawlState) -> bool:
        """
        Returns True if reflection should trigger after the current executor step.
        Controlled by settings.LLM_REFLECTION_ENABLED and LLM_REFLECTION_INTERVAL.
        """
        if not settings.LLM_REFLECTION_ENABLED:
            return False
        interval = settings.LLM_REFLECTION_INTERVAL
        if interval <= 0:
            return False
        explored = state.get("explored_count", 0)
        return explored > 0 and (explored % interval == 0)

    @classmethod
    async def process(cls, state: CrawlState) -> CrawlState:
        """
        LangGraph node execution: performs holistic reasoning on current progress.
        """
        cost_manager = state.get("cost_manager")
        if cost_manager and cost_manager.is_budget_exhausted():
            logger.info("ReflectionNode: Token budget exhausted, skipping self-critique.")
            return state

        explored = state.get("explored_count", 0)
        max_pages = state.get("max_pages", 10)
        captured = state.get("captured_endpoints") or []
        categories = state.get("endpoint_categories") or []
        goal = state.get("goal") or "Discover all API endpoints used by this web application"
        current_url = state.get("current_url", "")
        target_url = state.get("target_url", "")

        prompt = (
            f"You are an AI crawler supervisor conducting a mid-crawl progress review.\n\n"
            f"Crawl Progress Report:\n"
            f"  - Target Site: {target_url}\n"
            f"  - Current URL: {current_url}\n"
            f"  - Pages explored: {explored}/{max_pages}\n"
            f"  - Endpoints captured so far: {len(captured)}\n"
            f"  - Discovered API categories: {categories or ['none yet']}\n"
            f"  - Goal: {goal}\n\n"
            "Evaluate:\n"
            "1. Is the agent making meaningful progress toward discovering new API endpoints?\n"
            "2. What functional areas or UI sections of the application appear to be BLIND SPOTS or UNEXPLORED?\n"
            "3. What specific type of interaction or section should the planner prioritize next?\n\n"
            "Respond ONLY with a valid JSON object:\n"
            "{\n"
            '  "making_progress": true,\n'
            '  "blind_spots": ["e.g. user profile management", "search filters"],\n'
            '  "next_priority": "short recommendation for next actions"\n'
            "}"
        )

        try:
            from app.agents.nodes.llm_client import get_llm, ModelTier
            # Reflection is a complex reasoning task — use SMART tier (gpt-4o / gpt-5.4)
            llm = get_llm(ModelTier.SMART)
            response = await llm.ainvoke(prompt)
            response_text = response.content if hasattr(response, "content") else str(response)

            tokens_est = (len(prompt) + len(response_text)) // 4
            if cost_manager:
                model_name = settings.AZURE_OPENAI_DEPLOYMENT_SMART if settings.AZURE_OPENAI_ENDPOINT else settings.OPENAI_MODEL_SMART
                cost_manager.record_usage(tokens_est, model_name)

            clean = response_text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            reflection_data = json.loads(clean)

            state["reflection_notes"] = json.dumps(reflection_data)
            logger.info(
                f"🧠 Reflection Complete (Page {explored}/{max_pages}) | "
                f"Progress: {reflection_data.get('making_progress')} | "
                f"Priority: '{reflection_data.get('next_priority', '')[:60]}'"
            )

        except Exception as e:
            logger.warning(f"ReflectionNode failed ({type(e).__name__}: {e}). Continuing without critique.")

        return state
