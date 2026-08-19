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

    def plan_next_action(self) -> Action:
        """
        Stateful planning heuristic (AGENTS.md §13, §14).

        Ranks potential actions based on:
        - Novelty: Unvisited pages score highest for exploration.
        - Verification need: Discovered unverified endpoints require verification.
        - Budget limits: Selects FINISH if budget exhausted or goal satisfied.
        """
        from app.runtime.debug import (
            recorder,
            PlannerDecisionTrace,
            CandidateActionScore,
        )

        candidates: List[CandidateActionScore] = []
        selected_action_obj: Action

        if self.state.budget.is_exhausted or self.state.budget.is_timed_out:
            selected_action_obj = Action(
                session_id=self.state.session_id,
                action_type=ActionType.FINISH,
                rationale="Budget or time limit reached.",
            )
            candidates.append(CandidateActionScore(
                action_type="finish",
                target="session",
                score=1.0,
                reason="Budget or time limit exhausted",
            ))
        else:
            # 1. Root page exploration candidate
            target_url = self.state.goal.target_url
            if target_url and target_url not in self.state.visited_urls:
                candidates.append(CandidateActionScore(
                    action_type="navigate",
                    target=target_url,
                    score=0.95,
                    information_gain=0.90,
                    reason="Root target page has not been explored yet.",
                ))

            # 2. Unverified endpoints
            for node in self.world_model.nodes.values():
                if node.node_type.value == "endpoint":
                    conf = node.attributes.get("confidence")
                    if conf in (ConfidenceLevel.INFERRED.value, ConfidenceLevel.TESTED.value):
                        endpoint_key = node.label
                        ep_url = node.attributes.get("example_url")
                        method = node.attributes.get("method", "GET")
                        if ep_url and node.id not in self.state.verified_endpoint_ids:
                            candidates.append(CandidateActionScore(
                                action_type="verify_endpoint",
                                target=ep_url,
                                score=0.85,
                                information_gain=0.75,
                                reason=f"Endpoint {endpoint_key} discovered but unverified.",
                            ))

            if not candidates:
                selected_action_obj = Action(
                    session_id=self.state.session_id,
                    action_type=ActionType.FINISH,
                    rationale="Exploration and verification goals achieved.",
                )
                candidates.append(CandidateActionScore(
                    action_type="finish",
                    target="session",
                    score=1.0,
                    reason="All reachable routes explored and verified",
                ))
            else:
                best = max(candidates, key=lambda c: c.score)
                if best.action_type == "navigate":
                    selected_action_obj = Action(
                        session_id=self.state.session_id,
                        action_type=ActionType.NAVIGATE,
                        target=best.target,
                        parameters={"max_clicks": 15},
                        rationale=f"Explore root target application {best.target} to discover interactive API surface.",
                    )
                elif best.action_type == "verify_endpoint":
                    # Find matching node id
                    matching_node_id = None
                    for n in self.world_model.nodes.values():
                        if n.attributes.get("example_url") == best.target:
                            matching_node_id = n.id
                            break
                    selected_action_obj = Action(
                        session_id=self.state.session_id,
                        action_type=ActionType.VERIFY_ENDPOINT,
                        target=best.target,
                        parameters={"endpoint_key": best.target, "endpoint_id": matching_node_id},
                        rationale=best.reason,
                    )
                else:
                    selected_action_obj = Action(
                        session_id=self.state.session_id,
                        action_type=ActionType.FINISH,
                        rationale="Goal satisfied.",
                    )

        # Record planner decision trace
        try:
            recorder.record_planner_decision(
                session_id=self.state.session_id,
                trace=PlannerDecisionTrace(
                    session_id=self.state.session_id,
                    current_url=self.state.current_url,
                    known_endpoints_count=len(self.world_model.get_endpoints()),
                    verified_endpoints_count=len(self.state.verified_endpoint_ids),
                    hypotheses_count=len(self.state.hypotheses),
                    candidate_actions=candidates,
                    selected_action=selected_action_obj.action_type.value,
                    selected_target=selected_action_obj.target,
                    selection_rationale=selected_action_obj.rationale or "",
                ),
            )
        except Exception:
            pass

        return selected_action_obj

    async def execute_action(self, action: Action) -> AgentResult:
        """
        Enforce policy check, route action to appropriate specialized agent, and record outcome.
        """
        from app.runtime.debug import (
            recorder,
            tracer,
            stuck_detector,
            SpanType,
            ActionTrace,
            ActionState,
            PolicyEvaluationTrace,
        )

        start_time = time.perf_counter()

        # 1. Policy & Scope evaluation (AGENTS.md §22)
        policy_res = PolicyEngine.evaluate(
            action=action,
            state=self.state,
            approved_action_keys=self.approved_actions,
        )

        # Record policy trace
        try:
            recorder.record_policy_evaluation(
                session_id=self.state.session_id,
                trace=PolicyEvaluationTrace(
                    session_id=self.state.session_id,
                    action_id=action.id,
                    action_type=action.action_type.value,
                    target=action.target or "",
                    risk_level=action.risk_level.value,
                    scope_allowed=policy_res.decision != PolicyDecision.DENY or "scope" not in policy_res.reason.lower(),
                    ssrf_safe=policy_res.decision != PolicyDecision.DENY or "ssrf" not in policy_res.reason.lower(),
                    budget_allowed=not self.state.budget.is_exhausted,
                    approval_required=policy_res.decision == PolicyDecision.REQUIRE_APPROVAL,
                    decision=policy_res.decision.value,
                    reason=policy_res.reason,
                ),
            )
        except Exception:
            pass

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

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Record action trace and stuck check
        try:
            action_state_val = ActionState.SUCCEEDED if res.status == "completed" else ActionState.FAILED
            recorder.record_action(
                session_id=self.state.session_id,
                trace=ActionTrace(
                    action_id=action.id,
                    session_id=self.state.session_id,
                    agent_id=res.agent_id or "supervisor",
                    action_type=action.action_type.value,
                    target=action.target or "",
                    parameters=action.parameters,
                    risk_level=action.risk_level.value,
                    policy_decision=policy_res.decision.value,
                    policy_reason=policy_res.reason,
                    state=action_state_val,
                    duration_ms=duration_ms,
                    failure_reason=res.error,
                    observation_ids=[obs.id for obs in res.observations],
                ),
            )

            stuck_eval = stuck_detector.record_step(
                session_id=self.state.session_id,
                action_type=action.action_type.value,
                target=action.target or "",
                new_observations_count=len(res.observations),
            )
            if stuck_eval.is_stuck:
                recorder.record_stuck(self.state.session_id, stuck_eval)
        except Exception:
            pass

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
