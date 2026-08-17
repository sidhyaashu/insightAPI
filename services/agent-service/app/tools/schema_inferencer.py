"""Schema inference tool for generating OpenAPI 3.1 data models from live payloads."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from app.tools.base import ToolResult


def _infer_type(val: Any) -> Dict[str, Any]:
    if val is None:
        return {"type": "null"}
    if isinstance(val, bool):
        return {"type": "boolean", "example": val}
    if isinstance(val, int):
        return {"type": "integer", "example": val}
    if isinstance(val, float):
        return {"type": "number", "format": "float", "example": val}
    if isinstance(val, str):
        # Infer string formats
        schema: Dict[str, Any] = {"type": "string", "example": val[:100]}
        if "@" in val and "." in val:
            schema["format"] = "email"
        elif val.startswith("http://") or val.startswith("https://"):
            schema["format"] = "uri"
        elif len(val) == 10 and val.count("-") == 2:
            schema["format"] = "date"
        elif "T" in val and val.endswith("Z"):
            schema["format"] = "date-time"
        return schema
    if isinstance(val, list):
        if not val:
            return {"type": "array", "items": {}}
        # Infer items schema from first element (or merged)
        items_schema = _infer_type(val[0])
        return {"type": "array", "items": items_schema, "example": val[:2]}
    if isinstance(val, dict):
        properties = {}
        required = []
        for k, v in val.items():
            properties[k] = _infer_type(v)
            if v is not None:
                required.append(k)
        return {
            "type": "object",
            "properties": properties,
            "required": required if required else None,
        }
    return {"type": "string"}


def infer_openapi_schema(payload: Any) -> ToolResult:
    """
    Infer an OpenAPI 3.1 schema object from raw Python dict/list or JSON string.
    """
    try:
        if isinstance(payload, str):
            payload = json.loads(payload)

        inferred = _infer_type(payload)
        return ToolResult(
            tool_name="infer_openapi_schema",
            status="success",
            data={
                "schema": inferred,
                "is_object": isinstance(payload, dict),
                "is_array": isinstance(payload, list),
                "field_count": len(payload) if isinstance(payload, dict) else (len(payload[0]) if isinstance(payload, list) and payload and isinstance(payload[0], dict) else 0),
            },
        )
    except Exception as e:
        return ToolResult(
            tool_name="infer_openapi_schema",
            status="error",
            error=f"Schema inference failed: {str(e)}",
            data={},
        )
