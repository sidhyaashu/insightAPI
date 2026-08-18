"""
runtime/artifacts.py — Unified Product Artifact Generator for InsightAPI.

Architecture (AGENTS.md §21, §31):
  Core artifacts:
    - Evidence-backed API inventory
    - Application World Model Graph
    - OpenAPI 3.0.3 / 3.1.0 specification
    - Postman v2.1.0 Collection
    - Pytest automated regression test suite
    - Executive Discovery & Evidence Report (Markdown)

Security Rule (AGENTS.md §21):
  - Never leak authorization headers, tokens, or credentials into exported specs or artifacts.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.runtime.models import (
    ConfidenceLevel,
    DiscoveredEndpoint,
)
from app.runtime.world_model import ApplicationGraph
from app.runtime.observability import SessionMetrics
from app.services.openapi_exporter import OpenAPIExporter
from app.services.postman_exporter import PostmanExporter
from app.tools.test_generator import generate_pytest_suite as _generate_pytest_suite


class ArtifactGenerator:
    """
    Unified product artifact generation engine for InsightAPI investigations.
    """

    @staticmethod
    def generate_openapi_spec(
        inventory: List[DiscoveredEndpoint],
        title: str = "InsightAPI Discovered Surface",
        target_url: str = "https://api.example.com",
        version: str = "1.0.0",
    ) -> Dict[str, Any]:
        """
        Produce a valid OpenAPI 3.0.3 / 3.1.0 specification JSON from the discovered inventory.
        """
        endpoints_data = []
        for ep in inventory:
            endpoints_data.append({
                "method": ep.method,
                "template_route": ep.template_path,
                "schema": ep.inferred_schema or {"type": "object"},
                "confidence": 0.95 if ep.confidence == ConfidenceLevel.VERIFIED else 0.8,
                "status": ep.status_code or 200,
                "url": ep.example_url or f"{target_url.rstrip('/')}{ep.template_path}",
                "examples": [
                    {
                        "response_body": ep.example_url,
                        "request_payload": None,
                    }
                ] if ep.example_url else [],
            })

        return OpenAPIExporter.generate_spec(
            title=title,
            target_url=target_url,
            captured_endpoints=endpoints_data,
            version=version,
        )

    @staticmethod
    def generate_postman_collection(
        inventory: List[DiscoveredEndpoint],
        collection_name: str = "InsightAPI Discovered Endpoints",
        base_url: str = "https://api.example.com",
    ) -> Dict[str, Any]:
        """
        Produce a Postman v2.1.0 Collection from the discovered endpoints.
        """
        endpoints_data = []
        for ep in inventory:
            endpoints_data.append({
                "method": ep.method,
                "template_route": ep.template_path,
                "schema": ep.inferred_schema or {},
                "confidence": 0.95 if ep.confidence == ConfidenceLevel.VERIFIED else 0.8,
                "status": ep.status_code or 200,
                "url": ep.example_url or f"{base_url.rstrip('/')}{ep.template_path}",
            })

        return PostmanExporter.generate_collection(
            title=collection_name,
            target_url=base_url,
            captured_endpoints=endpoints_data,
        )

    @staticmethod
    def generate_pytest_suite(
        inventory: List[DiscoveredEndpoint],
        base_url: str = "https://api.example.com",
        auth_header: Optional[str] = None,
    ) -> str:
        """
        Generate a runnable Pytest regression test suite for all discovered endpoints.
        """
        endpoints_data = [ep.model_dump() for ep in inventory]
        return _generate_pytest_suite(
            endpoints=endpoints_data,
            base_url=base_url,
            auth_header=auth_header,
        )

    @staticmethod
    def generate_discovery_report(
        world_model: ApplicationGraph,
        inventory: List[DiscoveredEndpoint],
        metrics: Optional[SessionMetrics] = None,
    ) -> str:
        """
        Generate a comprehensive, evidence-backed Markdown Discovery Report.
        """
        summary = world_model.summary()
        verified_count = sum(1 for ep in inventory if ep.confidence == ConfidenceLevel.VERIFIED)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            f"# InsightAPI Discovery & Evidence Report",
            f"",
            f"**Session ID:** `{world_model.session_id}`  ",
            f"**Generated:** {now_str}  ",
            f"**Discovered Endpoints:** {len(inventory)} ({verified_count} verified)  ",
            f"**Application Graph Size:** {summary['total_nodes']} nodes, {summary['total_edges']} relationships  ",
            f"",
            f"---",
            f"",
            f"## Executive Summary",
            f"",
            f"InsightAPI autonomously explored the target application, observed behavioral network traffic, "
            f"inferred API route templates, and verified active endpoints with evidence.",
            f"",
            f"| Metric | Count |",
            f"|---|---|",
            f"| Total Discovered Endpoints | {len(inventory)} |",
            f"| Verified with Evidence | {verified_count} |",
            f"| Observed / Inferred | {len(inventory) - verified_count} |",
            f"| Total Application Nodes | {summary['total_nodes']} |",
            f"| Behavioral Graph Edges | {summary['total_edges']} |",
        ]

        if metrics:
            lines.extend([
                f"| Total Tool Calls | {sum(metrics.tools_executed.values())} |",
                f"| Investigation Errors | {metrics.errors_count} |",
            ])

        lines.extend([
            f"",
            f"## Discovered API Inventory",
            f"",
            f"| Method | Endpoint Template | Status | Auth Required | Confidence | Evidence Count |",
            f"|---|---|---|---|---|---|",
        ])

        for ep in inventory:
            auth_str = "Yes (401/403)" if ep.auth_required else ("No (200)" if ep.auth_required is False else "Unknown")
            lines.append(
                f"| `{ep.method}` | `{ep.template_path}` | {ep.status_code or 200} | {auth_str} | **{ep.confidence.value.upper()}** | {len(ep.evidence_ids)} |"
            )

        lines.extend([
            f"",
            f"## Behavioral Graph Relationships",
            f"",
            f"The application graph captures {summary['total_edges']} behavioral dependencies between pages, UI elements, and API endpoints:",
            f"",
        ])

        for edge in world_model.edges[:20]:
            lines.append(f"- `{edge.source_id}` **--[{edge.relation.value}]-->** `{edge.target_id}`")

        lines.extend([
            f"",
            f"---",
            f"*Generated autonomously by InsightAPI AI Autonomous Agent Runtime.*",
        ])

        return "\n".join(lines)
