"""
runtime/debug — InsightAPI Advanced Agent Debug & Observability Runtime.

Authoritative package exposing hierarchical tracing, centralized secret redaction,
correlation graphs, stuck detection, root-cause diagnosis, and debug file recorders.
"""
from app.runtime.debug.models import (
    ActionState,
    ActionTrace,
    AIDiagnosticReport,
    BrowserActionTrace,
    CandidateActionScore,
    DebugLevel,
    DebugSession,
    GraphMutationTrace,
    HypothesisTrace,
    MissingEndpointDiagnostic,
    ModelTrace,
    NetworkFailureType,
    NetworkTrace,
    PlannerDecisionTrace,
    PolicyEvaluationTrace,
    RetryTrace,
    RootCauseCategory,
    SpanStatus,
    SpanType,
    StuckDetectionTrace,
    TraceSpan,
    VerificationTrace,
)
from app.runtime.debug.redaction import (
    REDACTED_STR,
    redact_headers,
    redact_string,
    redact_url,
    sanitize_data,
)
from app.runtime.debug.correlation import correlator, CorrelationRegistry, CorrelationRecord
from app.runtime.debug.tracer import tracer, Tracer
from app.runtime.debug.stuck_detector import stuck_detector, StuckDetector
from app.runtime.debug.profiler import profiler, Profiler, InvestigationProfile
from app.runtime.debug.diagnostics import (
    RootCauseAnalyzer,
    MissingEndpointAnalyzer,
    generate_ai_diagnostic_md,
)
from app.runtime.debug.recorder import recorder, DebugRecorder
from app.runtime.debug.exporter import DebugExporter

__all__ = [
    "DebugLevel",
    "SpanType",
    "SpanStatus",
    "ActionState",
    "NetworkFailureType",
    "RootCauseCategory",
    "TraceSpan",
    "DebugSession",
    "CandidateActionScore",
    "PlannerDecisionTrace",
    "ActionTrace",
    "BrowserActionTrace",
    "NetworkTrace",
    "ModelTrace",
    "PolicyEvaluationTrace",
    "HypothesisTrace",
    "VerificationTrace",
    "GraphMutationTrace",
    "RetryTrace",
    "StuckDetectionTrace",
    "MissingEndpointDiagnostic",
    "AIDiagnosticReport",
    "REDACTED_STR",
    "redact_string",
    "redact_url",
    "redact_headers",
    "sanitize_data",
    "correlator",
    "CorrelationRegistry",
    "CorrelationRecord",
    "tracer",
    "Tracer",
    "stuck_detector",
    "StuckDetector",
    "profiler",
    "Profiler",
    "InvestigationProfile",
    "RootCauseAnalyzer",
    "MissingEndpointAnalyzer",
    "generate_ai_diagnostic_md",
    "recorder",
    "DebugRecorder",
    "DebugExporter",
]
