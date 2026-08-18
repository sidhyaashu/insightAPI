"""
runtime/observability.py — Session Telemetry, Metric Tracking & Audit Logging.

Architecture (AGENTS.md §27, §28):
  - Passive event-driven telemetry subscriber attached to AgentEventBus.
  - Non-intrusively tracks tool execution counts, latencies, tokens, errors, and timeline.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.runtime.models import AgentEvent, AgentEventType
from app.runtime.events import event_bus

logger = logging.getLogger("agent.runtime.observability")


class SessionMetrics(BaseModel):
    """Aggregated execution telemetry metrics for an investigation session."""
    session_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    total_events: int = 0
    tools_executed: Dict[str, int] = Field(default_factory=dict)
    tool_latencies_ms: Dict[str, List[int]] = Field(default_factory=dict)
    endpoints_discovered_count: int = 0
    endpoints_verified_count: int = 0
    hypotheses_tested_count: int = 0
    errors_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


class SessionTelemetryTracker:
    """
    Subscribes to AgentEventBus and aggregates real-time session telemetry.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionMetrics] = {}
        self._audit_logs: Dict[str, List[Dict[str, Any]]] = {}

        # Automatically hook into the event bus
        event_bus.subscribe(self.handle_event)

    def handle_event(self, event: AgentEvent) -> None:
        """Process an incoming event and update session metrics."""
        session_id = event.session_id
        if not session_id:
            return

        if session_id not in self._sessions:
            self._sessions[session_id] = SessionMetrics(session_id=session_id)
            self._audit_logs[session_id] = []

        metrics = self._sessions[session_id]
        metrics.total_events += 1

        # Append to audit log
        self._audit_logs[session_id].append({
            "timestamp": event.created_at.isoformat(),
            "event_id": event.id,
            "event_type": event.event_type.value,
            "agent_id": event.agent_id,
            "tool_id": event.tool_id,
            "error": event.error,
            "data": event.data,
        })

        if event.error:
            metrics.errors_count += 1

        # Event-specific telemetry updates
        if event.event_type == AgentEventType.SESSION_COMPLETED:
            metrics.completed_at = event.created_at

        elif event.event_type == AgentEventType.TOOL_COMPLETED:
            tool_name = event.data.get("tool", "unknown_tool")
            latency = event.data.get("latency_ms", 0)
            metrics.tools_executed[tool_name] = metrics.tools_executed.get(tool_name, 0) + 1
            if tool_name not in metrics.tool_latencies_ms:
                metrics.tool_latencies_ms[tool_name] = []
            metrics.tool_latencies_ms[tool_name].append(latency)

        elif event.event_type == AgentEventType.ENDPOINT_DISCOVERED:
            metrics.endpoints_discovered_count += 1

        elif event.event_type == AgentEventType.ENDPOINT_VERIFIED:
            metrics.endpoints_verified_count += 1

        elif event.event_type == AgentEventType.HYPOTHESIS_TESTED:
            metrics.hypotheses_tested_count += 1

    def get_metrics(self, session_id: str) -> Optional[SessionMetrics]:
        """Retrieve aggregated metrics for a session."""
        return self._sessions.get(session_id)

    def get_audit_log(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve the chronological audit log of events for a session."""
        return list(self._audit_logs.get(session_id, []))

    def clear(self, session_id: Optional[str] = None) -> None:
        """Clear telemetry state."""
        if session_id:
            self._sessions.pop(session_id, None)
            self._audit_logs.pop(session_id, None)
        else:
            self._sessions.clear()
            self._audit_logs.clear()


# Global telemetry singleton
telemetry = SessionTelemetryTracker()
