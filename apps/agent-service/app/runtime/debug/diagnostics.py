"""
runtime/debug/diagnostics.py — Automated Root-Cause & Missing-Endpoint Diagnostic Engine.

Performs automated failure classification, missing-endpoint walk-back diagnosis,
and AI-readable AI_DIAGNOSTIC.md report generation (Debug Prompt §31, §32, §33, §34, §42).
"""
from __future__ import annotations

import re
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

from app.runtime.debug.models import (
    AIDiagnosticReport,
    MissingEndpointDiagnostic,
    RootCauseCategory,
)
from app.runtime.world_model import ApplicationGraph


class RootCauseAnalyzer:
    """
    Classifies failure modes and sub-optimal runs into specific root cause categories.
    """

    @staticmethod
    def analyze(
        session_id: str,
        actions: List[Dict[str, Any]],
        errors: List[Dict[str, Any]],
        network_traces: List[Dict[str, Any]],
        discovered_count: int,
        verified_count: int,
        is_stuck: bool = False,
        stuck_reason: Optional[str] = None,
    ) -> Tuple[RootCauseCategory, float, List[str], str]:
        """
        Evaluates execution telemetry and returns (category, confidence, evidence_list, recommendation).
        """
        evidence: List[str] = []

        # ── 1. Policy / SSRF Denials ──────────────────────────────────────────
        policy_errors = [e for e in errors if "policy" in str(e).lower() or "guardrail" in str(e).lower() or "ssrf" in str(e).lower()]
        if policy_errors:
            evidence.append(f"{len(policy_errors)} policy/guardrail denial events intercepted.")
            return (
                RootCauseCategory.POLICY,
                0.95,
                evidence,
                "Verify target domain authorization scope and ensure target URL is not a private IP / SSRF restricted range.",
            )

        # ── 2. Authentication Failures ────────────────────────────────────────
        auth_errors = [e for e in errors if "401" in str(e) or "403" in str(e) or "auth" in str(e).lower() or "unauthorized" in str(e).lower()]
        auth_responses = [n for n in network_traces if n.get("response_status") in (401, 403)]
        if auth_errors or auth_responses:
            evidence.append(f"{len(auth_errors)} auth errors logged; {len(auth_responses)} 401/403 network responses captured.")
            return (
                RootCauseCategory.AUTHENTICATION,
                0.92,
                evidence,
                "Supply valid Bearer token, session cookie, or API credentials via auth_context.",
            )

        # ── 3. Browser Navigation Failures ────────────────────────────────────
        nav_errors = [e for e in errors if "navigation" in str(e).lower() or "timeout" in str(e).lower() or "net::err" in str(e).lower()]
        if nav_errors:
            evidence.append(f"{len(nav_errors)} browser navigation timeouts/connection errors.")
            return (
                RootCauseCategory.BROWSER_NAVIGATION,
                0.88,
                evidence,
                "Check target URL availability, DNS resolution, and increase navigation timeout.",
            )

        # ── 4. Browser Element / Interaction Failures ─────────────────────────
        interaction_errors = [e for e in errors if "click" in str(e).lower() or "selector" in str(e).lower() or "element" in str(e).lower()]
        if interaction_errors or (is_stuck and "dom" in (stuck_reason or "").lower()):
            evidence.append(f"{len(interaction_errors)} element interaction failures.")
            if is_stuck:
                evidence.append(f"Stuck state triggered: {stuck_reason}")
            return (
                RootCauseCategory.BROWSER_INTERACTION,
                0.85,
                evidence,
                "Inspect accessibility tree (AXTree) and update interactive element heuristics for overlays/modals.",
            )

        # ── 5. Zero Network Capture / Obfuscated Protocols ────────────────────
        if len(actions) > 0 and discovered_count == 0:
            evidence.append(f"Executed {len(actions)} actions across pages but captured 0 API network requests.")
            return (
                RootCauseCategory.NETWORK_CAPTURE,
                0.80,
                evidence,
                "Target may use embedded WebSockets, custom AJAX protocols, or static hydration. Verify network interceptor filters.",
            )

        # ── 6. Verification Discrepancies ─────────────────────────────────────
        if discovered_count > 0 and verified_count == 0:
            evidence.append(f"{discovered_count} endpoints discovered, but 0 successfully verified with replay evidence.")
            return (
                RootCauseCategory.VERIFICATION,
                0.82,
                evidence,
                "Endpoints may require CSRF tokens, dynamic query parameters, or stateful session cookies for replay.",
            )

        # ── 7. Normal Successful Run ──────────────────────────────────────────
        if discovered_count > 0 and verified_count > 0:
            evidence.append(f"Discovered {discovered_count} endpoints; successfully verified {verified_count} with multi-identifier evidence.")
            return (
                RootCauseCategory.UNKNOWN,
                0.95,
                evidence,
                "Investigation completed successfully.",
            )

        return (
            RootCauseCategory.UNKNOWN,
            0.50,
            ["No specific error signatures identified."],
            "Enable TRACE debug logging level for fine-grained execution capture.",
        )


