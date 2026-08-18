"""
runtime/models.py — Canonical Typed Models for the InsightAPI Agent Runtime

This module defines the authoritative typed data model for the entire
autonomous agent runtime. Every agent, tool, service, and event handler
should import from here instead of defining local ad-hoc dicts.

Design references (AGENTS.md):
  §9  — Observations must become first-class data
  §10 — Agent State canonical structure
  §11 — Evidence is more important than LLM confidence
  §12 — Hypothesis → Experiment → Evidence lifecycle
  §22 — Policy and safety (RiskLevel, PolicyDecision)
  §31 — Artifacts as product outputs

Phase 1 contract:
  - All models are PURE Pydantic v2 dataclasses.
  - Zero database dependencies in this module.
  - Existing tools continue returning ToolResult; use ToolResult.to_observation()
    to convert into an Observation when feeding the runtime.
  - No behavior change to any existing code path.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class ActionType(str, Enum):
    """
    Every action an agent may request.

    Browser actions: NAVIGATE → CLICK → FILL → SUBMIT → SCROLL → WAIT
    Network actions: PROBE_HTTP → REPLAY_REQUEST → INSPECT_GRAPHQL → INSPECT_WEBSOCKET
    Analysis actions: INSPECT_SCHEMA → INSPECT_ACCESSIBILITY_TREE
    Reasoning actions: CREATE_HYPOTHESIS → VERIFY_ENDPOINT
    Orchestration: DELEGATE_TASK → FINISH
    """
    # Browser
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SUBMIT = "submit"
    OPEN_MODAL = "open_modal"
    CHANGE_FILTER = "change_filter"
    SCROLL = "scroll"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    # Network
    PROBE_HTTP = "probe_http"
    EXECUTE_CURL = "execute_curl"
    REPLAY_REQUEST = "replay_request"
    INSPECT_GRAPHQL = "inspect_graphql"
    INSPECT_WEBSOCKET = "inspect_websocket"
    INSPECT_SSE = "inspect_sse"
    PARSE_HAR = "parse_har"
    # Analysis
    INSPECT_SCHEMA = "inspect_schema"
    INSPECT_ACCESSIBILITY_TREE = "inspect_accessibility_tree"
    SECURITY_AUDIT = "security_audit"
    # Reasoning
    CREATE_HYPOTHESIS = "create_hypothesis"
    VERIFY_ENDPOINT = "verify_endpoint"
    REFLECT = "reflect"
    # Orchestration
    DELEGATE_TASK = "delegate_task"
    FINISH = "finish"
    WAIT_FOR_APPROVAL = "wait_for_approval"


class ConfidenceLevel(str, Enum):
    """
    Evidence-based confidence for a discovered endpoint or claim.

    Hierarchy (AGENTS.md §11):
      UNOBSERVED → INFERRED → WEAK → PROBABLE → TESTED → VERIFIED → STRONGLY_VERIFIED
    """
    UNOBSERVED = "unobserved"
    INFERRED = "inferred"
    WEAK = "weak"
    PROBABLE = "probable"
    TESTED = "tested"
    VERIFIED = "verified"
    STRONGLY_VERIFIED = "strongly_verified"


class EvidenceStatus(str, Enum):
    """
    Observation/evidence lifecycle — mirrors AGENTS.md §11.
    """
    UNOBSERVED = "unobserved"
    INFERRED = "inferred"
    TESTED = "tested"
    VERIFIED = "verified"
    STRONGLY_VERIFIED = "strongly_verified"


class HypothesisStatus(str, Enum):
    """
    Hypothesis lifecycle — AGENTS.md §12.
    """
    CREATED = "created"
    TESTING = "testing"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    ABANDONED = "abandoned"
    VERIFIED = "verified"


class AgentEventType(str, Enum):
    """
    Structured execution event types — AGENTS.md §27.
    """
    SESSION_STARTED = "session_started"
    PLAN_CREATED = "plan_created"
    ACTION_REQUESTED = "action_requested"
    POLICY_CHECK = "policy_check"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"
    OBSERVATION_CREATED = "observation_created"
    HYPOTHESIS_CREATED = "hypothesis_created"
    HYPOTHESIS_TESTED = "hypothesis_tested"
    ENDPOINT_DISCOVERED = "endpoint_discovered"
    ENDPOINT_VERIFIED = "endpoint_verified"
    SUBAGENT_STARTED = "subagent_started"
    SUBAGENT_COMPLETED = "subagent_completed"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RECEIVED = "approval_received"
    VERIFICATION_STARTED = "verification_started"
    VERIFICATION_COMPLETED = "verification_completed"
    ARTIFACT_CREATED = "artifact_created"
    BUDGET_WARNING = "budget_warning"
    SESSION_COMPLETED = "session_completed"
    SESSION_FAILED = "session_failed"
    # Emitted as token stream chunks to the UI
    LLM_TOKEN = "token"


class ObservationSource(str, Enum):
    """
    Source system that produced an Observation — AGENTS.md §9.
    """
    BROWSER = "browser"
    NETWORK = "network"
    HTTP = "http"
    GRAPHQL = "graphql"
    WEBSOCKET = "websocket"
    SSE = "sse"
    AUTHENTICATION = "authentication"
    SCHEMA = "schema"
    SECURITY = "security"
    SYSTEM = "system"
    PLANNER = "planner"
    VERIFICATION = "verification"


class RiskLevel(str, Enum):
    """
    Action risk classification — AGENTS.md §22.
    Policy uses this to route through the approval gate.
    """
    READ_ONLY = "read_only"
    LOW_RISK = "low_risk"
    MODIFYING = "modifying"
    DESTRUCTIVE = "destructive"
    AUTH_SENSITIVE = "auth_sensitive"
    SECURITY_TEST = "security_test"


class PolicyDecision(str, Enum):
    """
    Output of the policy layer for a requested Action — AGENTS.md §22.
    """
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    DEFER = "defer"


class FailureClass(str, Enum):
    """
    Structured failure classification for self-healing — AGENTS.md §24.
    """
    TRANSIENT = "transient"
    AUTHENTICATION = "authentication"
    SCOPE = "scope"
    POLICY = "policy"
    TIMEOUT = "timeout"
    NETWORK = "network"
    BROWSER = "browser"
    VALIDATION = "validation"
    MODEL = "model"
    TOOL = "tool"
    UNKNOWN = "unknown"


class ArtifactType(str, Enum):
    """Output artifact classification — AGENTS.md §31."""
    API_INVENTORY = "api_inventory"
    OPENAPI_SPEC = "openapi_spec"
    POSTMAN_COLLECTION = "postman_collection"
    MARKDOWN_DOCS = "markdown_docs"
    REGRESSION_TESTS = "regression_tests"
    DISCOVERY_REPORT = "discovery_report"
    EVIDENCE_REPORT = "evidence_report"
    APPLICATION_GRAPH = "application_graph"
    SECURITY_FINDINGS = "security_findings"
    DRIFT_REPORT = "drift_report"


# ═══════════════════════════════════════════════════════════════════════════════
# GOAL
# ═══════════════════════════════════════════════════════════════════════════════

class Goal(BaseModel):
    """
    The top-level investigation goal.

    A Goal is created once per session and drives the Supervisor's planning loop.
    The Supervisor is done when completion_criteria are satisfied or budget is exhausted.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    target_url: str
    session_id: str
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    # Scope constraints (AGENTS.md §23)
    allowed_domains: List[str] = Field(default_factory=list)
    max_pages: int = 50
    max_requests: int = 200
    max_runtime_seconds: int = 600
    # Human-readable completion criteria
    completion_criteria: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════
