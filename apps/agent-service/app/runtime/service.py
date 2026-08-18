"""
runtime/service.py — Unified InvestigationRuntime Service Entrypoint.

Architecture (AGENTS.md §7, §25, §26, §31):
  The single authoritative service entrypoint for autonomous investigations.
  Used identically by:
    - FastAPI HTTP Endpoints
    - WebSocket Agentic Chat
    - CLI & Automated Tasks
    - Background Workers
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.models import (
    Action,
    ActionType,
    AgentBudget,
    AgentEvent,
    AgentEventType,
    AgentState,
    ConfidenceLevel,
    DiscoveredEndpoint,
    Goal,
    Hypothesis,
    Observation,
    PolicyDecision,
    RiskLevel,
)
from app.runtime.world_model import ApplicationGraph
from app.runtime.policy import PolicyEngine
from app.runtime.hypothesis import HypothesisEngine
from app.runtime.persistence import AgentStateStore, state_store
from app.runtime.artifacts import ArtifactGenerator
from app.runtime.observability import SessionMetrics, telemetry
from app.runtime.events import event_bus
from app.runtime.supervisor import Supervisor
from app.core.utils import extract_urls

logger = logging.getLogger("agent.runtime.service")


class InvestigationRequest(BaseModel):
    """Normalized configuration payload for starting or resuming an investigation."""
    session_id: str = Field(default_factory=lambda: f"sess-{uuid.uuid4().hex[:12]}")
    user_id: str = "default-user"
    user_tier: str = "FREE"
    target_url: str
    goal_description: str = "Discover undocumented APIs, routes, and relationships in the target application."
    allowed_domains: List[str] = Field(default_factory=list)
    auth_headers: Dict[str, str] = Field(default_factory=dict)
    auth_profile_id: Optional[str] = None
    model: Optional[str] = None
    approved_actions: List[str] = Field(default_factory=list)
    max_pages: int = 10
    max_tool_calls: int = 50
    max_runtime_seconds: int = 600
    crawl_context: Optional[str] = None


class InvestigationRuntime:
    """
    Authoritative service coordinator for autonomous API investigations.
    """

    def __init__(self, store: Optional[AgentStateStore] = None) -> None:
        self.store = store or state_store

    async def initialize_state(self, request: InvestigationRequest, db: Optional[AsyncSession] = None) -> AgentState:
        """
        Create a new AgentState or load an existing one from persistent storage.
        """
        existing = await self.store.load_state(request.session_id, db=db)
        if existing:
            if request.allowed_domains and not existing.goal.allowed_domains:
                existing.goal.allowed_domains = request.allowed_domains
            return existing

        # Infer allowed domains from target URL if not provided
        domains = list(request.allowed_domains)
        if not domains and request.target_url:
            from urllib.parse import urlparse
            parsed = urlparse(request.target_url)
            if parsed.hostname:
                domains.append(parsed.hostname)

        goal = Goal(
            description=request.goal_description,
            target_url=request.target_url,
            allowed_domains=domains,
            session_id=request.session_id,
            max_pages=request.max_pages,
            max_runtime_seconds=request.max_runtime_seconds,
        )

        budget = AgentBudget(
            max_tool_calls=request.max_tool_calls,
            max_browser_actions=request.max_pages * 5,
            max_runtime_seconds=request.max_runtime_seconds,
        )

        state = AgentState(
            session_id=request.session_id,
            goal=goal,
            current_url=request.target_url,
            budget=budget,
            auth_context=request.auth_headers,
        )

        await self.store.save_state(state, db=db)
        return state

    async def start_investigation(
        self,
        request: InvestigationRequest,
        db: Optional[AsyncSession] = None,
    ) -> AgentState:
        """
        Run an autonomous investigation synchronously to completion and return final AgentState.
        """
        session_id = request.session_id
        state = await self.initialize_state(request, db=db)

        world_model = await self.store.load_world_model(session_id, db=db)
        if not world_model:
            world_model = ApplicationGraph(session_id=session_id)

        supervisor = Supervisor(state=state, world_model=world_model, approved_actions=request.approved_actions)

        # Run canonical supervisor loop
        async for _ in supervisor.run(max_iterations=request.max_pages):
            pass

        # Formulate and test hypotheses
        hyps = HypothesisEngine.generate_hypotheses(world_model, session_id=session_id)
        for h in hyps[:5]:
            experiments = HypothesisEngine.design_experiment(h, request.target_url)
            exp_observations = []
            for exp_action in experiments:
                exp_obs = await supervisor.verifier.verify_endpoint(
                    method=exp_action.parameters.get("method", "GET"),
                    url=exp_action.target,
                    auth_headers=state.auth_context,
                )
                exp_observations.append(exp_obs)
                world_model.record_observation(exp_obs)
            HypothesisEngine.evaluate_observations(h, exp_observations)

        # Build inventory and save durable state
        inventory = HypothesisEngine.build_evidence_backed_inventory(world_model, hyps)
        await self.store.save_world_model(world_model, db=db)
        await self.store.save_hypotheses(session_id, hyps, db=db)
        await self.store.save_state(state, db=db)

        return state

    async def stream_investigation(
        self,
        request: InvestigationRequest,
        history: Optional[List[Dict[str, Any]]] = None,
        db: Optional[AsyncSession] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute an autonomous investigation and stream real-time events to clients.
        Maintains complete backward compatibility with the WebSocket wire protocol.
        """
        session_id = request.session_id
        state = await self.initialize_state(request, db=db)

        # Restore or create world model
        world_model = await self.store.load_world_model(session_id, db=db)
        if not world_model:
            world_model = ApplicationGraph(session_id=session_id)

        supervisor = Supervisor(state=state, world_model=world_model, approved_actions=request.approved_actions)

        # Initial UI planning notification
        yield {
            "type": "tool_start",
            "tool_id": f"tool-init-{session_id[:8]}",
            "tool": "supervisor_planning",
            "title": f"Planning investigation against {request.target_url or 'target'}",
            "input": {"target_url": request.target_url, "max_pages": request.max_pages},
        }

        # ── Step 1: Execute Supervisor Loop with Dynamic Event Streaming ───
        iteration = 0
        limit = request.max_pages

        while iteration < limit and not state.budget.is_exhausted and not state.budget.is_timed_out:
            iteration += 1
            action = supervisor.plan_next_action()
            if not action or action.action_type == ActionType.FINISH:
                break

            # Policy check
            policy_res = PolicyEngine.evaluate(action, state, approved_action_keys=set(request.approved_actions))
            if policy_res.decision != PolicyDecision.ALLOW:
                if policy_res.decision == PolicyDecision.REQUIRE_APPROVAL:
                    yield {
                        "type": "approval_required",
                        "approval_id": action.id,
                        "action": {
                            "action_type": action.action_type.value,
                            "target": action.target,
                            "rationale": action.rationale,
                            "risk_level": action.risk_level.value,
                        },
                    }
                break

            # Stream tool start
            tool_id = f"tool-{uuid.uuid4().hex[:8]}"
            yield {
                "type": "tool_start",
                "tool_id": tool_id,
                "tool": action.action_type.value,
                "title": f"Executing {action.action_type.value} on {action.target}",
                "input": action.parameters,
            }

            agent_res = await supervisor.execute_action(action)
            state.budget.tool_calls_used += 1

            # Update world model with every observation
            for obs in agent_res.observations:
                world_model.record_observation(obs)

            yield {
                "type": "tool_result",
                "tool_id": tool_id,
                "tool": action.action_type.value,
                "status": agent_res.status,
                "latency_ms": agent_res.latency_ms,
                "output": {"summary": agent_res.summary, "status": agent_res.status},
            }

            if agent_res.status == "blocked":
                break

        # ── Step 2: Hypothesis Generation & Multi-Parameter Verification ───
        hyps = HypothesisEngine.generate_hypotheses(world_model, session_id=session_id)
        if hyps:
            yield {
                "type": "tool_start",
                "tool_id": f"tool-hyp-{uuid.uuid4().hex[:8]}",
                "tool": "hypothesis_verifier",
                "title": f"Formulated {len(hyps)} hypotheses — verifying endpoints with evidence",
                "input": {"hypotheses_count": len(hyps)},
            }

            for h in hyps[:3]:
                experiments = HypothesisEngine.design_experiment(h, request.target_url)
                exp_observations = []
                for exp_action in experiments:
                    exp_obs = await supervisor.verifier.verify_endpoint(
                        method=exp_action.parameters.get("method", "GET"),
                        url=exp_action.target,
                        auth_headers=state.auth_context,
                    )
                    exp_observations.append(exp_obs)
                    world_model.record_observation(exp_obs)

                HypothesisEngine.evaluate_observations(h, exp_observations)

        # ── Step 3: Produce Evidence-Backed Inventory & Artifacts ─────────
        inventory = HypothesisEngine.build_evidence_backed_inventory(world_model, hyps)
        metrics = telemetry.get_metrics(session_id)
        report_md = ArtifactGenerator.generate_discovery_report(world_model, inventory, metrics)

        # Durable persistence
        await self.store.save_world_model(world_model, db=db)
        await self.store.save_hypotheses(session_id, hyps, db=db)
        await self.store.save_state(state, db=db)

        # Publish SESSION_COMPLETED event
        await event_bus.publish(
            AgentEvent(
                session_id=session_id,
                event_type=AgentEventType.SESSION_COMPLETED,
                data={
                    "total_endpoints": len(inventory),
                    "verified_endpoints": sum(1 for ep in inventory if ep.confidence == ConfidenceLevel.VERIFIED),
                    "graph_nodes": len(world_model.nodes),
                    "graph_edges": len(world_model.edges),
                },
            )
        )

        # ── Step 4: Stream Structured Synthesis Tokens ────────────────────
        tokens = [
            f"### Investigation Summary for {request.target_url}\n\n",
            f"- **Discovered Endpoints**: {len(inventory)}\n",
            f"- **Verified with Evidence**: {sum(1 for ep in inventory if ep.confidence == ConfidenceLevel.VERIFIED)}\n",
            f"- **Application Graph Nodes**: {len(world_model.nodes)} ({len(world_model.edges)} relationships)\n\n",
            f"```http\n",
        ]
        for ep in inventory[:5]:
            tokens.append(f"{ep.method} {ep.template_path} -> {ep.status_code or 200} [{ep.confidence.value.upper()}]\n")
        tokens.append(f"```\n\n")

        if hyps:
            tokens.append(f"> [!NOTE]\n> **Hypotheses Tested**: {len(hyps)} behavioral hypotheses evaluated.\n\n")

        for token in tokens:
            yield {"type": "token", "content": token}

        yield {
            "type": "done",
            "session_id": session_id,
            "summary": {
                "discovered_count": len(inventory),
                "verified_count": sum(1 for ep in inventory if ep.confidence == ConfidenceLevel.VERIFIED),
                "graph_size": len(world_model.nodes),
            },
        }

    async def resume_investigation(self, session_id: str, db: Optional[AsyncSession] = None) -> Optional[AgentState]:
        """Restore investigation state for a given session."""
        return await self.store.load_state(session_id, db=db)

    async def get_artifacts(self, session_id: str, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """Generate and retrieve all product artifacts for an investigation."""
        world_model = await self.store.load_world_model(session_id, db=db) or ApplicationGraph(session_id=session_id)
        hyps = await self.store.load_hypotheses(session_id, db=db)
        inventory = HypothesisEngine.build_evidence_backed_inventory(world_model, hyps)
        metrics = telemetry.get_metrics(session_id)

        target_url = "https://api.example.com"
        for node in world_model.nodes.values():
            if node.node_type.value == "page" and node.attributes.get("url"):
                target_url = node.attributes["url"]
                break

        return {
            "session_id": session_id,
            "inventory": [ep.model_dump() for ep in inventory],
            "openapi_spec": ArtifactGenerator.generate_openapi_spec(inventory, target_url=target_url),
            "postman_collection": ArtifactGenerator.generate_postman_collection(inventory, base_url=target_url),
            "pytest_suite": ArtifactGenerator.generate_pytest_suite(inventory, base_url=target_url),
            "discovery_report": ArtifactGenerator.generate_discovery_report(world_model, inventory, metrics),
            "graph": world_model.to_dict(),
        }


# Global runtime singleton
runtime_service = InvestigationRuntime()
