"""
runtime/agents/recon.py — Autonomous Reconnaissance & Tech-Stack Fingerprinting Agent.

Role (AGENTS.md §15):
  - Phase 1 pre-crawl application reconnaissance
  - Sitemaps & robots.txt discovery for route seeding
  - Technology stack, CMS, and edge WAF fingerprinting
  - Structured metadata (JSON-LD, OpenGraph) extraction
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
from app.tools.recon import recon_website

logger = logging.getLogger("agent.runtime.recon")


class ReconAgent(BaseAgent):
    """
    Specialized agent for pre-crawl sitemap discovery and technology stack fingerprinting.
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
            data={"role": "recon", "task_id": task.id, "target": target_url},
        )

        auth_hdrs = state.auth_context if (isinstance(state.auth_context, dict) and not state.auth_context.get("headers")) else (state.auth_context.get("headers") if isinstance(state.auth_context, dict) else None)
        
        tool_result = await recon_website(
            url=target_url,
            auth_headers=auth_hdrs,
            timeout_sec=task.parameters.get("timeout_sec", 15.0),
        )

        state.budget.tool_calls_used += 1
        observations: List[Observation] = []

        if tool_result.status == "success":
            data = tool_result.data
            technologies = data.get("technologies", [])
            sitemap_urls = data.get("sitemap_urls", [])
            title = data.get("title", "")
            status_code = data.get("status_code", 200)
            is_waf = data.get("is_waf_protected", False)

            # 1. Root page observation with technology stack
            tech_tags = [f"tech:{t['name'].lower().replace(' ', '_')}" for t in technologies]
            obs_root = Observation(
                session_id=state.session_id,
                source=ObservationSource.BROWSER,
                page_url=target_url,
                page_title=title or ("Access Denied (403)" if is_waf and status_code == 403 else "Landing Page"),
                response_status=status_code,
                confidence=ConfidenceLevel.TESTED,
                tags=["recon_root", "tech_fingerprint"] + tech_tags,
                metadata={
                    "technologies": technologies,
                    "robots_txt": data.get("robots_txt", {}),
                    "json_ld_schemas": data.get("json_ld_schemas", []),
                    "is_waf_protected": is_waf,
                },
            )
            observations.append(obs_root)

            # 2. Add discovered sitemap routes to frontier observations
            for s_url in sitemap_urls:
                if s_url != target_url and s_url not in state.visited_urls:
                    obs_sitemap = Observation(
                        session_id=state.session_id,
                        source=ObservationSource.BROWSER,
                        page_url=s_url,
                        confidence=ConfidenceLevel.INFERRED,
                        tags=["discovered_page", "sitemap_frontier"],
                    )
                    observations.append(obs_sitemap)

            # 3. Add discovered API subdomains to frontier observations
            for sub in data.get("discovered_subdomains", []):
                sub_url = sub.get("url")
                if sub_url and sub_url not in state.visited_urls:
                    obs_sub = Observation(
                        session_id=state.session_id,
                        source=ObservationSource.BROWSER,
                        page_url=sub_url,
                        page_title=f"API Gateway Subdomain ({sub.get('prefix')})",
                        confidence=ConfidenceLevel.INFERRED,
                        tags=["discovered_subdomain", f"subdomain:{sub.get('prefix')}"],
                        metadata={"ips": sub.get("ips", []), "cnames": sub.get("cnames", [])},
                    )
                    observations.append(obs_sub)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        tech_summary = ", ".join([t["name"] for t in tool_result.data.get("technologies", [])]) or "Generic Web"
        sitemaps_count = len(tool_result.data.get("sitemap_urls", []))

        result = AgentResult(
            task_id=task.id,
            agent_id=self.agent_id,
            role="recon",
            status="completed" if tool_result.status == "success" else "failed",
            summary=f"Reconnaissance on {target_url}: detected [{tech_summary}], found {sitemaps_count} sitemap routes.",
            observations=observations,
            discovered_endpoints=[],
            error=tool_result.error,
            latency_ms=latency_ms,
        )

        await self.emit_event(
            session_id=state.session_id,
            event_type=AgentEventType.SUBAGENT_COMPLETED,
            data={
                "role": "recon",
                "task_id": task.id,
                "technologies": tool_result.data.get("technologies", []),
                "sitemap_urls_count": sitemaps_count,
            },
        )

        return result
