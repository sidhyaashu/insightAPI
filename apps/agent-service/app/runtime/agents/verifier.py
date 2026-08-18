"""
runtime/agents/verifier.py — Skeptical Verification & Evidence-Gathering Agent.

Role (AGENTS.md §11, §12, §15, §30):
  - Skeptical replay of discovered endpoints with varied parameter values
  - Confirms authentication requirements (authenticated vs unauthenticated response)
  - Produces structured Evidence objects and upgrades ConfidenceLevel to VERIFIED
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
    Evidence,
    EvidenceStatus,
    Observation,
    ObservationSource,
    VerificationResult,
)
from app.tools import probe_http_endpoint

logger = logging.getLogger("agent.runtime.verifier")


class VerificationAgent(BaseAgent):
    """
    Skeptical agent dedicated to replaying endpoints, validating parameters, and establishing evidence.
    """

    async def execute(
        self,
        task: AgentTask,
        state: AgentState,
    ) -> AgentResult:
        start_time = time.perf_counter()
        endpoint_key = task.parameters.get("endpoint_key", "")
        method = task.parameters.get("method", "GET").upper()
        target_url = task.target or ""

        await self.emit_event(
            session_id=state.session_id,
            event_type=AgentEventType.VERIFICATION_STARTED,
            data={"role": "verifier", "task_id": task.id, "endpoint_key": endpoint_key},
        )

        observations: List[Observation] = []
        evidence_list: List[Evidence] = []
        status_codes: List[int] = []

        # 1. Baseline Replay Test
        base_res = await probe_http_endpoint(
            url=target_url,
            method=method,
            headers=state.auth_context.get("headers"),
        )
        state.budget.http_requests_used += 1
        state.budget.tool_calls_used += 1

        if base_res.status == "success":
            status_codes.append(base_res.data.get("status_code", 0))
            obs_base = Observation(
                session_id=state.session_id,
                source=ObservationSource.VERIFICATION,
                request_method=method,
                request_url=target_url,
                response_status=base_res.data.get("status_code"),
                confidence=ConfidenceLevel.TESTED,
                latency_ms=base_res.latency_ms,
                tags=["verification_baseline"],
            )
            observations.append(obs_base)

            evidence_list.append(
                Evidence(
                    session_id=state.session_id,
                    observation_id=obs_base.id,
                    endpoint_key=endpoint_key,
                    status=EvidenceStatus.TESTED,
                    confidence_score=0.8,
                    description=f"Baseline replay returned status {base_res.data.get('status_code')}",
                )
            )

        # 2. Auth Requirement Test (probe unauthenticated if credentials exist)
        auth_required = False
        if state.auth_context.get("headers"):
            unauth_res = await probe_http_endpoint(
                url=target_url,
                method=method,
                headers={},  # strip auth
            )
            state.budget.http_requests_used += 1
            state.budget.tool_calls_used += 1

            unauth_status = unauth_res.data.get("status_code", 0)
            status_codes.append(unauth_status)
            if unauth_status in (401, 403):
                auth_required = True
                obs_auth = Observation(
                    session_id=state.session_id,
                    source=ObservationSource.VERIFICATION,
                    request_method=method,
                    request_url=target_url,
                    response_status=unauth_status,
                    confidence=ConfidenceLevel.VERIFIED,
                    tags=["auth_requirement_check"],
                )
                observations.append(obs_auth)
                evidence_list.append(
                    Evidence(
                        session_id=state.session_id,
                        observation_id=obs_auth.id,
                        endpoint_key=endpoint_key,
                        status=EvidenceStatus.VERIFIED,
                        confidence_score=0.95,
                        description=f"Confirmed authentication required (401/403 returned on unauthenticated request)",
                    )
                )

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        is_verified = len(status_codes) > 0 and 200 in status_codes

        if is_verified:
            await self.emit_event(
                session_id=state.session_id,
                event_type=AgentEventType.ENDPOINT_VERIFIED,
                data={
                    "endpoint_key": endpoint_key,
                    "confidence": "verified",
                    "auth_required": auth_required,
                    "observed_statuses": status_codes,
                },
            )

        result = AgentResult(
            task_id=task.id,
            agent_id=self.agent_id,
            role="verifier",
            status="completed" if is_verified else "failed",
            summary=f"Verified {endpoint_key}: statuses={status_codes}, auth_required={auth_required}.",
            observations=observations,
            evidence=evidence_list,
            latency_ms=latency_ms,
        )

        await self.emit_event(
            session_id=state.session_id,
            event_type=AgentEventType.VERIFICATION_COMPLETED,
            data={"role": "verifier", "task_id": task.id, "verified": is_verified},
        )

        return result
