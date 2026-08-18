"""
runtime/agents/network.py — Specialized Network & Traffic Intelligence Agent.

Role (AGENTS.md §15):
  - Direct HTTP probing, cURL execution, and HAR log parsing
  - Dynamic route template normalization
  - Schema inference on live response bodies
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
from app.tools import (
    probe_http_endpoint,
    execute_curl,
    infer_openapi_schema,
)
from app.tools.traffic_parser import parse_har_traffic
from app.core.utils import normalize_route_template

logger = logging.getLogger("agent.runtime.network")


class NetworkAgent(BaseAgent):
    """
    Specialized agent for direct HTTP communication, traffic parsing, and schema analysis.
    """

    async def execute(
        self,
        task: AgentTask,
        state: AgentState,
    ) -> AgentResult:
        start_time = time.perf_counter()
        action_type = task.parameters.get("action_type", "probe_http")
        target_url = task.target or state.goal.target_url

        await self.emit_event(
            session_id=state.session_id,
            event_type=AgentEventType.SUBAGENT_STARTED,
            data={"role": "network", "task_id": task.id, "action": action_type},
        )

        observations: List[Observation] = []
        discovered_endpoints: List[Dict[str, Any]] = []
        status = "completed"
        error_msg = None

        if action_type == "parse_har":
            har_text = task.parameters.get("har_text", "")
            res = parse_har_traffic(har_text)
            state.budget.tool_calls_used += 1
            if res.status == "success":
                discovered_endpoints = res.data.get("endpoints", [])
                for ep in discovered_endpoints:
                    observations.append(
                        Observation(
                            session_id=state.session_id,
                            source=ObservationSource.NETWORK,
                            request_method=ep.get("method"),
                            request_url=ep.get("example_url"),
                            request_template=ep.get("template_path"),
                            response_status=ep.get("status_code"),
                            confidence=ConfidenceLevel.TESTED,
                            latency_ms=res.latency_ms,
                        )
                    )
            else:
                status = "failed"
                error_msg = res.error

        elif action_type == "execute_curl":
            curl_command = task.parameters.get("curl_command", "")
            res = await execute_curl(curl_command)
            state.budget.http_requests_used += 1
            state.budget.tool_calls_used += 1
            if res.status == "success":
                method = res.data.get("method", "GET")
                url = res.data.get("url", "")
                template = normalize_route_template(url)
                ep_dict = {
                    "method": method,
                    "template_path": template,
                    "example_url": url,
                    "status_code": res.data.get("status_code"),
                }
                discovered_endpoints.append(ep_dict)
                observations.append(
                    Observation(
                        session_id=state.session_id,
                        source=ObservationSource.HTTP,
                        request_method=method,
                        request_url=url,
                        request_template=template,
                        response_status=res.data.get("status_code"),
                        response_body=res.data.get("body"),
                        confidence=ConfidenceLevel.TESTED,
                        latency_ms=res.latency_ms,
                    )
                )
            else:
                status = "failed"
                error_msg = res.error

        else:  # probe_http default
            method = task.parameters.get("method", "GET").upper()
            auth_headers = task.parameters.get("headers") or state.auth_context.get("headers")
            body = task.parameters.get("body")

            res = await probe_http_endpoint(
                url=target_url,
                method=method,
                headers=auth_headers,
                body=body,
            )
            state.budget.http_requests_used += 1
            state.budget.tool_calls_used += 1

            if res.status == "success":
                template = normalize_route_template(target_url)
                resp_body = res.data.get("body")
                schema = None
                if res.data.get("is_json") and isinstance(resp_body, (dict, list)):
                    schema_res = infer_openapi_schema(resp_body)
                    if schema_res.status == "success":
                        schema = schema_res.data.get("schema")

                ep_dict = {
                    "method": method,
                    "template_path": template,
                    "example_url": target_url,
                    "status_code": res.data.get("status_code"),
                    "inferred_schema": schema,
                }
                discovered_endpoints.append(ep_dict)
                observations.append(
                    Observation(
                        session_id=state.session_id,
                        source=ObservationSource.HTTP,
                        request_method=method,
                        request_url=target_url,
                        request_template=template,
                        response_status=res.data.get("status_code"),
                        response_body=resp_body,
                        inferred_schema=schema,
                        confidence=ConfidenceLevel.TESTED,
                        latency_ms=res.latency_ms,
                    )
                )

                await self.emit_event(
                    session_id=state.session_id,
                    event_type=AgentEventType.ENDPOINT_DISCOVERED,
                    data={
                        "endpoint_key": f"{method} {template}",
                        "method": method,
                        "template_path": template,
                        "status_code": res.data.get("status_code"),
                    },
                )
            else:
                status = "failed"
                error_msg = res.error

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        result = AgentResult(
            task_id=task.id,
            agent_id=self.agent_id,
            role="network",
            status=status,
            summary=f"Network task ({action_type}) on {target_url}: status={status}.",
            observations=observations,
            discovered_endpoints=discovered_endpoints,
            error=error_msg,
            latency_ms=latency_ms,
        )

        await self.emit_event(
            session_id=state.session_id,
            event_type=AgentEventType.SUBAGENT_COMPLETED,
            data={"role": "network", "task_id": task.id, "endpoints_count": len(discovered_endpoints)},
        )

        return result
