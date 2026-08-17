"""HAR, Swagger, and network traffic parser for in-chat discovery."""
from __future__ import annotations

import re
import json
import logging
import urllib.parse
from typing import Any, Dict, List, Optional
from app.tools.base import ToolResult, truncate_payload

logger = logging.getLogger(__name__)

STATIC_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".css", ".scss", ".less",
    ".js", ".jsx", ".ts", ".tsx", ".mjs",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp4", ".mp3", ".webm", ".avi",
    ".pdf", ".zip", ".tar", ".gz"
}


def _normalize_route_template(path: str) -> str:
    """Normalize dynamic ID segments into parameterized route templates (/users/123 -> /users/{id})."""
    segments = path.strip("/").split("/")
    normalized = []
    for seg in segments:
        if not seg:
            continue
        # Integer IDs (/101)
        if seg.isdigit():
            normalized.append("{id}")
        # UUIDs (/550e8400-e29b-41d4-a716-446655440000)
        elif re.match(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", seg):
            normalized.append("{uuid}")
        # Hex hashes or long random tokens
        elif re.match(r"^[0-9a-fA-F]{24,64}$", seg):
            normalized.append("{token}")
        else:
            normalized.append(seg)
    return "/" + "/".join(normalized)


def parse_har_traffic(har_content: Any) -> ToolResult:
    """
    Parse browser DevTools HAR traffic JSON and extract unique REST endpoints, methods, and schemas.
    """
    try:
        if isinstance(har_content, str):
            har_data = json.loads(har_content)
        elif isinstance(har_content, dict):
            har_data = har_content
        else:
            return ToolResult(tool_name="parse_har_traffic", status="error", error="Invalid HAR format.")

        entries = har_data.get("log", {}).get("entries", [])
        if not entries and "entries" in har_data:
            entries = har_data["entries"]

        endpoints_map: Dict[str, Dict[str, Any]] = {}
        total_entries = len(entries)
        skipped_static = 0

        for entry in entries:
            req = entry.get("request", {})
            resp = entry.get("response", {})
            raw_url = req.get("url", "")
            if not raw_url:
                continue

            parsed_url = urllib.parse.urlparse(raw_url)
            path = parsed_url.path or "/"

            # Check static extension
            lower_path = path.lower()
            if any(lower_path.endswith(ext) for ext in STATIC_EXTENSIONS):
                skipped_static += 1
                continue

            method = req.get("method", "GET").upper()
            status_code = resp.get("status", 200)
            template_path = _normalize_route_template(path)
            endpoint_key = f"{method} {template_path}"

            # Response content
            resp_content = resp.get("content", {})
            mime_type = resp_content.get("mimeType", "")
            text_body = resp_content.get("text", "")
            parsed_body = None
            if text_body:
                try:
                    parsed_body = json.loads(text_body)
                except Exception:
                    parsed_body = text_body[:500]

            # Request postData
            req_body = None
            post_data = req.get("postData", {})
            if post_data.get("text"):
                try:
                    req_body = json.loads(post_data["text"])
                except Exception:
                    req_body = post_data["text"][:500]

            if endpoint_key not in endpoints_map:
                endpoints_map[endpoint_key] = {
                    "method": method,
                    "template_path": template_path,
                    "example_url": raw_url,
                    "status_code": status_code,
                    "mime_type": mime_type,
                    "query_params": req.get("queryString", []),
                    "request_body": req_body,
                    "sample_response": truncate_payload(parsed_body, 1000),
                    "occurrences": 1,
                }
            else:
                endpoints_map[endpoint_key]["occurrences"] += 1

        discovered_endpoints = list(endpoints_map.values())

        return ToolResult(
            tool_name="parse_har_traffic",
            status="success",
            data={
                "total_entries_scanned": total_entries,
                "static_assets_filtered": skipped_static,
                "unique_endpoints_found": len(discovered_endpoints),
                "endpoints": discovered_endpoints[:50],  # cap at top 50
            },
        )

    except Exception as e:
        logger.warning(f"HAR parsing error: {e}")
        return ToolResult(
            tool_name="parse_har_traffic",
            status="error",
            error=f"HAR parsing failed: {str(e)}",
            data={},
        )
