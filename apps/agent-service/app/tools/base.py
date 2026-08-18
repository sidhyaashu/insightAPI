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
