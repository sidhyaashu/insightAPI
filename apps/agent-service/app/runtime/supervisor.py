"""
runtime/supervisor.py — Autonomous Supervisor, Information-Gain Planner & Agent Orchestrator.

Architecture (AGENTS.md §4, §13, §14, §16, §24, §30):
  The Supervisor coordinates ExplorerAgent, NetworkAgent, and VerificationAgent
  through a stateful planning loop:
    Goal → State → World Model → Hypotheses → Planner → Action →
    Observation → Evidence → Reflection → Verification → Next Action
"""
from __future__ import annotations

import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Set

from app.runtime.models import (
    Action,
    ActionType,
    AgentEvent,
    AgentEventType,
    AgentState,
    ConfidenceLevel,
    Evidence,
    Goal,
    Hypothesis,
    HypothesisStatus,
    Observation,
    PolicyDecision,
    PolicyResult,
)
from app.runtime.world_model import ApplicationGraph
from app.runtime.policy import PolicyEngine
from app.runtime.agents.base import AgentTask, AgentResult
from app.runtime.agents.explorer import ExplorerAgent
from app.runtime.agents.network import NetworkAgent
from app.runtime.agents.verifier import VerificationAgent
from app.runtime.events import event_bus

logger = logging.getLogger("agent.runtime.supervisor")


