"""
runtime/persistence.py — Stateful Session Persistence & Resumability Layer.

Architecture (AGENTS.md §25, §26):
  - Multi-tier memory and persistence:
    1. Working Memory (Hot AgentState)
    2. Session Memory (Events, Observations, Hypotheses)
    3. Application Memory (Application World Model / Graph)
  - Durable PostgreSQL backing via SQLAlchemy AsyncSession.
  - Allows paused, interrupted, or multi-stage investigations to resume seamlessly after restart.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.runtime.models import (
    AgentState,
    Goal,
    Hypothesis,
    Observation,
)
from app.runtime.world_model import ApplicationGraph
from app.models.crawl_session import CrawlSession

logger = logging.getLogger("agent.runtime.persistence")


class AgentStateStore:
    """
    Persistence adapter for AgentState, ApplicationGraph, and Hypotheses.
    Supports in-memory caching and durable PostgreSQL database storage.
    """

    def __init__(self) -> None:
        self._state_cache: Dict[str, Dict[str, Any]] = {}
        self._graph_cache: Dict[str, Dict[str, Any]] = {}
        self._hypotheses_cache: Dict[str, List[Dict[str, Any]]] = {}

    async def save_state(self, state: AgentState, db: Optional[AsyncSession] = None) -> None:
        """Serialize and persist the hot AgentState to cache and DB."""
        state_dict = state.model_dump(mode="json")
        self._state_cache[state.session_id] = state_dict

        if db:
            try:
                # Upsert into crawl_sessions
                res = await db.execute(select(CrawlSession).where(CrawlSession.id == state.session_id))
                session_obj = res.scalar_one_or_none()
                if session_obj:
                    metrics_json = session_obj.llm_metrics_json or {}
                    metrics_json["agent_state"] = state_dict
                    session_obj.llm_metrics_json = metrics_json
                    target_url_val = state.current_url or (state.goal.target_url if state.goal else "https://api.example.com")
                    session_obj.target_url = target_url_val or session_obj.target_url
                    session_obj.goal = state.goal.description if state.goal else session_obj.goal
                else:
                    target_url_val = state.current_url or (state.goal.target_url if state.goal else "https://api.example.com")
                    new_session = CrawlSession(
                        id=state.session_id,
                        user_id="default-user",
                        target_url=target_url_val,
                        goal=state.goal.description if state.goal else None,
                        status="running",
                        llm_metrics_json={"agent_state": state_dict},
                    )
                    db.add(new_session)
                await db.commit()
                logger.debug(f"Persisted AgentState to DB for session {state.session_id}")
            except Exception as e:
                logger.warning(f"Failed to persist AgentState to DB (falling back to cache): {e}")

    async def load_state(self, session_id: str, db: Optional[AsyncSession] = None) -> Optional[AgentState]:
        """Load and deserialize AgentState by session_id from cache or DB."""
        raw = self._state_cache.get(session_id)
        if not raw and db:
            try:
                res = await db.execute(select(CrawlSession).where(CrawlSession.id == session_id))
                session_obj = res.scalar_one_or_none()
                if session_obj and session_obj.llm_metrics_json:
                    raw = session_obj.llm_metrics_json.get("agent_state")
                    if raw:
                        self._state_cache[session_id] = raw
            except Exception as e:
                logger.warning(f"Error loading AgentState from DB: {e}")

        if not raw:
            return None
        return AgentState.model_validate(raw)

    async def save_world_model(self, graph: ApplicationGraph, db: Optional[AsyncSession] = None) -> None:
        """Persist the Application Graph structure to cache and DB."""
        graph_dict = graph.to_dict()
        self._graph_cache[graph.session_id] = graph_dict

        if db:
            try:
                res = await db.execute(select(CrawlSession).where(CrawlSession.id == graph.session_id))
                session_obj = res.scalar_one_or_none()
                if session_obj:
                    metrics_json = session_obj.llm_metrics_json or {}
                    metrics_json["world_model"] = graph_dict
                    session_obj.llm_metrics_json = metrics_json
                    session_obj.captured_count = len(graph.nodes)
                    await db.commit()
                    logger.debug(f"Persisted ApplicationGraph to DB for session {graph.session_id}")
            except Exception as e:
                logger.warning(f"Failed to persist ApplicationGraph to DB: {e}")

    async def load_world_model(self, session_id: str, db: Optional[AsyncSession] = None) -> Optional[ApplicationGraph]:
        """Restore ApplicationGraph by session_id from cache or DB."""
        raw = self._graph_cache.get(session_id)
        if not raw and db:
            try:
                res = await db.execute(select(CrawlSession).where(CrawlSession.id == session_id))
                session_obj = res.scalar_one_or_none()
                if session_obj and session_obj.llm_metrics_json:
                    raw = session_obj.llm_metrics_json.get("world_model")
                    if raw:
                        self._graph_cache[session_id] = raw
            except Exception as e:
                logger.warning(f"Error loading ApplicationGraph from DB: {e}")

        if not raw:
            return None
        return ApplicationGraph.from_dict(raw)

    async def save_hypotheses(self, session_id: str, hypotheses: List[Hypothesis], db: Optional[AsyncSession] = None) -> None:
        """Persist generated hypotheses and evidence links to cache and DB."""
        hyp_list = [h.model_dump(mode="json") for h in hypotheses]
        self._hypotheses_cache[session_id] = hyp_list

        if db:
            try:
                res = await db.execute(select(CrawlSession).where(CrawlSession.id == session_id))
                session_obj = res.scalar_one_or_none()
                if session_obj:
                    metrics_json = session_obj.llm_metrics_json or {}
                    metrics_json["hypotheses"] = hyp_list
                    session_obj.llm_metrics_json = metrics_json
                    await db.commit()
            except Exception as e:
                logger.warning(f"Failed to persist hypotheses to DB: {e}")

    async def load_hypotheses(self, session_id: str, db: Optional[AsyncSession] = None) -> List[Hypothesis]:
        """Restore hypotheses for a given session from cache or DB."""
        raw_list = self._hypotheses_cache.get(session_id)
        if not raw_list and db:
            try:
                res = await db.execute(select(CrawlSession).where(CrawlSession.id == session_id))
                session_obj = res.scalar_one_or_none()
                if session_obj and session_obj.llm_metrics_json:
                    raw_list = session_obj.llm_metrics_json.get("hypotheses", [])
                    if raw_list:
                        self._hypotheses_cache[session_id] = raw_list
            except Exception as e:
                logger.warning(f"Error loading hypotheses from DB: {e}")

        if not raw_list:
            return []
        return [Hypothesis.model_validate(r) for r in raw_list]

    def clear(self, session_id: Optional[str] = None) -> None:
        """Clear cache for session or all sessions (useful for test resets)."""
        if session_id:
            self._state_cache.pop(session_id, None)
            self._graph_cache.pop(session_id, None)
            self._hypotheses_cache.pop(session_id, None)
        else:
            self._state_cache.clear()
            self._graph_cache.clear()
            self._hypotheses_cache.clear()


# Global state store singleton
state_store = AgentStateStore()
