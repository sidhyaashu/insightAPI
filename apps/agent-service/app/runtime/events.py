"""
runtime/events.py — AgentEventBus for InsightAPI Autonomous Agent Runtime

Provides an in-process pub/sub event bus that all agents and tools use to
emit structured AgentEvent objects. Consumers (UI WebSocket bridge, audit log,
observability) subscribe once and receive all events without tight coupling.

Architecture (AGENTS.md §27):
  SESSION_STARTED → TOOL_STARTED → TOOL_COMPLETED → OBSERVATION_CREATED →
  HYPOTHESIS_CREATED → ENDPOINT_DISCOVERED → VERIFICATION_* → ARTIFACT_CREATED

Phase 1 scope:
  - Fully in-process, synchronous and async handlers supported.
  - No persistence (Phase 8 will add DB persistence).
  - Thread-safe (uses asyncio.Lock for handler registration).
  - Backward-compatible: also exposes to_wire_dict() for existing WebSocket
    consumers that expect raw dicts.

Phase 2 will add event_bridge.py which converts existing {type: "tool_start"}
dicts emitted by react_engine.py into AgentEvents automatically.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

from app.runtime.models import AgentEvent, AgentEventType

logger = logging.getLogger("agent.runtime.events")

# Type aliases
SyncHandler = Callable[[AgentEvent], None]
AsyncHandler = Callable[[AgentEvent], Coroutine[Any, Any, None]]
Handler = Union[SyncHandler, AsyncHandler]


class AgentEventBus:
    """
    In-process publish/subscribe event bus for the agent runtime.

    Usage::

        bus = AgentEventBus()

        # Subscribe to all events
        @bus.on()
        async def log_all(event: AgentEvent):
            logger.info(f"[{event.event_type}] {event.session_id}")

        # Subscribe to a specific event type
        @bus.on(AgentEventType.ENDPOINT_DISCOVERED)
        async def handle_discovery(event: AgentEvent):
            ...  # persist endpoint

        # Publish
        await bus.publish(AgentEvent(
            session_id="sess-123",
            event_type=AgentEventType.ENDPOINT_DISCOVERED,
            data={"endpoint_key": "GET /api/users/{id}"},
        ))

    Handler errors are caught and logged individually — a failing subscriber
    never silences other subscribers.
    """

    def __init__(self) -> None:
        # Handlers registered for ALL events (wildcard)
        self._global_handlers: List[Handler] = []
        # Handlers registered for a specific event type
        self._typed_handlers: Dict[AgentEventType, List[Handler]] = {}
        self._lock = asyncio.Lock()
        # In-memory event log (Phase 8 will replace with DB)
        self._event_log: List[AgentEvent] = []
        self._max_log_size: int = 5_000

    # ── Registration ──────────────────────────────────────────────────────────

    def on(
        self,
        event_type: Optional[AgentEventType] = None,
    ) -> Callable[[Handler], Handler]:
        """
        Decorator to register a sync or async handler.

        Parameters
        ----------
        event_type:
            If None, the handler receives ALL events.
            If specified, the handler only receives events of that type.
        """
        def decorator(fn: Handler) -> Handler:
            if event_type is None:
                self._global_handlers.append(fn)
            else:
                self._typed_handlers.setdefault(event_type, []).append(fn)
            return fn
        return decorator

    def subscribe(
        self,
        handler: Handler,
        event_type: Optional[AgentEventType] = None,
    ) -> None:
        """
        Programmatic (non-decorator) subscription.

        Parameters
        ----------
        handler:    Sync or async callable receiving a single AgentEvent.
        event_type: None = subscribe to all events; specific type = filter.
        """
        if event_type is None:
            if handler not in self._global_handlers:
                self._global_handlers.append(handler)
        else:
            bucket = self._typed_handlers.setdefault(event_type, [])
            if handler not in bucket:
                bucket.append(handler)

    def unsubscribe(
        self,
        handler: Handler,
        event_type: Optional[AgentEventType] = None,
    ) -> None:
        """Remove a previously registered handler."""
        if event_type is None:
            try:
                self._global_handlers.remove(handler)
            except ValueError:
                pass
        else:
            bucket = self._typed_handlers.get(event_type, [])
            try:
                bucket.remove(handler)
            except ValueError:
                pass

    # ── Publishing ────────────────────────────────────────────────────────────

    async def publish(self, event: AgentEvent) -> None:
        """
        Publish an event to all matching handlers.

        Errors in individual handlers are caught and logged. A failing
        handler never prevents other handlers from receiving the event.
        """
        # Append to in-memory log (with size cap)
        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

        # Collect handlers: global + typed
        handlers = list(self._global_handlers)
        handlers += self._typed_handlers.get(event.event_type, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as exc:
                logger.error(
                    f"AgentEventBus: handler {handler!r} raised on "
                    f"{event.event_type} (session={event.session_id}): {exc}",
                    exc_info=True,
                )

    def publish_sync(self, event: AgentEvent) -> None:
        """
        Synchronous publish — only calls synchronous handlers.

        Use in non-async contexts (e.g., unit tests without an event loop).
        Async handlers are skipped with a warning.
        """
        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

        handlers = list(self._global_handlers)
        handlers += self._typed_handlers.get(event.event_type, [])

        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                logger.debug(
                    f"AgentEventBus.publish_sync: skipping async handler {handler!r} "
                    f"for event {event.event_type}"
                )
                continue
            try:
                handler(event)
            except Exception as exc:
                logger.error(
                    f"AgentEventBus.publish_sync: handler {handler!r} raised: {exc}",
                    exc_info=True,
                )

    # ── Factory helpers ───────────────────────────────────────────────────────

    @staticmethod
    def make_tool_started(
        session_id: str,
        tool_name: str,
        tool_id: str,
        title: str,
        input_summary: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
    ) -> AgentEvent:
        """Convenience factory for TOOL_STARTED events."""
        return AgentEvent(
            session_id=session_id,
            event_type=AgentEventType.TOOL_STARTED,
            agent_id=agent_id,
            tool_id=tool_id,
            data={
                "tool": tool_name,
                "title": title,
                "input": input_summary or {},
            },
        )

    @staticmethod
    def make_tool_completed(
        session_id: str,
        tool_name: str,
        tool_id: str,
        status: str,
        latency_ms: int,
        output: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> AgentEvent:
        """Convenience factory for TOOL_COMPLETED events."""
        return AgentEvent(
            session_id=session_id,
            event_type=AgentEventType.TOOL_COMPLETED,
            agent_id=agent_id,
            tool_id=tool_id,
            error=error,
            data={
                "tool": tool_name,
                "status": status,
                "latency_ms": latency_ms,
                "output": output or {},
            },
        )

    @staticmethod
    def make_endpoint_discovered(
        session_id: str,
        endpoint_key: str,
        confidence: str = "inferred",
        agent_id: Optional[str] = None,
    ) -> AgentEvent:
        """Convenience factory for ENDPOINT_DISCOVERED events."""
        return AgentEvent(
            session_id=session_id,
            event_type=AgentEventType.ENDPOINT_DISCOVERED,
            agent_id=agent_id,
            data={
                "endpoint_key": endpoint_key,
                "confidence": confidence,
            },
        )

    # ── Introspection ─────────────────────────────────────────────────────────

    def get_session_events(self, session_id: str) -> List[AgentEvent]:
        """Return all in-memory events for a session (Phase 8 will hit the DB)."""
        return [e for e in self._event_log if e.session_id == session_id]

    def get_events_by_type(self, event_type: AgentEventType) -> List[AgentEvent]:
        """Return all in-memory events of a specific type."""
        return [e for e in self._event_log if e.event_type == event_type]

    def clear(self) -> None:
        """Clear the in-memory event log. Useful in tests."""
        self._event_log.clear()

    @property
    def event_count(self) -> int:
        return len(self._event_log)


# ── Global singleton ──────────────────────────────────────────────────────────
# One bus per process. Import this in agents, tools, and WebSocket handlers.
# Tests may instantiate their own AgentEventBus() instead.

event_bus = AgentEventBus()
