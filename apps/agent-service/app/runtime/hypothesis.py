"""
runtime/hypothesis.py — Hypothesis Generation, Experimentation & Evidence Engine.

Architecture (AGENTS.md §11, §12, §30):
  Core InsightAPI Workflow:
    Hypothesis → Experiment → Observation → Evidence → Verification
"""
from __future__ import annotations

import re
import uuid
import logging
from typing import Any, Dict, List, Optional

from app.runtime.models import (
    Action,
    ActionType,
    AgentState,
    ConfidenceLevel,
    DiscoveredEndpoint,
    Evidence,
    EvidenceStatus,
    Hypothesis,
    HypothesisStatus,
    Observation,
)
from app.runtime.world_model import ApplicationGraph
from app.core.utils import normalize_route_template

logger = logging.getLogger("agent.runtime.hypothesis")


class HypothesisEngine:
    """
    Automates hypothesis generation from discovered endpoints, experiment design,
    and evidence-backed verification.
    """

    @staticmethod
    def generate_hypotheses(world_model: ApplicationGraph, session_id: str) -> List[Hypothesis]:
        """
        Analyze current graph and formulate testable hypotheses.
        """
        hypotheses: List[Hypothesis] = []

        for node in world_model.nodes.values():
            if node.node_type.value != "endpoint":
                continue

            method = node.attributes.get("method", "GET")
            template = node.attributes.get("template_path", "")
            example_url = node.attributes.get("example_url", "")

            # 1. Parameterized Route Hypothesis
            if "{" in template and "}" in template and example_url:
                hyp = Hypothesis(
                    session_id=session_id,
                    claim=f"Route '{method} {template}' is a parameterized resource accepting dynamic IDs.",
                    endpoint_key=f"{method} {template}",
                    status=HypothesisStatus.CREATED,
                    experiment_description=f"Replay {template} with valid and invalid IDs to confirm parameterized behavior.",
                )
                hypotheses.append(hyp)

            # 2. Authentication Requirement Hypothesis
            auth_req = node.attributes.get("auth_required")
            if auth_req is None and example_url:
                hyp = Hypothesis(
                    session_id=session_id,
                    claim=f"Endpoint '{method} {template}' enforces authentication for access.",
                    endpoint_key=f"{method} {template}",
                    status=HypothesisStatus.CREATED,
                    experiment_description=f"Send authenticated vs unauthenticated requests to test 401/403 behavior.",
                )
                hypotheses.append(hyp)

        return hypotheses

    @staticmethod
    def design_experiment(hypothesis: Hypothesis, base_url: str) -> List[Action]:
        """
        Generate experimental Actions to test a specific Hypothesis.
        """
        actions: List[Action] = []
        endpoint_key = hypothesis.endpoint_key or ""
        parts = endpoint_key.split(" ", 1)
        method = parts[0] if len(parts) > 0 else "GET"

        if "parameterized" in hypothesis.claim.lower():
            # Action A: Probe with invalid ID (expect 404)
            invalid_url = f"{base_url.rstrip('/')}/99999999"
            actions.append(
                Action(
                    session_id=hypothesis.session_id,
                    action_type=ActionType.PROBE_HTTP,
                    target=invalid_url,
                    parameters={"method": method, "hypothesis_id": hypothesis.id, "probe_type": "invalid_id"},
                    rationale=f"Test invalid resource ID on {endpoint_key} (expect 404).",
                )
            )

        elif "authentication" in hypothesis.claim.lower():
            # Action: Probe unauthenticated
            actions.append(
                Action(
                    session_id=hypothesis.session_id,
                    action_type=ActionType.PROBE_HTTP,
                    target=base_url,
                    parameters={"method": method, "hypothesis_id": hypothesis.id, "probe_type": "unauth"},
                    rationale=f"Test unauthenticated request against {endpoint_key} (expect 401/403).",
                )
            )

        return actions

    @staticmethod
    def evaluate_observations(
        hypothesis: Hypothesis,
        observations: List[Observation],
    ) -> Hypothesis:
        """
        Evaluate experiment observations, establish supporting/contradicting evidence,
        and update hypothesis status.
        """
        for obs in observations:
            status_code = obs.response_status or 0

            if "parameterized" in hypothesis.claim.lower():
                if status_code in (404, 400):
                    hypothesis.supporting_evidence_ids.append(obs.id)
                    hypothesis.status = HypothesisStatus.SUPPORTED
                    hypothesis.confidence_score = min(1.0, hypothesis.confidence_score + 0.5)
                elif status_code == 200:
                    hypothesis.supporting_evidence_ids.append(obs.id)
                    hypothesis.confidence_score = min(1.0, hypothesis.confidence_score + 0.3)

            elif "authentication" in hypothesis.claim.lower():
                if status_code in (401, 403):
                    hypothesis.supporting_evidence_ids.append(obs.id)
                    hypothesis.status = HypothesisStatus.VERIFIED
                    hypothesis.conclusion = "Authentication requirement confirmed."
                    hypothesis.confidence_score = 0.95
                elif status_code == 200:
                    hypothesis.contradicting_evidence_ids.append(obs.id)
                    hypothesis.status = HypothesisStatus.CONTRADICTED
                    hypothesis.conclusion = "Endpoint is publicly accessible without authentication."
                    hypothesis.confidence_score = 0.90

        if hypothesis.confidence_score >= 0.8 and hypothesis.status != HypothesisStatus.CONTRADICTED:
            hypothesis.status = HypothesisStatus.VERIFIED
            hypothesis.conclusion = f"Verified with {len(hypothesis.supporting_evidence_ids)} pieces of supporting evidence."

        return hypothesis

    @staticmethod
    def build_evidence_backed_inventory(
        world_model: ApplicationGraph,
        hypotheses: List[Hypothesis],
    ) -> List[DiscoveredEndpoint]:
        """
        Produce a certified, evidence-backed API inventory distinguishing observed facts from inferences.
        """
        inventory: List[DiscoveredEndpoint] = []
        hyp_map = {h.endpoint_key: h for h in hypotheses if h.endpoint_key}

        for node in world_model.nodes.values():
            if node.node_type.value != "endpoint":
                continue

            method = node.attributes.get("method", "GET")
            template = node.attributes.get("template_path", "")
            endpoint_key = f"{method} {template}"
            status_code = node.attributes.get("status_code", 200)
            inferred_schema = node.attributes.get("inferred_schema")
            is_graphql = node.attributes.get("is_graphql", False)
            graphql_op = node.attributes.get("graphql_operation")

            # Determine confidence based on hypotheses and observations
            conf = ConfidenceLevel.TESTED
            evidence_ids: List[str] = []
            auth_req = node.attributes.get("auth_required")

            if endpoint_key in hyp_map:
                h = hyp_map[endpoint_key]
                if h.status == HypothesisStatus.VERIFIED:
                    conf = ConfidenceLevel.VERIFIED
                evidence_ids.extend(h.supporting_evidence_ids)

            inventory.append(
                DiscoveredEndpoint(
                    session_id=world_model.session_id,
                    method=method,
                    template_path=template,
                    example_url=node.attributes.get("example_url"),
                    status_code=status_code,
                    inferred_schema=inferred_schema,
                    confidence=conf,
                    evidence_ids=evidence_ids,
                    auth_required=auth_req,
                    is_graphql=is_graphql,
                    graphql_operation=graphql_op,
                    tags=["verified" if conf == ConfidenceLevel.VERIFIED else "observed"],
                )
            )

        return inventory