# BUDGET
# ═══════════════════════════════════════════════════════════════════════════════

class AgentBudget(BaseModel):
    """
    Tracks resource consumption against hard limits — AGENTS.md §29.

    All fields are mutable counters. The Planner reads remaining_* values
    to decide whether to continue or trigger a FINISH action.
    """
    # Limits
    max_tool_calls: int = 100
    max_model_calls: int = 30
    max_tokens: int = 500_000
    max_browser_actions: int = 50
    max_http_requests: int = 100
    max_retries: int = 10
    max_runtime_seconds: int = 600
    # Consumed
    tool_calls_used: int = 0
    model_calls_used: int = 0
    tokens_used: int = 0
    browser_actions_used: int = 0
    http_requests_used: int = 0
    retries_used: int = 0
    # Derived
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_exhausted(self) -> bool:
        """Returns True if any hard limit has been reached."""
        return (
            self.tool_calls_used >= self.max_tool_calls
            or self.model_calls_used >= self.max_model_calls
            or self.tokens_used >= self.max_tokens
            or self.browser_actions_used >= self.max_browser_actions
            or self.http_requests_used >= self.max_http_requests
        )

    @property
    def elapsed_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.started_at).total_seconds()

    @property
    def is_timed_out(self) -> bool:
        return self.elapsed_seconds >= self.max_runtime_seconds


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT STATE
# ═══════════════════════════════════════════════════════════════════════════════

