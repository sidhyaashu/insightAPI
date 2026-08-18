"""
runtime/agents/base.py — Base class and contracts for Specialized Agents.

Reference (AGENTS.md §15, §16, §17):
  Child agents have:
    task_id, agent_id, parent_agent_id, role, goal, allowed_tools, budget, state, result, evidence
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.runtime.models import (
    Action,
    AgentBudget,
    AgentEvent,
    AgentEventType,
    AgentState,
    Evidence,
    Observation,
)
from app.runtime.events import event_bus


class AgentTask(BaseModel):
    """A delegated task assigned to a specialized child agent."""
    id: str = Field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    parent_agent_id: Optional[str] = None
    role: str
    goal: str
    target: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    max_steps: int = 10
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentResult(BaseModel):
    """Structured result returned by a specialized child agent."""
    task_id: str
    agent_id: str
    role: str
    status: str  # "completed" | "failed" | "blocked"
    summary: str
    observations: List[Observation] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    discovered_endpoints: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    latency_ms: int = 0


class BaseAgent(ABC):
    """
    Abstract base class for specialized agent roles (Explorer, Network, Verifier).
    """

    def __init__(self, agent_id: Optional[str] = None) -> None:
        self.agent_id = agent_id or f"{self.__class__.__name__.lower()}-{uuid.uuid4().hex[:6]}"

    @abstractmethod
    async def execute(
        self,
        task: AgentTask,
        state: AgentState,
    ) -> AgentResult:
        """Execute the assigned task against the current agent state and return AgentResult."""
        pass

    async def emit_event(
        self,
        session_id: str,
        event_type: AgentEventType,
        data: Dict[str, Any],
        error: Optional[str] = None,
    ) -> None:
        """Publish a typed event to the global AgentEventBus."""
        event = AgentEvent(
            session_id=session_id,
            event_type=event_type,
            agent_id=self.agent_id,
            data=data,
            error=error,
        )
        await event_bus.publish(event)
