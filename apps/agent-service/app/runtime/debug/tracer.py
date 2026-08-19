"""
runtime/debug/tracer.py — Hierarchical Execution Tracer & Span Context Manager.

Provides structured nested span management for Investigations, Planning,
Actions, Policy checks, Tools, Browser actuations, and Network events
(AGENTS.md §27, Debug Prompt §4).
"""
from __future__ import annotations

import contextlib
import contextvars
import logging
from typing import Any, Dict, Iterator, List, Optional

from app.runtime.debug.models import SpanStatus, SpanType, TraceSpan

logger = logging.getLogger("agent.runtime.debug.tracer")

# ContextVar holding the current active span in the async task
_current_span_var: contextvars.ContextVar[Optional[TraceSpan]] = contextvars.ContextVar(
    "_current_span_var", default=None
)


class Tracer:
    """
    Hierarchical trace coordinator tracking active execution spans across async tasks.
    """

    def __init__(self) -> None:
        self._spans: Dict[str, List[TraceSpan]] = {}  # session_id -> spans

    def get_current_span(self) -> Optional[TraceSpan]:
        """Retrieve the currently active span in context."""
        return _current_span_var.get()

    @contextlib.contextmanager
    def span(
        self,
        name: str,
        span_type: SpanType,
        session_id: str,
        trace_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        action_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Iterator[TraceSpan]:
        """
        Context manager starting and automatically closing a hierarchical execution span.
        """
        parent_span = self.get_current_span()
        parent_span_id = parent_span.span_id if parent_span else None
        effective_trace_id = trace_id or (parent_span.trace_id if parent_span else f"trc-{session_id[:8]}")

        span_obj = TraceSpan(
            trace_id=effective_trace_id,
            session_id=session_id,
            parent_span_id=parent_span_id,
            name=name,
            span_type=span_type,
            agent_id=agent_id or (parent_span.agent_id if parent_span else None),
            task_id=task_id or (parent_span.task_id if parent_span else None),
            action_id=action_id or (parent_span.action_id if parent_span else None),
            attributes=attributes or {},
        )

        self._spans.setdefault(session_id, []).append(span_obj)
        token = _current_span_var.set(span_obj)

        try:
            yield span_obj
            if span_obj.status == SpanStatus.RUNNING:
                span_obj.finish(SpanStatus.SUCCESS)
        except Exception as e:
            span_obj.finish(SpanStatus.FAILED, error=e)
            raise
        finally:
            _current_span_var.reset(token)

    def get_spans(self, session_id: str) -> List[TraceSpan]:
        """Retrieve all recorded spans for a session."""
        return list(self._spans.get(session_id, []))

    def clear(self, session_id: Optional[str] = None) -> None:
        """Clear spans from memory."""
        if session_id:
            self._spans.pop(session_id, None)
        else:
            self._spans.clear()


# Global tracer singleton
tracer = Tracer()
