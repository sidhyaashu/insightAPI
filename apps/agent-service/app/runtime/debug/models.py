"""
runtime/debug/models.py — Canonical Typed Models for the Agent Debug & Observability Runtime.

Defines all data models for hierarchical spans, execution traces, planner decisions,
browser/network diagnostics, root cause classifications, and AI diagnostic reports.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class DebugLevel(str, Enum):
    """Granularity level for debug data capture."""
    OFF = "off"
    ERROR = "error"
    NORMAL = "normal"
    VERBOSE = "verbose"
    TRACE = "trace"


class SpanType(str, Enum):
    """Categorization of execution trace spans."""
    INVESTIGATION = "investigation"
    PLANNING = "planning"
    ACTION = "action"
    POLICY = "policy"
    TOOL = "tool"
    BROWSER = "browser"
    NETWORK = "network"
    OBSERVATION = "observation"
    HYPOTHESIS = "hypothesis"
    VERIFICATION = "verification"
    ARTIFACT = "artifact"
    PERSISTENCE = "persistence"
    MODEL = "model"


class SpanStatus(str, Enum):
    """Lifecycle status of an execution span."""
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    RETRIED = "retried"
    SKIPPED = "skipped"


class ActionState(str, Enum):
    """Complete lifecycle states of an autonomous action."""
    PLANNED = "planned"
    POLICY_CHECK = "policy_check"
    APPROVED = "approved"
    DENIED = "denied"
    STARTED = "started"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRIED = "retried"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class NetworkFailureType(str, Enum):
    """Failure diagnostics category for network requests."""
    NETWORK = "network"
    AUTH = "auth"
    SCOPE = "scope"
    POLICY = "policy"
    TIMEOUT = "timeout"
    SERVER = "server"
    CLIENT = "client"
    PARSER = "parser"
    UNKNOWN = "unknown"


class RootCauseCategory(str, Enum):
    """Automated root-cause diagnostic categories."""
    BROWSER_NAVIGATION = "browser_navigation"
    BROWSER_INTERACTION = "browser_interaction"
    AUTHENTICATION = "authentication"
    NETWORK_CAPTURE = "network_capture"
    HTTP_EXECUTION = "http_execution"
    API_NORMALIZATION = "api_normalization"
    GRAPH_UPDATE = "graph_update"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    VERIFICATION = "verification"
    PLANNER = "planner"
    POLICY = "policy"
    BUDGET = "budget"
    PERSISTENCE = "persistence"
    MODEL = "model"
    TOOL = "tool"
    UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE & SPAN MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class SpanEvent(BaseModel):
    """Discrete timestamped event occurring within a span."""
    name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attributes: Dict[str, Any] = Field(default_factory=dict)


class TraceSpan(BaseModel):
    """Hierarchical execution span representing a unit of work."""
    span_id: str = Field(default_factory=lambda: f"span-{uuid.uuid4().hex[:12]}")
    parent_span_id: Optional[str] = None
    trace_id: str
    session_id: str
    name: str
    span_type: SpanType
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    action_id: Optional[str] = None
    status: SpanStatus = SpanStatus.RUNNING
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    events: List[SpanEvent] = Field(default_factory=list)
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    def finish(self, status: SpanStatus = SpanStatus.SUCCESS, error: Optional[Exception] = None) -> None:
        """Mark span completed and calculate elapsed duration."""
        self.end_time = datetime.now(timezone.utc)
        self.status = status
        self.duration_ms = max(0, int((self.end_time - self.start_time).total_seconds() * 1000))
        if error:
            self.error_type = type(error).__name__
            self.error_message = str(error)
            self.status = SpanStatus.FAILED


class DebugSession(BaseModel):
    """Root metadata and container for a complete investigation debug run."""
    debug_session_id: str = Field(default_factory=lambda: f"dbg-{uuid.uuid4().hex[:12]}")
    session_id: str
    investigation_id: Optional[str] = None
    user_id: Optional[str] = None
    target_url: str
    goal_description: str
    debug_level: DebugLevel = DebugLevel.NORMAL
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    final_status: str = "running"
    final_reason: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# SPECIALIZED TRACES
# ═══════════════════════════════════════════════════════════════════════════════

class CandidateActionScore(BaseModel):
    """Score breakdown for an action considered by the planner."""
    action_type: str
    target: str
    score: float
    information_gain: float = 0.0
    risk: float = 0.0
    cost: float = 0.0
    reason: str
    rejected_reason: Optional[str] = None


class PlannerDecisionTrace(BaseModel):
    """Structured audit of a single supervisor planning cycle."""
    decision_id: str = Field(default_factory=lambda: f"dec-{uuid.uuid4().hex[:8]}")
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_url: Optional[str] = None
    current_page_title: Optional[str] = None
    known_endpoints_count: int = 0
    verified_endpoints_count: int = 0
    hypotheses_count: int = 0
    budget_remaining_tools: int = 0
    budget_remaining_seconds: float = 0.0
    candidate_actions: List[CandidateActionScore] = Field(default_factory=list)
    selected_action: Optional[str] = None
    selected_target: Optional[str] = None
    selection_rationale: str
    unresolved_questions: List[str] = Field(default_factory=list)


class ActionTrace(BaseModel):
    """Complete audit record of an autonomous action execution."""
    action_id: str = Field(default_factory=lambda: f"ACT-{uuid.uuid4().hex[:6].upper()}")
    session_id: str
    span_id: Optional[str] = None
    agent_id: str
    action_type: str
    target: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "low_risk"
    policy_decision: str = "allow"
    policy_reason: Optional[str] = None
    state: ActionState = ActionState.PLANNED
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    retry_count: int = 0
    failure_reason: Optional[str] = None
    observation_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)


class BrowserActionTrace(BaseModel):
    """Detailed record of a browser interaction and resulting DOM/AXTree changes."""
    trace_id: str = Field(default_factory=lambda: f"brw-{uuid.uuid4().hex[:8]}")
    action_id: str
    session_id: str
    action_type: str
    target_selector: Optional[str] = None
    target_text: Optional[str] = None
    element_found: bool = True
    element_count: int = 1
    before_url: str
    after_url: str
    page_title: str
    before_state_hash: Optional[str] = None
    after_state_hash: Optional[str] = None
    axtree_summary: Optional[str] = None
    screenshot_ref: Optional[str] = None
    latency_ms: int = 0
    error: Optional[str] = None
    recovery_attempted: Optional[str] = None


class NetworkTrace(BaseModel):
    """Sanitized and correlated network request/response trace."""
    request_id: str = Field(default_factory=lambda: f"REQ-{uuid.uuid4().hex[:6].upper()}")
    action_id: Optional[str] = None
    endpoint_id: Optional[str] = None
    observation_id: Optional[str] = None
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    protocol: str = "REST"
    method: str
    url: str
    normalized_template: str
    query_params: Dict[str, Any] = Field(default_factory=dict)
    request_headers: Dict[str, str] = Field(default_factory=dict)
    request_body: Optional[Any] = None
    response_status: Optional[int] = None
    response_headers: Dict[str, str] = Field(default_factory=dict)
    response_body: Optional[Any] = None
    duration_ms: int = 0
    initiator_page: Optional[str] = None
    initiator_action: Optional[str] = None
    failure_type: Optional[NetworkFailureType] = None
    failure_details: Optional[str] = None


class ModelTrace(BaseModel):
    """Sanitized audit of LLM/model provider invocations."""
    model_request_id: str = Field(default_factory=lambda: f"mdl-{uuid.uuid4().hex[:8]}")
    session_id: str
    action_id: Optional[str] = None
    provider: str
    model: str
    role: str
    prompt_version: str = "v3"
    sanitized_prompt_summary: str
    sanitized_output_summary: str
    latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    is_fallback: bool = False
    fallback_reason: Optional[str] = None
    error: Optional[str] = None


class PolicyEvaluationTrace(BaseModel):
    """Audit of policy and safety evaluation for an action."""
    evaluation_id: str = Field(default_factory=lambda: f"pol-{uuid.uuid4().hex[:8]}")
    session_id: str
    action_id: str
    action_type: str
    target: str
    risk_level: str
    scope_allowed: bool
    ssrf_safe: bool
    budget_allowed: bool
    approval_required: bool
    decision: str
    reason: str


class HypothesisTrace(BaseModel):
    """Lifecycle trace of an endpoint hypothesis and experiments."""
    hypothesis_id: str
    session_id: str
    template_path: str
    method: str
    creation_reason: str
    supporting_observations: List[str] = Field(default_factory=list)
    confidence: float
    status: str
    experiments_designed: int = 0
    experiments_run: int = 0
    experiments_passed: int = 0
    conclusion: str


class VerificationTrace(BaseModel):
    """Detailed audit of verification experiments for an endpoint."""
    verification_id: str = Field(default_factory=lambda: f"ver-{uuid.uuid4().hex[:8]}")
    session_id: str
    hypothesis_id: Optional[str] = None
    endpoint_key: str
    test_cases_count: int
    request_ids: List[str] = Field(default_factory=list)
    status_codes_observed: List[int] = Field(default_factory=list)
    outcome: str  # VERIFIED, PARTIALLY_VERIFIED, INCONCLUSIVE, REJECTED, BLOCKED
    rationale: str
    failure_reason: Optional[str] = None


class GraphMutationTrace(BaseModel):
    """Audit log entry for an ApplicationGraph mutation."""
    mutation_id: str = Field(default_factory=lambda: f"mut-{uuid.uuid4().hex[:8]}")
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mutation_type: str  # NODE_ADDED, NODE_UPDATED, EDGE_ADDED, EDGE_REMOVED, CONFIDENCE_CHANGED
    target_id: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    reason: str
    source_observation_id: Optional[str] = None


class RetryTrace(BaseModel):
    """Audit log entry for an action retry or self-healing recovery."""
    retry_id: str = Field(default_factory=lambda: f"rty-{uuid.uuid4().hex[:8]}")
    session_id: str
    action_id: str
    retry_number: int
    previous_error: str
    recovery_strategy: str
    result_status: str


class StuckDetectionTrace(BaseModel):
    """Record of stuck or no-progress conditions detected during an investigation."""
    stuck_id: str = Field(default_factory=lambda: f"stk-{uuid.uuid4().hex[:8]}")
    session_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_stuck: bool
    stuck_reason: str
    repeated_action_types: List[str] = Field(default_factory=list)
    repeated_state_hashes: List[str] = Field(default_factory=list)
    steps_without_progress: int = 0
    suggested_recoveries: List[str] = Field(default_factory=list)


class MissingEndpointDiagnostic(BaseModel):
    """Diagnostic walking backward to identify why an expected endpoint was not found."""
    target_endpoint: str
    session_id: str
    status: str = "NOT_DISCOVERED"
    root_cause: RootCauseCategory = RootCauseCategory.UNKNOWN
    broken_link_stage: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    recommended_action: str


class AIDiagnosticReport(BaseModel):
    """Comprehensive 15-question AI-readable diagnostic summary report."""
    session_id: str
    target_url: str
    goal: str
    status: str
    duration_seconds: float
    total_actions: int
    successful_actions: int
    failed_actions: int
    retries_count: int
    pages_explored: List[str] = Field(default_factory=list)
    endpoints_discovered_count: int
    endpoints_verified_count: int
    unresolved_hypotheses_count: int
    unexplored_regions: List[str] = Field(default_factory=list)
    last_successful_progress: Optional[str] = None
    stopping_reason: str
    root_cause: RootCauseCategory
    root_cause_confidence: float
    root_cause_evidence: List[str] = Field(default_factory=list)
    recommended_next_experiment: str
