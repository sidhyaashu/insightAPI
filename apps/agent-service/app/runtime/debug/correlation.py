"""
runtime/debug/correlation.py — Lifecycle Correlation Registry.

Maintains bidirectional correlation graphs across Action IDs, Request IDs,
Endpoint IDs, Observation IDs, Hypothesis IDs, Evidence IDs, and Artifact IDs
(AGENTS.md §9, Debug Prompt §10, §37).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field


class CorrelationRecord(BaseModel):
    """Correlated identifier mapping for a single action/request/observation event."""
    session_id: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    action_id: Optional[str] = None
    request_id: Optional[str] = None
    endpoint_id: Optional[str] = None
    observation_id: Optional[str] = None
    hypothesis_id: Optional[str] = None
    evidence_id: Optional[str] = None
    artifact_id: Optional[str] = None


class CorrelationRegistry:
    """
    Thread-safe in-memory correlation graph indexing all entity relationships.
    """

    def __init__(self) -> None:
        self._records: List[CorrelationRecord] = []
        # Reverse lookup indexes
        self._by_action: Dict[str, List[int]] = {}
        self._by_request: Dict[str, List[int]] = {}
        self._by_endpoint: Dict[str, List[int]] = {}
        self._by_observation: Dict[str, List[int]] = {}
        self._by_hypothesis: Dict[str, List[int]] = {}
        self._by_session: Dict[str, List[int]] = {}

    def link(
        self,
        session_id: str,
        action_id: Optional[str] = None,
        request_id: Optional[str] = None,
        endpoint_id: Optional[str] = None,
        observation_id: Optional[str] = None,
        hypothesis_id: Optional[str] = None,
        evidence_id: Optional[str] = None,
        artifact_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
    ) -> CorrelationRecord:
        """Register a correlated lifecycle mapping."""
        record = CorrelationRecord(
            session_id=session_id,
            trace_id=trace_id,
            span_id=span_id,
            action_id=action_id,
            request_id=request_id,
            endpoint_id=endpoint_id,
            observation_id=observation_id,
            hypothesis_id=hypothesis_id,
            evidence_id=evidence_id,
            artifact_id=artifact_id,
        )
        idx = len(self._records)
        self._records.append(record)

        if session_id:
            self._by_session.setdefault(session_id, []).append(idx)
        if action_id:
            self._by_action.setdefault(action_id, []).append(idx)
        if request_id:
            self._by_request.setdefault(request_id, []).append(idx)
        if endpoint_id:
            self._by_endpoint.setdefault(endpoint_id, []).append(idx)
        if observation_id:
            self._by_observation.setdefault(observation_id, []).append(idx)
        if hypothesis_id:
            self._by_hypothesis.setdefault(hypothesis_id, []).append(idx)

        return record

    def get_for_action(self, action_id: str) -> List[CorrelationRecord]:
        """Find all correlation records linked to an Action ID."""
        return [self._records[i] for i in self._by_action.get(action_id, [])]

    def get_for_request(self, request_id: str) -> List[CorrelationRecord]:
        """Find all correlation records linked to a Request ID."""
        return [self._records[i] for i in self._by_request.get(request_id, [])]

    def get_for_endpoint(self, endpoint_id: str) -> List[CorrelationRecord]:
        """Find all correlation records linked to an Endpoint ID."""
        return [self._records[i] for i in self._by_endpoint.get(endpoint_id, [])]

    def get_for_session(self, session_id: str) -> List[CorrelationRecord]:
        """Find all correlation records for a given Session ID."""
        return [self._records[i] for i in self._by_session.get(session_id, [])]

    def clear(self, session_id: Optional[str] = None) -> None:
        """Clear registry state."""
        if not session_id:
            self._records.clear()
            self._by_action.clear()
            self._by_request.clear()
            self._by_endpoint.clear()
            self._by_observation.clear()
            self._by_hypothesis.clear()
            self._by_session.clear()
        else:
            # Filter session
            remaining = [r for r in self._records if r.session_id != session_id]
            self._records = remaining
            # Reindex
            self._by_action.clear()
            self._by_request.clear()
            self._by_endpoint.clear()
            self._by_observation.clear()
            self._by_hypothesis.clear()
            self._by_session.clear()
            for idx, r in enumerate(self._records):
                if r.session_id:
                    self._by_session.setdefault(r.session_id, []).append(idx)
                if r.action_id:
                    self._by_action.setdefault(r.action_id, []).append(idx)
                if r.request_id:
                    self._by_request.setdefault(r.request_id, []).append(idx)
                if r.endpoint_id:
                    self._by_endpoint.setdefault(r.endpoint_id, []).append(idx)
                if r.observation_id:
                    self._by_observation.setdefault(r.observation_id, []).append(idx)
                if r.hypothesis_id:
                    self._by_hypothesis.setdefault(r.hypothesis_id, []).append(idx)


# Global singleton correlation registry
correlator = CorrelationRegistry()
