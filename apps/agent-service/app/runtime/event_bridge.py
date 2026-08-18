"""
runtime/event_bridge.py — Bidirectional adapter between legacy raw dicts and typed AgentEvents.

Phase 2 responsibility:
  - Convert legacy {type: "tool_start", ...} dicts → AgentEvent
  - Convert AgentEvent → wire dict (already handled by AgentEvent.to_wire())
  - Provide a publish helper that tools and react_engine.py can call
    without restructuring the existing yield-based generator.

Design rules:
  - Never modifies the raw dict before it is yielded to the WebSocket client.
  - All mapping is best-effort; unknown event types map to AgentEventType.TOOL_STARTED.
  - Failures in bridge/publish are ALWAYS silenced — the streaming path must never
    fail because of the event bridge.
  - Zero circular imports: bridge imports from runtime.models and runtime.events only.

Usage in an async generator (react_engine.py pattern)::

    from app.runtime.event_bridge import publish_raw

    raw = {"type": "tool_start", "tool_id": "t-001", "tool": "probe_http_endpoint", ...}
    await publish_raw(session_id, raw)   # fire-and-forget; does not change raw
    yield raw                            # unchanged to WebSocket client
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.runtime.events import event_bus
from app.runtime.models import AgentEvent, AgentEventType

logger = logging.getLogger("agent.runtime.event_bridge")

# ── Legacy dict type → AgentEventType mapping ─────────────────────────────────
# Only the types currently emitted by react_engine.py are mapped here.
# Unknown types fall back to TOOL_STARTED.

_TYPE_MAP: Dict[str, AgentEventType] = {
    "tool_start": AgentEventType.TOOL_STARTED,
    "tool_started": AgentEventType.TOOL_STARTED,
    "tool_result": AgentEventType.TOOL_COMPLETED,
    "tool_completed": AgentEventType.TOOL_COMPLETED,
    "tool_failed": AgentEventType.TOOL_FAILED,
    "approval_required": AgentEventType.APPROVAL_REQUIRED,
    "approval_received": AgentEventType.APPROVAL_RECEIVED,
    "token": AgentEventType.LLM_TOKEN,
    "done": AgentEventType.SESSION_COMPLETED,
    "endpoint_discovered": AgentEventType.ENDPOINT_DISCOVERED,
    "endpoint_verified": AgentEventType.ENDPOINT_VERIFIED,
    "hypothesis_created": AgentEventType.HYPOTHESIS_CREATED,
    "hypothesis_tested": AgentEventType.HYPOTHESIS_TESTED,
    "observation_created": AgentEventType.OBSERVATION_CREATED,
    "subagent_started": AgentEventType.SUBAGENT_STARTED,
    "subagent_completed": AgentEventType.SUBAGENT_COMPLETED,
    "artifact_created": AgentEventType.ARTIFACT_CREATED,
    "session_started": AgentEventType.SESSION_STARTED,
    "session_completed": AgentEventType.SESSION_COMPLETED,
    "plan_created": AgentEventType.PLAN_CREATED,
    "budget_warning": AgentEventType.BUDGET_WARNING,
    "verification_started": AgentEventType.VERIFICATION_STARTED,
    "verification_completed": AgentEventType.VERIFICATION_COMPLETED,
}


def raw_dict_to_agent_event(
    raw: Dict[str, Any],
    session_id: str,
    agent_id: Optional[str] = None,
) -> AgentEvent:
    """
    Convert a legacy raw event dict into a typed AgentEvent.

    The original ``raw`` dict is embedded in ``AgentEvent.data`` so no
    information is lost. The caller still yields the original dict to
    the WebSocket client — this function only produces the typed version
    for the event bus.

    Parameters
    ----------
    raw:        The raw dict currently yielded by react_engine / tools.
    session_id: Active investigation session ID.
    agent_id:   Emitting agent ID (optional; None for legacy paths).
    """
    raw_type = raw.get("type", "")
    event_type = _TYPE_MAP.get(raw_type, AgentEventType.TOOL_STARTED)

    # Extract well-known fields from the raw dict
    tool_id = raw.get("tool_id")
    error = raw.get("error")

    # The data payload is everything from the raw dict except fields
    # that are already first-class AgentEvent attributes.
    excluded_top_level = {"type", "tool_id", "error"}
    data = {k: v for k, v in raw.items() if k not in excluded_top_level}

    return AgentEvent(
        session_id=session_id,
        event_type=event_type,
        agent_id=agent_id,
        tool_id=tool_id,
        error=error,
        data=data,
    )


async def publish_raw(
    session_id: str,
    raw: Dict[str, Any],
    agent_id: Optional[str] = None,
) -> None:
    """
    Convert a raw event dict to a typed AgentEvent and publish it to the global
    event_bus. This is a fire-and-forget call — any failure is logged and swallowed
    so it never interrupts the streaming generator.

    Intended usage in react_engine.py::

        raw = {"type": "tool_start", ...}
        await publish_raw(session_id, raw)
        yield raw   # unchanged

    Parameters
    ----------
    session_id: The current investigation session ID.
    raw:        The raw event dict about to be yielded.
    agent_id:   Optional emitting agent ID.
    """
    try:
        event = raw_dict_to_agent_event(raw, session_id, agent_id)
        await event_bus.publish(event)
    except Exception as exc:
        # Bridge failures MUST NOT affect the streaming path
        logger.debug(f"event_bridge.publish_raw silenced error: {exc}")


def agent_event_to_wire(event: AgentEvent) -> Dict[str, Any]:
    """
    Convert a typed AgentEvent back to the wire format expected by the
    WebSocket client. Delegates to AgentEvent.to_wire().
    """
    return event.to_wire()