class AgentState(BaseModel):
    """
    Canonical agent state — AGENTS.md §10.

    This is the authoritative working memory for the Supervisor and all agents.
    It is serialized to Redis + DB on each planning step (Phase 8).

    Design note: Large raw payloads (response bodies, HTML) are stored by reference
    (observation IDs) — NOT inlined here. Keep this model lean.
    """
    # Identity
    session_id: str
    goal: Goal
    budget: AgentBudget = Field(default_factory=AgentBudget)

    # Navigation state
    current_url: Optional[str] = None
    current_page_title: Optional[str] = None
    visited_urls: List[str] = Field(default_factory=list)
    visited_state_hashes: List[str] = Field(default_factory=list)

    # Authentication
    is_authenticated: bool = False
    auth_type: Optional[str] = None  # bearer|jwt|api_key|cookie|basic|oauth|anonymous
    auth_context: Dict[str, Any] = Field(default_factory=dict)

    # Discovery (IDs/references only — full data in DB)
    discovered_endpoint_ids: List[str] = Field(default_factory=list)
    discovered_entity_ids: List[str] = Field(default_factory=list)
    open_hypothesis_ids: List[str] = Field(default_factory=list)
    verified_endpoint_ids: List[str] = Field(default_factory=list)

    # Task tracking
    completed_task_ids: List[str] = Field(default_factory=list)
    failed_task_ids: List[str] = Field(default_factory=list)
    blocked_task_ids: List[str] = Field(default_factory=list)

    # Action history (last N actions, not full history)
    recent_actions: List[Dict[str, Any]] = Field(default_factory=list)
    failed_actions: List[Dict[str, Any]] = Field(default_factory=list)

    # Open questions the agent cannot yet answer
    open_questions: List[str] = Field(default_factory=list)

    # Pending human approvals
    pending_approval_ids: List[str] = Field(default_factory=list)

    # Current plan (list of planned actions)
    current_plan: List[Dict[str, Any]] = Field(default_factory=list)

    # Artifacts produced this session
    artifact_ids: List[str] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        """Update the updated_at timestamp. Call after every state mutation."""
        self.updated_at = datetime.now(timezone.utc)

    def record_url_visited(self, url: str) -> None:
        if url not in self.visited_urls:
            self.visited_urls.append(url)
        self.current_url = url
        self.touch()

    def add_recent_action(self, action: "Action") -> None:
        """Keep the last 50 actions in hot state."""
        self.recent_actions.append(action.model_dump())
        if len(self.recent_actions) > 50:
            self.recent_actions = self.recent_actions[-50:]
        self.touch()


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION
# ═══════════════════════════════════════════════════════════════════════════════