class MissingEndpointAnalyzer:
    """
    Walks backward from an expected endpoint to diagnose why it was not discovered.
    """

    @staticmethod
    def analyze(
        target_endpoint: str,
        session_id: str,
        graph: ApplicationGraph,
        actions: List[Dict[str, Any]],
        network_traces: List[Dict[str, Any]],
    ) -> MissingEndpointDiagnostic:
        """
        Step-by-step 12-link walk-back diagnosis:
        Expected -> Network captured? -> Page visited? -> UI action executed? -> Normalization? -> Graph?
        """
        norm_target = target_endpoint.strip().lower()
        method_match = re.match(r"^(GET|POST|PUT|DELETE|PATCH)\s+(.*)$", norm_target, re.IGNORECASE)
        expected_method = method_match.group(1).upper() if method_match else "GET"
        expected_path = method_match.group(2) if method_match else norm_target

        # 1. Did the network layer intercept this URL?
        matched_network = []
        for n in network_traces:
            req_url = (n.get("url") or "").lower()
            req_tmpl = (n.get("normalized_template") or "").lower()
            if expected_path.lower() in req_url or expected_path.lower() in req_tmpl:
                matched_network.append(n)

        if not matched_network:
            # 2. Was the parent page visited?
            expected_page_hint = expected_path.split("/")[1] if "/" in expected_path.strip("/") else ""
            visited_pages = [a.get("target", "") for a in actions if a.get("action_type") == "navigate"]

            page_found = any(expected_page_hint in p.lower() for p in visited_pages if expected_page_hint)

            if not page_found:
                return MissingEndpointDiagnostic(
                    target_endpoint=target_endpoint,
                    session_id=session_id,
                    status="NOT_DISCOVERED",
                    root_cause=RootCauseCategory.BROWSER_NAVIGATION,
                    broken_link_stage="PAGE_NOT_VISITED",
                    evidence={
                        "expected_path": expected_path,
                        "visited_pages": visited_pages,
                        "network_requests_captured": len(network_traces),
                    },
                    recommended_action=f"Add navigation link to '{expected_path}' or increase exploration depth (max_pages).",
                )
            else:
                return MissingEndpointDiagnostic(
                    target_endpoint=target_endpoint,
                    session_id=session_id,
                    status="NOT_DISCOVERED",
                    root_cause=RootCauseCategory.BROWSER_INTERACTION,
                    broken_link_stage="UI_ACTION_NOT_TRIGGERED",
                    evidence={
                        "page_visited": True,
                        "network_traffic_captured": len(network_traces),
                        "actions_on_page": len(actions),
                    },
                    recommended_action="Relevant page was visited, but UI interactive controls (buttons, forms, tabs) triggering the API were not actuated.",
                )

        # 3. Network captured it — was it filtered or discarded in normalization?
        endpoints_in_graph = graph.get_endpoints()
        graph_matched = any(
            expected_path.lower() in ep.template_path.lower() and ep.method.upper() == expected_method
            for ep in endpoints_in_graph
        )

        if not graph_matched:
            return MissingEndpointDiagnostic(
                target_endpoint=target_endpoint,
                session_id=session_id,
                status="INTERCEPTED_BUT_NOT_INDEXED",
                root_cause=RootCauseCategory.API_NORMALIZATION,
                broken_link_stage="NORMALIZATION_OR_GRAPH_UPDATE",
                evidence={
                    "network_intercepted": True,
                    "sample_network_trace": matched_network[0],
                },
                recommended_action="Endpoint request was seen on the wire but rejected during route template normalization or deduplication.",
            )

        return MissingEndpointDiagnostic(
            target_endpoint=target_endpoint,
            session_id=session_id,
            status="DISCOVERED",
            root_cause=RootCauseCategory.UNKNOWN,
            broken_link_stage="NONE",
            evidence={"endpoint_in_graph": True, "matched_network": len(matched_network)},
            recommended_action="Endpoint is already present in the Application Graph.",
        )


