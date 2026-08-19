"""
runtime/debug/recorder.py — Structured Debug Event Recorder & File Exporter.

Records all execution traces, decisions, network traffic, browser snapshots,
errors, and timeline events to memory and disk in debug/<session_id>/
(AGENTS.md §27, Debug Prompt §26, §27, §28, §29).
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.runtime.debug.models import (
    ActionTrace,
    AIDiagnosticReport,
    BrowserActionTrace,
    DebugLevel,
    DebugSession,
    GraphMutationTrace,
    HypothesisTrace,
    ModelTrace,
    NetworkTrace,
    PlannerDecisionTrace,
    PolicyEvaluationTrace,
    RetryTrace,
    StuckDetectionTrace,
    VerificationTrace,
)
from app.runtime.debug.redaction import sanitize_data
from app.runtime.debug.diagnostics import (
    RootCauseAnalyzer,
    generate_ai_diagnostic_md,
)
from app.runtime.debug.correlation import correlator
from app.runtime.debug.profiler import profiler
from app.runtime.debug.tracer import tracer
from app.runtime.events import event_bus
from app.runtime.models import AgentEvent, AgentEventType

logger = logging.getLogger("agent.runtime.debug.recorder")

DEFAULT_DEBUG_ROOT = Path("debug")


class DebugRecorder:
    """
    Central recorder aggregating all debugging telemetry, traces, and file artifacts.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or DEFAULT_DEBUG_ROOT
        self._sessions: Dict[str, DebugSession] = {}
        self._timeline: Dict[str, List[str]] = {}
        self._actions: Dict[str, List[Dict[str, Any]]] = {}
        self._network: Dict[str, List[Dict[str, Any]]] = {}
        self._planner: Dict[str, List[Dict[str, Any]]] = {}
        self._browser: Dict[str, List[Dict[str, Any]]] = {}
        self._policy: Dict[str, List[Dict[str, Any]]] = {}
        self._models: Dict[str, List[Dict[str, Any]]] = {}
        self._hypotheses: Dict[str, List[Dict[str, Any]]] = {}
        self._verifications: Dict[str, List[Dict[str, Any]]] = {}
        self._mutations: Dict[str, List[Dict[str, Any]]] = {}
        self._errors: Dict[str, List[Dict[str, Any]]] = {}
        self._retries: Dict[str, List[Dict[str, Any]]] = {}
        self._stuck_traces: Dict[str, List[Dict[str, Any]]] = {}

    def start_session(
        self,
        session_id: str,
        target_url: str,
        goal_description: str,
        user_id: Optional[str] = None,
        debug_level: DebugLevel = DebugLevel.NORMAL,
    ) -> DebugSession:
        """Initialize a new debug session."""
        session = DebugSession(
            session_id=session_id,
            user_id=user_id,
            target_url=target_url,
            goal_description=goal_description,
            debug_level=debug_level,
        )
        self._sessions[session_id] = session
        self._timeline[session_id] = []
        self._actions[session_id] = []
        self._network[session_id] = []
        self._planner[session_id] = []
        self._browser[session_id] = []
        self._policy[session_id] = []
        self._models[session_id] = []
        self._hypotheses[session_id] = []
        self._verifications[session_id] = []
        self._mutations[session_id] = []
        self._errors[session_id] = []
        self._retries[session_id] = []
        self._stuck_traces[session_id] = []

        profiler.start_session(session_id)
        self.record_timeline(session_id, "SESSION_START", f"Goal: {goal_description} -> {target_url}")
        return session

    def record_timeline(self, session_id: str, category: str, message: str) -> str:
        """Format and append a human-readable timeline entry."""
        session = self._sessions.get(session_id)
        start_time = session.start_time if session else datetime.now(timezone.utc)
        elapsed_sec = (datetime.now(timezone.utc) - start_time).total_seconds()
        mins = int(elapsed_sec // 60)
        secs = elapsed_sec % 60
        entry = f"[{mins:02d}:{secs:06.3f}] {category.upper():<12} {message}"
        self._timeline.setdefault(session_id, []).append(entry)
        return entry

    def record_planner_decision(self, session_id: str, trace: PlannerDecisionTrace) -> None:
        """Record planner cycle deliberation and candidates."""
        sanitized = sanitize_data(trace.model_dump())
        self._planner.setdefault(session_id, []).append(sanitized)
        self.record_timeline(
            session_id,
            "PLAN",
            f"Selected {trace.selected_action} -> {trace.selected_target} ({trace.selection_rationale})",
        )

    def record_action(self, session_id: str, trace: ActionTrace) -> None:
        """Record an autonomous action lifecycle event."""
        sanitized = sanitize_data(trace.model_dump())
        self._actions.setdefault(session_id, []).append(sanitized)
        correlator.link(
            session_id=session_id,
            action_id=trace.action_id,
            span_id=trace.span_id,
        )
        self.record_timeline(
            session_id,
            "ACTION",
            f"{trace.action_id} {trace.action_type} -> {trace.target} [{trace.state.value.upper()}] ({trace.duration_ms or 0}ms)",
        )

    def record_policy_evaluation(self, session_id: str, trace: PolicyEvaluationTrace) -> None:
        """Record policy / safety evaluation."""
        sanitized = sanitize_data(trace.model_dump())
        self._policy.setdefault(session_id, []).append(sanitized)
        self.record_timeline(
            session_id,
            "POLICY",
            f"{trace.action_id} Decision={trace.decision.upper()} Risk={trace.risk_level} ({trace.reason})",
        )

    def record_browser_action(self, session_id: str, trace: BrowserActionTrace) -> None:
        """Record browser interaction details."""
        sanitized = sanitize_data(trace.model_dump())
        self._browser.setdefault(session_id, []).append(sanitized)
        self.record_timeline(
            session_id,
            "BROWSER",
            f"{trace.action_type} {trace.before_url} -> {trace.after_url} (Found={trace.element_found})",
        )

    def record_network_trace(self, session_id: str, trace: NetworkTrace) -> None:
        """Record sanitized network event and correlate identifiers."""
        sanitized = sanitize_data(trace.model_dump())
        self._network.setdefault(session_id, []).append(sanitized)
        correlator.link(
            session_id=session_id,
            action_id=trace.action_id,
            request_id=trace.request_id,
            endpoint_id=trace.endpoint_id,
            observation_id=trace.observation_id,
        )
        status_str = f"-> {trace.response_status}" if trace.response_status else f"FAILED ({trace.failure_type.value if trace.failure_type else 'error'})"
        self.record_timeline(
            session_id,
            "NETWORK",
            f"{trace.request_id} {trace.method} {trace.normalized_template} {status_str} ({trace.duration_ms}ms)",
        )

    def record_model_trace(self, session_id: str, trace: ModelTrace) -> None:
        """Record model/LLM invocation audit."""
        sanitized = sanitize_data(trace.model_dump())
        self._models.setdefault(session_id, []).append(sanitized)
        self.record_timeline(
            session_id,
            "MODEL",
            f"{trace.provider}/{trace.model} ({trace.role}) Tokens={trace.total_tokens} Latency={trace.latency_ms}ms",
        )

    def record_hypothesis(self, session_id: str, trace: HypothesisTrace) -> None:
        """Record hypothesis creation and evaluation."""
        sanitized = sanitize_data(trace.model_dump())
        self._hypotheses.setdefault(session_id, []).append(sanitized)
        correlator.link(session_id=session_id, hypothesis_id=trace.hypothesis_id)
        self.record_timeline(
            session_id,
            "HYPOTHESIS",
            f"{trace.hypothesis_id} {trace.method} {trace.template_path} -> {trace.status.upper()} (Conf={trace.confidence:.2f})",
        )

    def record_verification(self, session_id: str, trace: VerificationTrace) -> None:
        """Record verification test cases and outcome."""
        sanitized = sanitize_data(trace.model_dump())
        self._verifications.setdefault(session_id, []).append(sanitized)
        self.record_timeline(
            session_id,
            "VERIFIED" if trace.outcome.lower() == "verified" else "VERIF_FAIL",
            f"{trace.endpoint_key} -> {trace.outcome.upper()} ({trace.rationale})",
        )

    def record_graph_mutation(self, session_id: str, trace: GraphMutationTrace) -> None:
        """Record graph addition or update."""
        sanitized = sanitize_data(trace.model_dump())
        self._mutations.setdefault(session_id, []).append(sanitized)
        self.record_timeline(
            session_id,
            "GRAPH_MUT",
            f"{trace.mutation_type} on {trace.target_id} ({trace.reason})",
        )

    def record_error(self, session_id: str, error_type: str, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Record an error event."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": error_type,
            "message": message,
            "context": sanitize_data(context or {}),
        }
        self._errors.setdefault(session_id, []).append(entry)
        self.record_timeline(session_id, "ERROR", f"{error_type}: {message}")

    def record_retry(self, session_id: str, trace: RetryTrace) -> None:
        """Record a self-healing retry event."""
        sanitized = sanitize_data(trace.model_dump())
        self._retries.setdefault(session_id, []).append(sanitized)
        self.record_timeline(
            session_id,
            "RETRY",
            f"Retry #{trace.retry_number} on {trace.action_id}: Strategy='{trace.recovery_strategy}' -> {trace.result_status.upper()}",
        )

    def record_stuck(self, session_id: str, trace: StuckDetectionTrace) -> None:
        """Record stuck detection alert."""
        sanitized = sanitize_data(trace.model_dump())
        self._stuck_traces.setdefault(session_id, []).append(sanitized)
        if trace.is_stuck:
            self.record_timeline(session_id, "STUCK_ALERT", trace.stuck_reason)

    def complete_session(
        self,
        session_id: str,
        final_status: str = "completed",
        final_reason: Optional[str] = None,
        world_model: Optional[Any] = None,
    ) -> AIDiagnosticReport:
        """
        Finalize investigation session, run root-cause analysis, and persist all debug files.
        """
        session = self._sessions.get(session_id)
        if not session:
            session = self.start_session(session_id, "unknown", "unknown")

        session.end_time = datetime.now(timezone.utc)
        session.duration_ms = max(0, int((session.end_time - session.start_time).total_seconds() * 1000))
        session.final_status = final_status
        session.final_reason = final_reason

        actions = self._actions.get(session_id, [])
        network = self._network.get(session_id, [])
        errors = self._errors.get(session_id, [])
        timeline = self._timeline.get(session_id, [])

        endpoints_discovered = len(self._network.get(session_id, []))
        endpoints_verified = len([v for v in self._verifications.get(session_id, []) if v.get("outcome", "").lower() == "verified"])

        stuck_trace = self._stuck_traces.get(session_id, [{}])[-1] if self._stuck_traces.get(session_id) else {}
        is_stuck = bool(stuck_trace.get("is_stuck", False))
        stuck_reason = stuck_trace.get("stuck_reason")

        # Automated Root Cause Analysis
        category, confidence, root_evidence, recommendation = RootCauseAnalyzer.analyze(
            session_id=session_id,
            actions=actions,
            errors=errors,
            network_traces=network,
            discovered_count=endpoints_discovered,
            verified_count=endpoints_verified,
            is_stuck=is_stuck,
            stuck_reason=stuck_reason,
        )

        successful_actions = sum(1 for a in actions if a.get("state") == "succeeded")
        failed_actions = sum(1 for a in actions if a.get("state") == "failed")
        pages_explored = list(set([a.get("target", "") for a in actions if a.get("action_type") == "navigate"]))

        report = AIDiagnosticReport(
            session_id=session_id,
            target_url=session.target_url,
            goal=session.goal_description,
            status=final_status,
            duration_seconds=session.duration_ms / 1000.0,
            total_actions=len(actions),
            successful_actions=successful_actions,
            failed_actions=failed_actions,
            retries_count=len(self._retries.get(session_id, [])),
            pages_explored=pages_explored,
            endpoints_discovered_count=endpoints_discovered,
            endpoints_verified_count=endpoints_verified,
            unresolved_hypotheses_count=len([h for h in self._hypotheses.get(session_id, []) if h.get("status") != "verified"]),
            stopping_reason=final_reason or ("Goal achieved" if final_status == "completed" else "Terminated"),
            root_cause=category,
            root_cause_confidence=confidence,
            root_cause_evidence=root_evidence,
            recommended_next_experiment=recommendation,
        )

        self.record_timeline(session_id, "SESSION_DONE", f"Status: {final_status.upper()} (RootCause={category.value})")

        # Persist debug directory files
        try:
            self._flush_to_disk(session_id, report, world_model)
        except Exception as e:
            logger.warning(f"Error persisting debug files to disk for session {session_id}: {e}")

        return report

    def _flush_to_disk(self, session_id: str, report: AIDiagnosticReport, world_model: Optional[Any] = None) -> Path:
        """Write all debug artifacts to debug/<session_id>/."""
        session_dir = self.base_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        session = self._sessions.get(session_id)
        summary_data = {
            "session": session.model_dump() if session else {},
            "report": report.model_dump(),
            "profile": profiler.get_profile(session_id).model_dump(),
        }

        # 1. summary.json
        with open(session_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, default=str)

        # 2. AI_DIAGNOSTIC.md
        diag_md = generate_ai_diagnostic_md(report, self._timeline.get(session_id, []))
        with open(session_dir / "AI_DIAGNOSTIC.md", "w", encoding="utf-8") as f:
            f.write(diag_md)

        # 3. timeline.jsonl
        with open(session_dir / "timeline.jsonl", "w", encoding="utf-8") as f:
            for line in self._timeline.get(session_id, []):
                f.write(json.dumps({"entry": line}) + "\n")

        # 4. actions.jsonl
        with open(session_dir / "actions.jsonl", "w", encoding="utf-8") as f:
            for act in self._actions.get(session_id, []):
                f.write(json.dumps(act, default=str) + "\n")

        # 5. network.jsonl
        with open(session_dir / "network.jsonl", "w", encoding="utf-8") as f:
            for net in self._network.get(session_id, []):
                f.write(json.dumps(net, default=str) + "\n")

        # 6. hypotheses.jsonl
        with open(session_dir / "hypotheses.jsonl", "w", encoding="utf-8") as f:
            for hyp in self._hypotheses.get(session_id, []):
                f.write(json.dumps(hyp, default=str) + "\n")

        # 7. policy.jsonl
        with open(session_dir / "policy.jsonl", "w", encoding="utf-8") as f:
            for pol in self._policy.get(session_id, []):
                f.write(json.dumps(pol, default=str) + "\n")

        # 8. errors.jsonl
        with open(session_dir / "errors.jsonl", "w", encoding="utf-8") as f:
            for err in self._errors.get(session_id, []):
                f.write(json.dumps(err, default=str) + "\n")

        # 9. graph.json
        if world_model and hasattr(world_model, "to_dict"):
            with open(session_dir / "graph.json", "w", encoding="utf-8") as f:
                json.dump(world_model.to_dict(), f, indent=2, default=str)

        return session_dir

    # Data Retrieval Helpers for API Endpoints
    def get_session(self, session_id: str) -> Optional[DebugSession]:
        return self._sessions.get(session_id)

    def get_timeline(self, session_id: str) -> List[str]:
        return list(self._timeline.get(session_id, []))

    def get_actions(self, session_id: str) -> List[Dict[str, Any]]:
        return list(self._actions.get(session_id, []))

    def get_network(self, session_id: str) -> List[Dict[str, Any]]:
        return list(self._network.get(session_id, []))

    def get_errors(self, session_id: str) -> List[Dict[str, Any]]:
        return list(self._errors.get(session_id, []))

    def get_hypotheses(self, session_id: str) -> List[Dict[str, Any]]:
        return list(self._hypotheses.get(session_id, []))

    def clear(self, session_id: Optional[str] = None) -> None:
        """Clear memory cache."""
        if session_id:
            self._sessions.pop(session_id, None)
            self._timeline.pop(session_id, None)
            self._actions.pop(session_id, None)
            self._network.pop(session_id, None)
            self._planner.pop(session_id, None)
            self._browser.pop(session_id, None)
            self._policy.pop(session_id, None)
            self._models.pop(session_id, None)
            self._hypotheses.pop(session_id, None)
            self._verifications.pop(session_id, None)
            self._mutations.pop(session_id, None)
            self._errors.pop(session_id, None)
            self._retries.pop(session_id, None)
            self._stuck_traces.pop(session_id, None)
        else:
            self._sessions.clear()
            self._timeline.clear()
            self._actions.clear()
            self._network.clear()
            self._planner.clear()
            self._browser.clear()
            self._policy.clear()
            self._models.clear()
            self._hypotheses.clear()
            self._verifications.clear()
            self._mutations.clear()
            self._errors.clear()
            self._retries.clear()
            self._stuck_traces.clear()


# Global recorder singleton
recorder = DebugRecorder()