class Supervisor:
    """
    Autonomous Supervisor and Information-Gain Planning Orchestrator.
    """

    def __init__(
        self,
        state: AgentState,
        world_model: Optional[ApplicationGraph] = None,
        approved_actions: Optional[List[str]] = None,
    ) -> None:
        self.state = state
        self.world_model = world_model or ApplicationGraph(session_id=state.session_id)
        self.approved_actions = set(approved_actions or [])

        # Child agents
        self.explorer = ExplorerAgent()
        self.network = NetworkAgent()
        self.verifier = VerificationAgent()

    async def emit_event(
        self,
        event_type: AgentEventType,
        data: Dict[str, Any],
        error: Optional[str] = None,
    ) -> None:
        """Emit a structured event to AgentEventBus."""
        event = AgentEvent(
            session_id=self.state.session_id,
            event_type=event_type,
            data=data,
            error=error,
        )
        await event_bus.publish(event)

    def plan_next_action(self) -> Optional[Action]:
        """
        Information-Gain Action Selection Heuristic (AGENTS.md §14).

        Ranks potential actions based on:
        - Novelty: Unvisited pages score highest for exploration.
        - Verification need: Discovered unverified endpoints require verification.
        - Budget limits: Selects FINISH if budget exhausted or goal satisfied.
        """
        if self.state.budget.is_exhausted or self.state.budget.is_timed_out:
            return Action(
                session_id=self.state.session_id,
                action_type=ActionType.FINISH,
                rationale="Budget or time limit reached.",
            )

        # 1. If target URL hasn't been explored yet, prioritize browser exploration
        target_url = self.state.goal.target_url
        if target_url and target_url not in self.state.visited_urls:
            return Action(
                session_id=self.state.session_id,
                action_type=ActionType.NAVIGATE,
                target=target_url,
                parameters={"max_clicks": 15},
                rationale=f"Explore root target application {target_url} to discover interactive API surface.",
            )

        # 2. Check for open hypotheses or unverified endpoints to verify
        for node in self.world_model.nodes.values():
            if node.node_type.value == "endpoint":
                conf = node.attributes.get("confidence")
                if conf in (ConfidenceLevel.INFERRED.value, ConfidenceLevel.TESTED.value):
                    endpoint_key = node.label
                    ep_url = node.attributes.get("example_url")
                    method = node.attributes.get("method", "GET")
                    if ep_url and node.id not in self.state.verified_endpoint_ids:
                        return Action(
                            session_id=self.state.session_id,
                            action_type=ActionType.VERIFY_ENDPOINT,
                            target=ep_url,
                            parameters={"endpoint_key": endpoint_key, "method": method, "endpoint_id": node.id},
                            rationale=f"Skeptically verify endpoint {endpoint_key} with auth and parameter checks.",
                        )

        # 3. If everything current is explored and verified, finish
        return Action(
            session_id=self.state.session_id,
            action_type=ActionType.FINISH,
            rationale="Exploration and verification goals achieved.",
        )

    async def execute_action(self, action: Action) -> AgentResult:
        """
        Enforce policy check, route action to appropriate specialized agent, and record outcome.
        """
        # 1. Policy & Scope evaluation (AGENTS.md §22)
        policy_res = PolicyEngine.evaluate(
            action=action,
            state=self.state,
            approved_action_keys=self.approved_actions,
        )

        if policy_res.decision == PolicyDecision.DENY:
            return AgentResult(
                task_id=action.id,
                agent_id="supervisor",
                role="supervisor",
                status="failed",
                summary=f"Policy Blocked: {policy_res.reason}",
                error=policy_res.reason,
            )

        if policy_res.decision == PolicyDecision.REQUIRE_APPROVAL:
            await self.emit_event(
                event_type=AgentEventType.APPROVAL_REQUIRED,
                data={
                    "approval_id": policy_res.requires_approval_id,
                    "action": action.model_dump(),
                    "reason": policy_res.reason,
                },
            )
            return AgentResult(
                task_id=action.id,
                agent_id="supervisor",
                role="supervisor",
                status="blocked",
                summary=f"Action requires approval: {policy_res.reason}",
            )

        # 2. Delegate to specialized agent
        self.state.add_recent_action(action)
        await self.emit_event(
            event_type=AgentEventType.TOOL_STARTED,
            data={"tool": action.action_type.value, "target": action.target, "input": action.parameters},
        )

        res: AgentResult
        if action.action_type == ActionType.NAVIGATE:
            task = AgentTask(
                parent_agent_id="supervisor",
                role="explorer",
                goal=action.rationale or "Explore page",
                target=action.target,
                parameters=action.parameters,
            )
            res = await self.explorer.execute(task, self.state)

        elif action.action_type == ActionType.VERIFY_ENDPOINT:
            task = AgentTask(
                parent_agent_id="supervisor",
                role="verifier",
                goal=action.rationale or "Verify endpoint",
                target=action.target,
                parameters=action.parameters,
            )
            res = await self.verifier.execute(task, self.state)
            ep_id = action.parameters.get("endpoint_id")
            if ep_id and res.status == "completed":
                self.state.verified_endpoint_ids.append(ep_id)

        elif action.action_type in (ActionType.PROBE_HTTP, ActionType.EXECUTE_CURL, ActionType.PARSE_HAR):
            task = AgentTask(
                parent_agent_id="supervisor",
                role="network",
                goal=action.rationale or "Execute network probe",
                target=action.target,
                parameters=action.parameters,
            )
            res = await self.network.execute(task, self.state)
        else:
            res = AgentResult(
                task_id=action.id,
                agent_id="supervisor",
                role="supervisor",
                status="completed",
                summary=f"Action {action.action_type.value} completed.",
            )

        await self.emit_event(
            event_type=AgentEventType.TOOL_COMPLETED,
            data={
                "tool": action.action_type.value,
                "status": res.status,
                "latency_ms": res.latency_ms,
                "output": {"summary": res.summary, "error": res.error},
            },
        )
        return res

    async def run(self, max_iterations: Optional[int] = None) -> AsyncIterator[AgentEvent]:
        """
        Execute the canonical stateful supervisor loop until completion or budget exhaustion.
        Architecture (AGENTS.md §4, §13, §29, §30).
        """
        await self.emit_event(
            event_type=AgentEventType.SESSION_STARTED,
            data={"goal": self.state.goal.model_dump(), "target_url": self.state.current_url},
        )

        iteration = 0
        limit = max_iterations if max_iterations is not None else self.state.budget.max_tool_calls

        while (
            iteration < limit
            and not self.state.budget.is_exhausted
            and not self.state.budget.is_timed_out
        ):
            iteration += 1

            # 1. Information-Gain Action Planning
            action = self.plan_next_action()
            if not action or action.action_type == ActionType.FINISH:
                logger.info(f"Supervisor loop finished: {action.rationale if action else 'No action'}")
                break

            await self.emit_event(
                event_type=AgentEventType.ACTION_REQUESTED,
                data=action.model_dump(),
            )

            # 2. Execute Action via Specialized Agent
            result = await self.execute_action(action)

            # 3. World Model & Graph Update — ensure every observation reaches ApplicationGraph
            for obs in result.observations:
                self.world_model.record_observation(obs)

            # 4. Check if blocked
            if result.status == "blocked":
                break

        await self.emit_event(
            event_type=AgentEventType.SESSION_COMPLETED,
            data={
                "session_id": self.state.session_id,
                "summary": self.world_model.summary(),
                "visited_pages": self.state.visited_urls,
                "budget_used": {
                    "tool_calls": self.state.budget.tool_calls_used,
                    "http_requests": self.state.budget.http_requests_used,
                    "browser_actions": self.state.budget.browser_actions_used,
                },
            },
        )
