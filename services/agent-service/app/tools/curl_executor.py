"""cURL parsing and live execution tool."""
from __future__ import annotations

import re
import shlex
import logging
from typing import Any, Dict, Optional

from app.tools.base import ToolResult
from app.tools.http_probe import probe_http_endpoint

logger = logging.getLogger(__name__)


def parse_curl_command(curl_str: str) -> Dict[str, Any]:
    """
    Parse a raw cURL command into structured HTTP request arguments.
    Supports -X/--request, -H/--header, -d/--data/--data-raw, -u/--user, -A/--user-agent, query params, etc.
    """
    # Normalize multiline backslashes
    clean = re.sub(r"\\\s*\n", " ", curl_str.strip())
    # Remove leading 'curl' or 'curl.exe'
    tokens = shlex.split(clean)
    if tokens and tokens[0].lower() in {"curl", "curl.exe"}:
        tokens = tokens[1:]

    method = "GET"
    url = ""
    headers: Dict[str, str] = {}
    body: Optional[str] = None
    i = 0
    while i < len(tokens):
        t = tokens[i]

        if t in ("-X", "--request") and i + 1 < len(tokens):
            method = tokens[i + 1].upper()
            i += 2
        elif t in ("-H", "--header") and i + 1 < len(tokens):
            h_raw = tokens[i + 1]
            if ":" in h_raw:
                k, v = h_raw.split(":", 1)
                headers[k.strip()] = v.strip()
            i += 2
        elif t in ("-d", "--data", "--data-raw", "--data-binary", "--data-urlencode") and i + 1 < len(tokens):
            body = tokens[i + 1]
            if method == "GET":
                method = "POST"
            i += 2
        elif t in ("-A", "--user-agent") and i + 1 < len(tokens):
            headers["User-Agent"] = tokens[i + 1]
            i += 2
        elif t in ("-u", "--user") and i + 1 < len(tokens):
            import base64
            auth_val = base64.b64encode(tokens[i + 1].encode()).decode()
            headers["Authorization"] = f"Basic {auth_val}"
            i += 2
        elif not t.startswith("-") and not url:
            url = t
            i += 1
        else:
            i += 1

    return {
        "url": url,
        "method": method,
        "headers": headers,
        "body": body,
    }


async def execute_curl(curl_command: str) -> ToolResult:
    """
    Parse a cURL command, execute the HTTP request live, and return status and telemetry.
    """
    try:
        parsed = parse_curl_command(curl_command)
        if not parsed["url"]:
            return ToolResult(
                tool_name="execute_curl",
                status="error",
                error="Could not extract a valid URL from the cURL command.",
                data={"raw_curl": curl_command},
            )

        probe_res = await probe_http_endpoint(
            url=parsed["url"],
            method=parsed["method"],
            headers=parsed["headers"],
            body=parsed["body"],
        )

        probe_dict = probe_res.data
        probe_dict["parsed_request"] = parsed
        return ToolResult(
            tool_name="execute_curl",
            status=probe_res.status,
            latency_ms=probe_res.latency_ms,
            error=probe_res.error,
            data=probe_dict,
        )

    except Exception as e:
        logger.warning(f"execute_curl failed: {e}")
        return ToolResult(
            tool_name="execute_curl",
            status="error",
            error=f"cURL execution failed: {str(e)}",
            data={"raw_curl": curl_command},
        )
