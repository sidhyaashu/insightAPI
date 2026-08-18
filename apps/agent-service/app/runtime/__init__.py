"""
runtime/__init__.py — InsightAPI Autonomous Agent Runtime

Exports the canonical typed models and event bus used by all agents,
tools, and services in the InsightAPI runtime.

Architecture context (AGENTS.md §7):
  Goal → State → World Model → Hypotheses → Planner → Action →
  Observation → Evidence → Reflection → Verification → Memory → Next Action

Import pattern:
    from app.runtime import AgentState, Observation, AgentEventBus
    from app.runtime.models import ActionType, ConfidenceLevel, HypothesisStatus
"""
from app.runtime.models import (
    # Enumerations
    ActionType,
    ConfidenceLevel,
    EvidenceStatus,
    HypothesisStatus,
    AgentEventType,
    ObservationSource,
    RiskLevel,
    PolicyDecision,
    FailureClass,
    # Core domain models
    Goal,
    AgentBudget,
    AgentState,
    Action,
    Observation,
    Evidence,
    Hypothesis,
    AgentEvent,
    PolicyResult,
    VerificationResult,
    DiscoveredEndpoint,
    Artifact,
)
from app.runtime.events import AgentEventBus, event_bus
from app.runtime.event_bridge import (
    publish_raw,
    raw_dict_to_agent_event,
    agent_event_to_wire,
)
from app.runtime.policy import PolicyEngine
from app.runtime.hypothesis import HypothesisEngine
from app.runtime.world_model import (
    ApplicationGraph,
    GraphNode,
    GraphEdge,
    NodeType,
    RelationType,
)
from app.runtime.agents import (
    BaseAgent,
    AgentTask,
    AgentResult,
    ExplorerAgent,
    NetworkAgent,
    VerificationAgent,
)
from app.runtime.persistence import AgentStateStore, state_store
from app.runtime.observability import SessionTelemetryTracker, SessionMetrics, telemetry
from app.runtime.artifacts import ArtifactGenerator
from app.runtime.supervisor import Supervisor

__all__ = [
    # Enumerations
    "ActionType",
    "ConfidenceLevel",
    "EvidenceStatus",
    "HypothesisStatus",
    "AgentEventType",
    "ObservationSource",
    "RiskLevel",
    "PolicyDecision",
    "FailureClass",
    "NodeType",
    "RelationType",
    # Domain models
    "Goal",
    "AgentBudget",
    "AgentState",
    "Action",
    "Observation",
    "Evidence",
    "Hypothesis",
    "AgentEvent",
    "PolicyResult",
    "VerificationResult",
    "DiscoveredEndpoint",
    "Artifact",
    # World Model Graph
    "ApplicationGraph",
    "GraphNode",
    "GraphEdge",
    # Policy & Hypothesis Engines
    "PolicyEngine",
    "HypothesisEngine",
    # Persistence & Observability
    "AgentStateStore",
    "state_store",
    "SessionTelemetryTracker",
    "SessionMetrics",
    "telemetry",
    # Artifacts Generator
    "ArtifactGenerator",
    # Specialized Agents & Supervisor
    "BaseAgent",
    "AgentTask",
    "AgentResult",
    "ExplorerAgent",
    "NetworkAgent",
    "VerificationAgent",
    "Supervisor",
    # Event bus & bridge
    "AgentEventBus",
    "event_bus",
    "publish_raw",
    "raw_dict_to_agent_event",
    "agent_event_to_wire",
]