class Action(BaseModel):
    """
    A single agent action request.

    The Planner produces Actions; the Policy layer approves/denies them;
    the appropriate agent/tool executes them.
    """
    id: str = Field(default_factory=lambda: f"act-{uuid.uuid4().hex[:12]}")
    session_id: str
    agent_id: Optional[str] = None
    action_type: ActionType
    target: Optional[str] = None        # URL, selector, or endpoint key
    parameters: Dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.READ_ONLY
    rationale: Optional[str] = None     # why the planner chose this action
    requires_approval: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════
# OBSERVATION
# ═══════════════════════════════════════════════════════════════════════════════

class Observation(BaseModel):
    """
    Normalized observation — AGENTS.md §9.

    Every tool result, browser event, and network event is converted into
    an Observation before being stored or reasoned over. This ensures all
    agents share a common evidence vocabulary.
    """
    id: str = Field(default_factory=lambda: f"obs-{uuid.uuid4().hex[:12]}")
    session_id: str
    source: ObservationSource
    action_id: Optional[str] = None     # the Action that produced this observation
    # Page / browser context
    page_url: Optional[str] = None
    page_title: Optional[str] = None
    # Network observation fields
    request_method: Optional[str] = None
    request_url: Optional[str] = None
    request_template: Optional[str] = None
    request_headers: Dict[str, str] = Field(default_factory=dict)
    request_body: Optional[Any] = None
    response_status: Optional[int] = None
    response_headers: Dict[str, str] = Field(default_factory=dict)
    response_body: Optional[Any] = None
    # Schema
    inferred_schema: Optional[Dict[str, Any]] = None
    # Evidence / quality
    confidence: ConfidenceLevel = ConfidenceLevel.INFERRED
    latency_ms: int = 0
    error: Optional[str] = None
    # Metadata
    raw_tool_result: Optional[Dict[str, Any]] = None  # original ToolResult.to_dict()
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════
# EVIDENCE
# ═══════════════════════════════════════════════════════════════════════════════

class Evidence(BaseModel):
    """
    A single piece of evidence supporting or contradicting an endpoint claim.

    Evidence links an Observation to an endpoint or hypothesis — AGENTS.md §11.
    """
    id: str = Field(default_factory=lambda: f"ev-{uuid.uuid4().hex[:12]}")
    session_id: str
    observation_id: str
    endpoint_key: Optional[str] = None     # "GET /api/users/{id}"
    hypothesis_id: Optional[str] = None
    status: EvidenceStatus = EvidenceStatus.INFERRED
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════
# HYPOTHESIS
# ═══════════════════════════════════════════════════════════════════════════════

class Hypothesis(BaseModel):
    """
    A testable claim about the target application — AGENTS.md §12.

    Example::
        Hypothesis:
          /api/products/{id} is a parameterized resource route.
        Experiment:
          Replay route with multiple observed IDs.
        Evidence:
          123 → 200, 124 → 200, invalid → 404
        Conclusion:
          Verified.
    """
    id: str = Field(default_factory=lambda: f"hyp-{uuid.uuid4().hex[:12]}")
    session_id: str
    claim: str                             # human-readable hypothesis statement
    endpoint_key: Optional[str] = None     # related endpoint if applicable
    status: HypothesisStatus = HypothesisStatus.CREATED
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradicting_evidence_ids: List[str] = Field(default_factory=list)
    experiment_description: Optional[str] = None
    conclusion: Optional[str] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def update_status(self, new_status: HypothesisStatus) -> None:
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT EVENT
# ═══════════════════════════════════════════════════════════════════════════════