def generate_ai_diagnostic_md(report: AIDiagnosticReport, timeline_events: List[str]) -> str:
    """
    Generates the human/AI-readable AI_DIAGNOSTIC.md report answering all 15 diagnostic questions.
    """
    lines = [
        f"# InsightAPI Autonomous Investigation — AI Diagnostic Report",
        f"",
        f"**Session ID**: `{report.session_id}`  ",
        f"**Target URL**: `{report.target_url}`  ",
        f"**Status**: `{report.status.upper()}` ({report.duration_seconds:.2f}s)  ",
        f"**Root Cause**: `{report.root_cause.value.upper()}` (Confidence: {report.root_cause_confidence * 100:.1f}%)  ",
        f"",
        f"---",
        f"",
        f"## 15-Point Autonomous Diagnostic Assessment",
        f"",
        f"1. **Original Goal**: {report.goal}",
        f"2. **Actions Attempted**: {report.total_actions} autonomous steps executed.",
        f"3. **Actions Succeeded**: {report.successful_actions} completed successfully.",
        f"4. **Actions Failed**: {report.failed_actions} failed.",
        f"5. **Bottlenecks / Slowdowns**: Total crawl elapsed in {report.duration_seconds:.2f}s across {len(report.pages_explored)} pages.",
        f"6. **Self-Healing Retries**: {report.retries_count} retries executed.",
        f"7. **Pages Explored**: {', '.join(report.pages_explored) if report.pages_explored else 'Landing page'}.",
        f"8. **Endpoints Discovered**: **{report.endpoints_discovered_count}** API routes indexed in Application Graph.",
        f"9. **Endpoints Verified**: **{report.endpoints_verified_count}** backed by replay/probe evidence.",
        f"10. **Unresolved Hypotheses**: {report.unresolved_hypotheses_count} behavioral hypotheses pending verification.",
        f"11. **Unexplored Application Regions**: {', '.join(report.unexplored_regions) if report.unexplored_regions else 'None identified within authorized scope'}.",
        f"12. **Last Successful Progress Point**: {report.last_successful_progress or 'Exploration initialized'}.",
        f"13. **Investigation Stopping Reason**: {report.stopping_reason}.",
        f"14. **Primary Root Cause**: `{report.root_cause.value}`.",
        f"15. **Recommended Next Experiment**: {report.recommended_next_experiment}",
        f"",
        f"---",
        f"",
        f"## Root Cause Evidence Breakdown",
        f"",
    ]

    for ev in report.root_cause_evidence:
        lines.append(f"- {ev}")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## Execution Timeline Highlights",
        f"",
        f"```text",
    ])

    for evt in timeline_events[:30]:
        lines.append(evt)

    lines.extend([
        f"```",
        f"",
    ])

    return "\n".join(lines)
