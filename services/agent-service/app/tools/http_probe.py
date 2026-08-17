"""HTTP probe tool for live API endpoint testing and schema discovery."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional
import httpx

from app.tools.base import ToolResult, truncate_payload
from app.tools.guardrails import validate_target_url

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SEC = 10.0
DEFAULT_USER_AGENT = "InsightAPI-Intelligence-Probe/1.0 (+https://insightapi.ai/bot)"


async def probe_http_endpoint(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Any] = None,
    follow_redirects: bool = True,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
) -> ToolResult:
    """
    Execute a real HTTP probe against the target URL and return detailed telemetry.

    Args:
        url: The full HTTP/HTTPS URL to probe.
        method: HTTP method (GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD).
        headers: Optional dictionary of request headers.
        params: Optional query parameters.
        body: Optional request body (dict/list for JSON, or raw string).
        follow_redirects: Whether to follow HTTP 3xx redirects.
        timeout_sec: Maximum timeout in seconds (default 10s).
    """
    start_time = time.perf_counter()
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"

    # 1. SSRF and Guardrail Validation
    is_safe, error_msg = validate_target_url(url)
    if not is_safe:
        return ToolResult(
            tool_name="probe_http_endpoint",
            status="error",
            latency_ms=0,
            error=f"Guardrail Blocked: {error_msg}",
            data={"url": url, "method": method, "blocked_by_guardrail": True},
        )

    method = method.upper().strip()
    req_headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json, text/plain, */*"}
    if headers:
        req_headers.update(headers)

    json_body = None
    data_body = None
    if body is not None:
        if isinstance(body, (dict, list)):
            json_body = body
            req_headers.setdefault("Content-Type", "application/json")
        elif isinstance(body, str):
            try:
                json_body = json.loads(body)
                req_headers.setdefault("Content-Type", "application/json")
            except Exception:
                data_body = body

    try:
        async with httpx.AsyncClient(
            verify=False,
            timeout=min(timeout_sec, 20.0),
            follow_redirects=follow_redirects,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        ) as client:
            resp = await client.request(
                method=method,
                url=url,
                headers=req_headers,
                params=params,
                json=json_body,
                content=data_body,
            )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Parse response body
        content_type = resp.headers.get("content-type", "").lower()
        parsed_json = None
        text_content = resp.text

        if "application/json" in content_type or "+json" in content_type:
            try:
                parsed_json = resp.json()
            except Exception:
                pass
        elif text_content.strip().startswith("{") or text_content.strip().startswith("["):
            try:
                parsed_json = resp.json()
            except Exception:
                pass

        body_payload = parsed_json if parsed_json is not None else text_content
        truncated_body = truncate_payload(body_payload)

        # Filter relevant response headers
        safe_resp_headers = {}
        for k, v in resp.headers.items():
            if k.lower() in {
                "content-type", "server", "date", "etag", "cache-control",
                "access-control-allow-origin", "x-ratelimit-remaining",
                "x-ratelimit-limit", "strict-transport-security",
                "x-content-type-options", "x-frame-options", "location"
            }:
                safe_resp_headers[k] = v

        return ToolResult(
            tool_name="probe_http_endpoint",
            status="success",
            latency_ms=latency_ms,
            data={
                "url": str(resp.url),
                "method": method,
                "status_code": resp.status_code,
                "status_text": resp.reason_phrase if hasattr(resp, "reason_phrase") else "",
                "latency_ms": latency_ms,
                "content_type": content_type,
                "response_headers": safe_resp_headers,
                "is_json": parsed_json is not None,
                "body": truncated_body,
                "redirects": [str(r.url) for r in resp.history] if resp.history else [],
            },
        )

    except httpx.TimeoutException:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return ToolResult(
            tool_name="probe_http_endpoint",
            status="error",
            latency_ms=latency_ms,
            error=f"Connection timed out after {timeout_sec}s while connecting to {url}",
            data={"url": url, "method": method, "timeout": True},
        )
    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.warning(f"probe_http_endpoint error for {url}: {e}")
        return ToolResult(
            tool_name="probe_http_endpoint",
            status="error",
            latency_ms=latency_ms,
            error=f"HTTP Request failed: {str(e)}",
            data={"url": url, "method": method},
        )
