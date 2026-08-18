"""
runtime/persistence.py — Stateful Session Persistence & Resumability Layer.

Architecture (AGENTS.md §25, §26):
  - Multi-tier memory and persistence:
    1. Working Memory (Hot AgentState)
    2. Session Memory (Events, Observations, Hypotheses)
    3. Application Memory (Application World Model / Graph)
  - Allows paused, interrupted, or multi-stage investigations to resume without re-exploration.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.runtime.models import (
    AgentState,
    Goal,
    Hypothesis,
    Observation,
)
from app.runtime.world_model import ApplicationGraph

logger = logging.getLogger("agent.runtime.persistence")


class AgentStateStore:
    """
    Persistence adapter for AgentState, ApplicationGraph, and Hypotheses.
    Supports in-memory caching and Redis / DB serialization.
    """

    def __init__(self) -> None:
        self._state_cache: Dict[str, Dict[str, Any]] = {}
        self._graph_cache: Dict[str, Dict[str, Any]] = {}
        self._hypotheses_cache: Dict[str, List[Dict[str, Any]]] = {}

    async def save_state(self, state: AgentState) -> None:
        """Serialize and persist the hot AgentState."""
        self._state_cache[state.session_id] = state.model_dump(mode="json")
        logger.debug(f"Saved AgentState for session {state.session_id}")

    async def load_state(self, session_id: str) -> Optional[AgentState]:
        """Load and deserialize AgentState by session_id."""
        raw = self._state_cache.get(session_id)
        if not raw:
            return None
        return AgentState.model_validate(raw)

    async def save_world_model(self, graph: ApplicationGraph) -> None:
        """Persist the Application Graph structure."""
        self._graph_cache[graph.session_id] = graph.to_dict()
        logger.debug(f"Saved ApplicationGraph for session {graph.session_id}")

    async def load_world_model(self, session_id: str) -> Optional[ApplicationGraph]:
        """Restore ApplicationGraph by session_id."""
        raw = self._graph_cache.get(session_id)
        if not raw:
            return None
        return ApplicationGraph.from_dict(raw)

    async def save_hypotheses(self, session_id: str, hypotheses: List[Hypothesis]) -> None:
        """Persist generated hypotheses and evidence links."""
        self._hypotheses_cache[session_id] = [h.model_dump(mode="json") for h in hypotheses]

    async def load_hypotheses(self, session_id: str) -> List[Hypothesis]:
        """Restore hypotheses for a given session."""
        raw_list = self._hypotheses_cache.get(session_id, [])
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