class AgentEvent(BaseModel):
    """
    A structured runtime event emitted by any agent, tool, or service.

    AgentEvents flow through AgentEventBus. They drive:
    - UI streaming (LLM_TOKEN, TOOL_STARTED, ENDPOINT_DISCOVERED, …)
    - Observability / audit trail
    - Replay and debugging

    This is the typed replacement for the raw ``{type: "tool_start", …}``
    dicts currently yielded by ReActEngine. The event_bridge module
    (Phase 2) converts between the two formats for backward compatibility.
    """
    id: str = Field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:12]}")
    session_id: str
    event_type: AgentEventType
    agent_id: Optional[str] = None
    tool_id: Optional[str] = None
    action_id: Optional[str] = None
    observation_id: Optional[str] = None
    hypothesis_id: Optional[str] = None
    # Payload — keep small; reference large data by ID
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_wire(self) -> Dict[str, Any]:
        """
        Serializes to the wire format expected by the WebSocket client.
        Maintains backward compatibility with the raw dict format.
        """
        payload = {
            "type": self.event_type.value,
            "event_id": self.id,
            "session_id": self.session_id,
        }
        if self.tool_id:
            payload["tool_id"] = self.tool_id
        if self.agent_id:
            payload["agent_id"] = self.agent_id
        payload.update(self.data)
        if self.error:
            payload["error"] = self.error
        return payload


# ═══════════════════════════════════════════════════════════════════════════════
# POLICY
# ═══════════════════════════════════════════════════════════════════════════════

class PolicyResult(BaseModel):
    """
    Result from the Policy layer for a requested Action — AGENTS.md §22.

    The Policy layer is responsible for all ALLOW/DENY decisions.
    The LLM is NEVER the final authority on dangerous actions.
    """
    action_id: str
    decision: PolicyDecision
    risk_level: RiskLevel
    reason: str
    requires_approval_id: Optional[str] = None  # set when decision == REQUIRE_APPROVAL
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICATION RESULT
# ═══════════════════════════════════════════════════════════════════════════════

class VerificationResult(BaseModel):
    """
    Result from the VerificationAgent replaying an endpoint — AGENTS.md §30.
    """
    id: str = Field(default_factory=lambda: f"vr-{uuid.uuid4().hex[:12]}")
    session_id: str
    endpoint_key: str
    confidence: ConfidenceLevel
    evidence_ids: List[str] = Field(default_factory=list)
    # Replay summary
    successful_replays: int = 0
    failed_replays: int = 0
    status_codes_observed: List[int] = Field(default_factory=list)
    auth_required: Optional[bool] = None
    schema_consistent: Optional[bool] = None
    notes: Optional[str] = None
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════
# DISCOVERED ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

class DiscoveredEndpoint(BaseModel):
    """
    Normalized representation of a discovered API endpoint.

    This is the typed version of the raw endpoint dicts currently used
    throughout the system. Migrate callsites incrementally; both forms
    remain valid during the transition.
    """
    id: str = Field(default_factory=lambda: f"ep-{uuid.uuid4().hex[:12]}")
    session_id: str
    method: str                             # "GET", "POST", …
    template_path: str                      # "/api/users/{id}"
    example_url: Optional[str] = None       # "/api/users/123"
    status_code: Optional[int] = None
    request_body: Optional[Any] = None
    response_body: Optional[Any] = None
    inferred_schema: Optional[Dict[str, Any]] = None
    confidence: ConfidenceLevel = ConfidenceLevel.INFERRED
    evidence_ids: List[str] = Field(default_factory=list)
    auth_required: Optional[bool] = None
    is_graphql: bool = False
    graphql_operation: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def endpoint_key(self) -> str:
        return f"{self.method.upper()} {self.template_path}"


# ═══════════════════════════════════════════════════════════════════════════════
# ARTIFACT
# ═══════════════════════════════════════════════════════════════════════════════

class Artifact(BaseModel):
    """
    A product output artifact — AGENTS.md §31.

    Artifacts reference evidence. Whenever practical they link back to
    the observation IDs that support their content.
    """
    id: str = Field(default_factory=lambda: f"art-{uuid.uuid4().hex[:12]}")
    session_id: str
    artifact_type: ArtifactType
    title: str
    content: Optional[Any] = None           # JSON / string payload
    file_path: Optional[str] = None         # path on disk if written to file
    evidence_ids: List[str] = Field(default_factory=list)
    endpoint_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
