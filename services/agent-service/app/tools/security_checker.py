"""Security checker tool for API vulnerability and posture evaluation."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from app.tools.base import ToolResult
from app.tools.http_probe import probe_http_endpoint

logger = logging.getLogger(__name__)


async def security_audit_endpoint(url: str, method: str = "GET") -> ToolResult:
    """
    Perform passive and active security header and transport auditing on an API endpoint.
    """
    probe = await probe_http_endpoint(url=url, method=method)
    if probe.status != "success":
        return ToolResult(
            tool_name="security_audit_endpoint",
            status="error",
            latency_ms=probe.latency_ms,
            error=probe.error,
            data={"url": url},
        )

    headers = {k.lower(): v for k, v in probe.data.get("response_headers", {}).items()}
    findings: List[Dict[str, Any]] = []

    # 1. HSTS Check
    if url.startswith("https://"):
        if "strict-transport-security" not in headers:
            findings.append({
                "category": "Transport Security",
                "severity": "MEDIUM",
                "title": "Missing HSTS Header",
                "description": "Strict-Transport-Security header is missing. Users could be vulnerable to SSL stripping attacks.",
            })
    else:
        findings.append({
            "category": "Transport Security",
            "severity": "HIGH",
            "title": "Insecure HTTP Protocol",
            "description": "The endpoint communicates over plaintext HTTP without TLS encryption.",
        })

    # 2. CORS Misconfiguration Check
    cors_origin = headers.get("access-control-allow-origin")
    if cors_origin == "*":
        findings.append({
            "category": "CORS Policy",
            "severity": "LOW",
            "title": "Wildcard Access-Control-Allow-Origin",
            "description": "Access-Control-Allow-Origin is set to '*'. Safe for public APIs, but dangerous if credentials/cookies are shared.",
        })

    # 3. Content-Type Sniffing Check
    if headers.get("x-content-type-options") != "nosniff":
        findings.append({
            "category": "MIME Sniffing",
            "severity": "LOW",
            "title": "Missing X-Content-Type-Options",
            "description": "X-Content-Type-Options: nosniff is missing, leaving browsers open to MIME type confusion.",
        })

    # 4. Clickjacking Frame Options
    if "x-frame-options" not in headers and "content-security-policy" not in headers:
        findings.append({
            "category": "Framing Protection",
            "severity": "LOW",
            "title": "Missing Frame Protections",
            "description": "Neither X-Frame-Options nor CSP frame-ancestors is present.",
        })

    # 5. Rate Limiting Headers Check
    rate_limit_headers = [k for k in headers.keys() if "ratelimit" in k or "x-rate-limit" in k]
    has_rate_limiting = len(rate_limit_headers) > 0

    score = 100 - (len([f for f in findings if f["severity"] == "HIGH"]) * 30) - (len([f for f in findings if f["severity"] == "MEDIUM"]) * 15) - (len([f for f in findings if f["severity"] == "LOW"]) * 5)
    score = max(0, min(100, score))

    return ToolResult(
        tool_name="security_audit_endpoint",
        status="success",
        latency_ms=probe.latency_ms,
        data={
            "url": url,
            "security_score": score,
            "findings_count": len(findings),
            "findings": findings,
            "has_rate_limiting": has_rate_limiting,
            "status_code": probe.data.get("status_code"),
            "headers_inspected": list(headers.keys()),
        },
    )
