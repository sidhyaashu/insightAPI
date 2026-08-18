"""Base classes, data models, and guardrails for agent tools."""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolMetadata(BaseModel):
    name: str
    description: str
    category: str = "network"
    is_safe: bool = True
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool_name: str
    status: str  # "success" | "error"
    latency_ms: int = 0
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool_name,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "data": self.data,
            "error": self.error,
        }

    def to_observation(
        self,
        session_id: str,
        source: Optional[str] = None,
        action_id: Optional[str] = None,
    ) -> "Any":
        """
        Convert this ToolResult into a typed ``Observation`` for the agent runtime.

        Importing here (deferred) avoids a circular import between the tools layer
        and the runtime layer. The ``source`` defaults to the tool name.

        Parameters
        ----------
        session_id:  Active investigation session ID.
        source:      ObservationSource string (defaults to tool-derived source).
        action_id:   ID of the Action that triggered this tool (if known).

        Returns
        -------
        app.runtime.models.Observation
        """
        from app.runtime.models import Observation, ObservationSource, ConfidenceLevel

        # Map common tool names to their canonical ObservationSource
        _source_map = {
            "probe_http_endpoint": ObservationSource.HTTP,
            "execute_curl": ObservationSource.HTTP,
            "explore_web_app_browser": ObservationSource.BROWSER,
            "parse_har_traffic": ObservationSource.NETWORK,
            "infer_openapi_schema": ObservationSource.SCHEMA,
            "security_audit_endpoint": ObservationSource.SECURITY,
            "parse_graphql_payload": ObservationSource.GRAPHQL,
        }
        resolved_source = (
            ObservationSource(source)
            if source
            else _source_map.get(self.tool_name, ObservationSource.HTTP)
        )

        confidence = (
            ConfidenceLevel.TESTED if self.status == "success"
            else ConfidenceLevel.UNOBSERVED
        )

        return Observation(
            session_id=session_id,
            source=resolved_source,
            action_id=action_id,
            request_url=self.data.get("url"),
            request_method=self.data.get("method"),
            response_status=self.data.get("status_code"),
            response_body=self.data.get("body"),
            latency_ms=self.latency_ms,
            confidence=confidence,
            error=self.error,
            raw_tool_result=self.to_dict(),
        )


def truncate_payload(data: Any, max_length: int = 25000) -> Any:
    """Ensure response payload size does not overflow LLM context window."""
    if isinstance(data, str) and len(data) > max_length:
        return data[:max_length] + f"\n... [Truncated: {len(data) - max_length} additional characters]"
    if isinstance(data, dict):
        truncated = {}
        for k, v in data.items():
            if isinstance(v, (str, dict, list)):
                truncated[k] = truncate_payload(v, max_length // 2)
            else:
                truncated[k] = v
        return truncated
    if isinstance(data, list):
        if len(data) > 30:
            return [truncate_payload(item, max_length // 4) for item in data[:30]] + [
                f"... [Truncated: {len(data) - 30} additional items]"
            ]
        return [truncate_payload(item, max_length // 4) for item in data]
    return data
