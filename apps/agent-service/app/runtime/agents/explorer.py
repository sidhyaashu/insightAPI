"""
runtime/agents/explorer.py — Autonomous Explorer Agent for Web & UI Discovery.

Role (AGENTS.md §15):
  - Browser navigation & accessibility tree analysis
  - Dynamic clicks, form population, virtual scrolling, SPA state tracking
  - Discovers undocumented APIs via UI actuation
"""
from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from app.runtime.agents.base import BaseAgent, AgentTask, AgentResult
from app.runtime.models import (
    AgentEventType,
    AgentState,
    ConfidenceLevel,
    Observation,
    ObservationSource,
)
from app.tools.browser_explorer import explore_web_app_browser

logger = logging.getLogger("agent.runtime.explorer")


class ExplorerAgent(BaseAgent):
    """
    Specialized agent for autonomous UI, DOM, and browser exploration.
    """

    async def execute(
        self,
        task: AgentTask,
        state: AgentState,
    ) -> AgentResult:
        start_time = time.perf_counter()
        target_url = task.target or state.goal.target_url

        await self.emit_event(
            session_id=state.session_id,
            event_type=AgentEventType.SUBAGENT_STARTED,
            data={"role": "explorer", "task_id": task.id, "target": target_url},
        )

        max_clicks = task.parameters.get("max_clicks", 15)
        timeout_sec = task.parameters.get("timeout_sec", 25.0)

        tool_result = await explore_web_app_browser(
            url=target_url,
            max_clicks=max_clicks,
            timeout_sec=timeout_sec,
            auth_headers=state.auth_context.get("headers"),
        )

        state.budget.browser_actions_used += tool_result.data.get("actions_executed", 1)
        state.budget.tool_calls_used += 1

        observations: List[Observation] = []
        discovered_endpoints: List[Dict[str, Any]] = tool_result.data.get("endpoints", [])

        # Record page navigation in state
        state.record_url_visited(target_url)

        if tool_result.status == "success":
            for ep in discovered_endpoints:
                obs = Observation(
                    session_id=state.session_id,
                    source=ObservationSource.BROWSER,
                    page_url=target_url,
                    request_method=ep.get("method"),
                    request_url=ep.get("example_url"),
                    request_template=ep.get("template_path"),
                    response_status=ep.get("status_code"),
                    response_body=ep.get("sample_response"),
                    confidence=ConfidenceLevel.TESTED,
                    latency_ms=tool_result.latency_ms,
                    tags=["browser_discovery", "spa"],
                )
                observations.append(obs)

                await self.emit_event(
                    session_id=state.session_id,
                    event_type=AgentEventType.ENDPOINT_DISCOVERED,
                    data={
                        "endpoint_key": f"{ep.get('method')} {ep.get('template_path')}",
                        "method": ep.get("method"),
                        "template_path": ep.get("template_path"),
                        "source": "browser_exploration",
                        "status_code": ep.get("status_code"),
                    },
                )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        result = AgentResult(
            task_id=task.id,
            agent_id=self.agent_id,
            role="explorer",
            status="completed" if tool_result.status == "success" else "failed",
            summary=f"Explored {target_url}: executed {tool_result.data.get('actions_executed', 0)} actions, discovered {len(discovered_endpoints)} endpoints.",
            observations=observations,
            discovered_endpoints=discovered_endpoints,
            error=tool_result.error,
            latency_ms=latency_ms,
        )

        await self.emit_event(
            session_id=state.session_id,
            event_type=AgentEventType.SUBAGENT_COMPLETED,
            data={"role": "explorer", "task_id": task.id, "discovered_count": len(discovered_endpoints)},
        )

        return result
